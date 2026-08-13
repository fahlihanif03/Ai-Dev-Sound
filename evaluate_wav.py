"""
evaluate_wav.py

Score one or more WAV files against a trained autoencoder model, using
the exact same feature extraction as training (see prepare_features.py).

Good first check before live_monitor.py: record a short clip of your
benchtop motor/fan with Voice Memos/QuickTime, or reuse MIMII files you
didn't train on, and see what score comes back.

Usage:
    python evaluate_wav.py --machine_id id_00 clip1.wav clip2.wav
"""
import os
os.environ["TF_USE_LEGACY_KERAS"] = "1"

import argparse
import numpy as np
from tensorflow import keras

from prepare_features import wav_to_log_mel, frames_to_vectors

MODEL_DIR = "models"


def load_model_and_stats(machine_id):
    model_path = os.path.join(MODEL_DIR, f"{machine_id}_fan_autoencoder.h5")
    stats_path = os.path.join(MODEL_DIR, f"{machine_id}_norm_stats.npz")
    if not os.path.exists(model_path):
        raise SystemExit(f"No trained model found at {model_path} - run train_autoencoder.py first.")
    model = keras.models.load_model(model_path)
    stats = np.load(stats_path)
    return model, stats["mean"], stats["std"], float(stats["threshold"])


def score_wav(path, model, mean, std):
    log_mel = wav_to_log_mel(path)
    vectors = frames_to_vectors(log_mel)
    if vectors.shape[0] == 0:
        raise ValueError(f"{path} is too short to extract features from")
    vectors_norm = (vectors - mean) / std
    pred = model.predict(vectors_norm, verbose=0)
    frame_errors = np.mean(np.square(vectors_norm - pred), axis=1)
    return float(np.mean(frame_errors))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--machine_id", default="id_00")
    parser.add_argument("--threshold", type=float, default=None,
                         help="Override the saved threshold - use this when testing raw MIMII "
                              "files after calibrate_threshold.py has changed the saved threshold "
                              "to your live mic's domain")
    parser.add_argument("wav_files", nargs="+")
    args = parser.parse_args()

    model, mean, std, saved_threshold = load_model_and_stats(args.machine_id)
    threshold = args.threshold if args.threshold is not None else saved_threshold
    source = "override" if args.threshold is not None else "saved"
    print(f"Loaded model for {args.machine_id}, anomaly threshold = {threshold:.4f} ({source})\n")

    for path in args.wav_files:
        score = score_wav(path, model, mean, std)
        verdict = "ANOMALY" if score > threshold else "normal"
        print(f"{path:40s}  score={score:8.4f}  -> {verdict}")


if __name__ == "__main__":
    main()
