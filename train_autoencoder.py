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

FEATURES_DIR = "features"
MODEL_DIR = "models"
INPUT_DIM = 64 * 5  # N_MELS * FRAMES - must match prepare_features.py


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
    if not os.path.exists(normal_path):
        raise SystemExit(f"Missing {normal_path} - run prepare_features.py first.")

    normal = np.load(normal_path)
    abnormal = np.load(abnormal_path)

    if normal.shape[0] == 0:
        raise SystemExit("No normal vectors found - check your dataset folder.")

    # standardize using stats from normal data only
    mean = normal.mean(axis=0, keepdims=True)
    std = normal.std(axis=0, keepdims=True) + 1e-6
    normal_norm = (normal - mean) / std
    abnormal_norm = (abnormal - mean) / std

    # hold out 10% of normal vectors to check separation against abnormal
    n_val = max(1, int(0.1 * len(normal_norm)))
    rng = np.random.default_rng(42)
    idx = rng.permutation(len(normal_norm))
    val_idx, train_idx = idx[:n_val], idx[n_val:]

    x_train = normal_norm[train_idx]
    x_val_normal = normal_norm[val_idx]

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

    # sanity check: reconstruction error should be higher for abnormal
    # vectors than for held-out normal vectors
    def recon_error(x):
        pred = model.predict(x, verbose=0)
        return np.mean(np.square(x - pred), axis=1)

    normal_scores = recon_error(x_val_normal)
    abnormal_scores = recon_error(abnormal_norm)

    labels = np.concatenate([np.zeros(len(normal_scores)), np.ones(len(abnormal_scores))])
    scores = np.concatenate([normal_scores, abnormal_scores])
    auc = roc_auc_score(labels, scores)
    print(f"\nValidation AUC ({args.machine_id}): {auc:.4f}  "
          f"(0.5 = no better than random, 1.0 = perfect separation)")

    # threshold = 95th percentile of held-out normal scores, i.e. accept
    # a ~5% false-positive rate on sounds we know are actually normal
    threshold = float(np.percentile(normal_scores, 95))
    print(f"Anomaly threshold (95th percentile of normal scores): {threshold:.4f}")
    print(f"  normal  scores: mean={normal_scores.mean():.4f}  max={normal_scores.max():.4f}")
    print(f"  abnormal scores: mean={abnormal_scores.mean():.4f}  min={abnormal_scores.min():.4f}")

    # save mean/std/threshold so this exact normalization + cutoff can be
    # reproduced by evaluate_wav.py and live_monitor.py
    np.savez(os.path.join(MODEL_DIR, f"{args.machine_id}_norm_stats.npz"),
              mean=mean, std=std, threshold=threshold)

    # save as legacy Keras .h5 - required format for DEEPCRAFT Model Converter
    h5_path = os.path.join(MODEL_DIR, f"{args.machine_id}_fan_autoencoder.h5")
    model.save(h5_path, save_format="h5")
    print(f"Saved model to {h5_path}")


if __name__ == "__main__":
    main()
