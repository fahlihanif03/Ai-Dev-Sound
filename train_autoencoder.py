"""
train_autoencoder.py

Trains a dense autoencoder for unsupervised anomaly detection on MIMII fan
sound features (produced by prepare_features.py), and exports a Keras 2
.h5 model - the format DEEPCRAFT Model Converter expects.

The idea: train only on normal sounds. A healthy sound reconstructs
cleanly through the bottleneck; a faulty one doesn't. Reconstruction
error becomes the anomaly score.

Usage:
    python train_autoencoder.py --machine_id id_00
"""

import os
# Current TensorFlow defaults to Keras 3, whose .h5 output DEEPCRAFT
# Model Converter can't read. This env var switches to legacy Keras 2 -
# it requires the `tf-keras` package (see requirements.txt) to be
# installed, or this will fail on import.
os.environ["TF_USE_LEGACY_KERAS"] = "1"

import argparse
import numpy as np
import tensorflow as tf
from tensorflow import keras
from tensorflow.keras import layers
from sklearn.metrics import roc_auc_score

from prepare_features import N_MELS, FRAMES, WINDOW_SECONDS, vectors_per_window
from scoring import fit_error_stats, score_vectors, iter_windows, SCORE_PERCENTILE

FEATURES_DIR = "features"
MODEL_DIR = "models"
INPUT_DIM = N_MELS * FRAMES  # must match prepare_features.py


def build_autoencoder(input_dim):
    inputs = keras.Input(shape=(input_dim,), name="input")
    x = layers.Dense(128, activation="relu")(inputs)
    x = layers.Dense(128, activation="relu")(x)
    x = layers.Dense(128, activation="relu")(x)
    x = layers.Dense(8, activation="relu", name="bottleneck")(x)
    x = layers.Dense(128, activation="relu")(x)
    x = layers.Dense(128, activation="relu")(x)
    x = layers.Dense(128, activation="relu")(x)
    outputs = layers.Dense(input_dim, activation=None, name="output")(x)
    model = keras.Model(inputs, outputs, name="fan_autoencoder")
    model.compile(optimizer=keras.optimizers.Adam(1e-3), loss="mse")
    return model


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--machine_id", default="id_00",
                         help="Which fan id folder to train on, e.g. id_00")
    parser.add_argument("--epochs", type=int, default=50)
    parser.add_argument("--batch_size", type=int, default=512)
    args = parser.parse_args()

    os.makedirs(MODEL_DIR, exist_ok=True)

    normal_path = os.path.join(FEATURES_DIR, f"{args.machine_id}_normal.npy")
    abnormal_path = os.path.join(FEATURES_DIR, f"{args.machine_id}_abnormal.npy")
    lengths_path = os.path.join(FEATURES_DIR, f"{args.machine_id}_normal_lengths.npy")
    abnormal_lengths_path = os.path.join(FEATURES_DIR, f"{args.machine_id}_abnormal_lengths.npy")
    if not os.path.exists(normal_path):
        raise SystemExit(f"Missing {normal_path} - run prepare_features.py first.")
    if not os.path.exists(lengths_path):
        raise SystemExit(f"Missing {lengths_path} - re-run prepare_features.py (it now also "
                          f"saves per-file lengths needed for window-pooled validation).")

    normal = np.load(normal_path)
    normal_lengths = np.load(lengths_path)
    abnormal = np.load(abnormal_path)
    abnormal_lengths = np.load(abnormal_lengths_path)

    if normal.shape[0] == 0:
        raise SystemExit("No normal vectors found - check your dataset folder.")

    # standardize using stats from normal data only
    mean = normal.mean(axis=0, keepdims=True)
    std = normal.std(axis=0, keepdims=True) + 1e-6
    normal_norm = (normal - mean) / std
    abnormal_norm = (abnormal - mean) / std

    # hold out 10% of FILES (not individual vectors) as normal validation,
    # so their per-file frame ordering stays intact for window pooling
    n_files = len(normal_lengths)
    n_val_files = max(1, int(0.1 * n_files))
    rng = np.random.default_rng(42)
    file_order = rng.permutation(n_files)
    val_files, train_files = set(file_order[:n_val_files]), set(file_order[n_val_files:])

    file_starts = np.concatenate([[0], np.cumsum(normal_lengths)])
    train_mask = np.zeros(len(normal_norm), dtype=bool)
    for i in train_files:
        train_mask[file_starts[i]: file_starts[i + 1]] = True

    x_train = normal_norm[train_mask]
    x_val_normal = normal_norm[~train_mask]
    val_lengths = normal_lengths[sorted(val_files)]

    model = build_autoencoder(INPUT_DIM)
    model.summary()

    model.fit(
        x_train, x_train,
        validation_split=0.1,
        epochs=args.epochs,
        batch_size=args.batch_size,
        shuffle=True,
        verbose=2,
    )

    # per-dimension error stats, fit on held-out normal vectors only
    err_mean, err_std = fit_error_stats(model, x_val_normal)

    # pool scores over windows sized to match a real live_monitor.py capture
    # (WINDOW_SECONDS below), not a whole 10s file - so the validation AUC
    # and threshold reflect what the live monitor will actually see.
    window_size = vectors_per_window(WINDOW_SECONDS)
    normal_scores = np.array([
        score_vectors(w, model, err_std) for w in iter_windows(x_val_normal, val_lengths, window_size)
    ])
    abnormal_scores = np.array([
        score_vectors(w, model, err_std) for w in iter_windows(abnormal_norm, abnormal_lengths, window_size)
    ])

    if len(normal_scores) == 0 or len(abnormal_scores) == 0:
        raise SystemExit(
            f"Not enough audio per file to form a {WINDOW_SECONDS}s window "
            f"({window_size} vectors) - got {len(normal_scores)} normal / "
            f"{len(abnormal_scores)} abnormal windows."
        )

    labels = np.concatenate([np.zeros(len(normal_scores)), np.ones(len(abnormal_scores))])
    scores = np.concatenate([normal_scores, abnormal_scores])
    auc = roc_auc_score(labels, scores)
    pauc = roc_auc_score(labels, scores, max_fpr=0.1)
    print(f"\nValidation AUC ({args.machine_id}):  {auc * 100:.2f}%  "
          f"(50% = no better than random, 100% = perfect separation)")
    print(f"Validation pAUC (max_fpr=0.1):     {pauc * 100:.2f}%")

    # threshold = 95th percentile of held-out normal scores, i.e. accept
    # a ~5% false-positive rate on sounds we know are actually normal
    threshold = float(np.percentile(normal_scores, 95))
    print(f"Anomaly threshold (95th percentile of normal scores): {threshold:.4f}")
    print(f"  normal  scores: mean={normal_scores.mean():.4f}  max={normal_scores.max():.4f}")
    print(f"  abnormal scores: mean={abnormal_scores.mean():.4f}  min={abnormal_scores.min():.4f}")

    # save mean/std/threshold/err stats so this exact normalization + cutoff
    # + scoring can be reproduced by evaluate_wav.py and live_monitor.py
    np.savez(os.path.join(MODEL_DIR, f"{args.machine_id}_norm_stats.npz"),
              mean=mean, std=std, threshold=threshold,
              err_mean=err_mean, err_std=err_std)

    # save as legacy Keras .h5 - required format for DEEPCRAFT Model Converter
    h5_path = os.path.join(MODEL_DIR, f"{args.machine_id}_fan_autoencoder.h5")
    model.save(h5_path, save_format="h5")
    print(f"Saved model to {h5_path}")


if __name__ == "__main__":
    main()
