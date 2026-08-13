"""
calibrate_threshold.py

MIMII was recorded with a studio microphone array in a real factory -
your Mac's built-in mic (or the board's mic later) is a different
recording domain, so the threshold learned from MIMII doesn't transfer
directly. This script fixes that by measuring real scores through your
actual mic and picking a threshold based on what it hears.

Two modes:
  - Normal-only (default): records known-normal sound, sets the
    threshold at a percentile above what normal typically scores.
    An educated guess - works with just a healthy-running machine.
  - Normal + defect (--with-defect, recommended if you can produce
    both): also records known-defect sound (a real induced fault, or
    MIMII abnormal clips played through a speaker), then computes the
    threshold that actually best separates the two classes in your
    mic's real domain - measured, not guessed.

Usage:
    # normal-only
    python calibrate_threshold.py --machine_id id_00 --seconds 60

    # normal + defect (better, if you can produce defect sound on demand)
    python calibrate_threshold.py --machine_id id_00 --seconds 60 --with-defect
"""
import os
os.environ["TF_USE_LEGACY_KERAS"] = "1"

import argparse
import time
import numpy as np
import sounddevice as sd
from tensorflow import keras

from prepare_features import audio_to_log_mel, frames_to_vectors, SAMPLE_RATE

MODEL_DIR = "models"
WINDOW_SECONDS = 2.0


def score_window(y, model, mean, std):
    log_mel = audio_to_log_mel(y)
    vectors = frames_to_vectors(log_mel)
    if vectors.shape[0] == 0:
        return None
    vectors_norm = (vectors - mean) / std
    pred = model.predict(vectors_norm, verbose=0)
    frame_errors = np.mean(np.square(vectors_norm - pred), axis=1)
    return float(np.mean(frame_errors))


def record_scores(label, seconds, model, mean, std, device):
    print(f"\nAbout to record {seconds}s of KNOWN-{label.upper()} sound.")
    if label == "normal":
        print("Make sure the machine is actually running normally right now.")
    else:
        print("Produce the defect sound now (induced fault, or a defect clip played nearby).")
    print("Starting in 3 seconds...")
    time.sleep(3)

    window_samples = int(WINDOW_SECONDS * SAMPLE_RATE)
    n_windows = max(1, seconds // int(WINDOW_SECONDS))

    scores = []
    for i in range(n_windows):
        recording = sd.rec(window_samples, samplerate=SAMPLE_RATE, channels=1,
                            dtype="float32", device=device)
        sd.wait()
        score = score_window(recording[:, 0], model, mean, std)
        if score is None:
            continue
        scores.append(score)
        print(f"  {label} window {i + 1}/{n_windows}: score={score:.4f}")

    return np.array(scores)


def best_separating_threshold(normal_scores, abnormal_scores):
    """Search every candidate cutoff and pick the one maximizing Youden's J
    (true positive rate - false positive rate). Only meaningful with real
    examples of both classes - otherwise there's nothing to separate."""
    candidates = np.unique(np.concatenate([normal_scores, abnormal_scores]))
    best_threshold, best_j = candidates[0], -1.0
    for t in candidates:
        tpr = np.mean(abnormal_scores > t)
        fpr = np.mean(normal_scores > t)
        j = tpr - fpr
        if j > best_j:
            best_j, best_threshold = j, t
    return float(best_threshold), float(best_j)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--machine_id", default="id_00")
    parser.add_argument("--seconds", type=int, default=60,
                         help="How long to record each class for calibration")
    parser.add_argument("--device", type=int, default=None)
    parser.add_argument("--percentile", type=float, default=95,
                         help="[normal-only mode] percentile of normal scores to use as threshold")
    parser.add_argument("--with-defect", action="store_true",
                         help="Also record known-defect sound and compute the best-separating "
                              "threshold instead of a percentile guess")
    args = parser.parse_args()

    model_path = os.path.join(MODEL_DIR, f"{args.machine_id}_fan_autoencoder.h5")
    stats_path = os.path.join(MODEL_DIR, f"{args.machine_id}_norm_stats.npz")
    if not os.path.exists(model_path):
        raise SystemExit(f"No trained model found at {model_path} - run train_autoencoder.py first.")

    model = keras.models.load_model(model_path)
    stats = np.load(stats_path)
    mean, std = stats["mean"], stats["std"]
    old_threshold = float(stats["threshold"])

    normal_scores = record_scores("normal", args.seconds, model, mean, std, args.device)
    if normal_scores.size == 0:
        raise SystemExit("No usable normal audio captured - check your microphone/device selection.")

    if args.with_defect:
        abnormal_scores = record_scores("defect", args.seconds, model, mean, std, args.device)
        if abnormal_scores.size == 0:
            raise SystemExit("No usable defect audio captured - check your microphone/device selection.")

        new_threshold, j_stat = best_separating_threshold(normal_scores, abnormal_scores)
        print(f"\nNormal scores: mean={normal_scores.mean():.4f}  max={normal_scores.max():.4f}")
        print(f"Defect scores: mean={abnormal_scores.mean():.4f}  min={abnormal_scores.min():.4f}")
        print(f"Best-separating threshold: {new_threshold:.4f}  "
              f"(Youden's J={j_stat:.3f} - 1.0 is perfect separation, 0 is no better than chance)")
    else:
        new_threshold = float(np.percentile(normal_scores, args.percentile))
        print(f"\nNormal scores: mean={normal_scores.mean():.4f}  max={normal_scores.max():.4f}")
        print(f"Threshold ({args.percentile:.0f}th percentile of normal): {new_threshold:.4f}")

    print(f"Old threshold: {old_threshold:.4f}")
    print(f"New threshold: {new_threshold:.4f}")

    np.savez(stats_path, mean=mean, std=std, threshold=new_threshold)
    print("\nSaved. live_monitor.py and other scripts will use the new threshold automatically.")


if __name__ == "__main__":
    main()
