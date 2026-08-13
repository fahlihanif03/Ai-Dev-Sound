"""
live_monitor.py

Continuously listens through your Mac's microphone and scores rolling
2-second windows against a trained autoencoder model - stand near the
benchtop motor/fan and watch live anomaly scores before touching any
embedded hardware.

Requires: pip install sounddevice
On first run, macOS will prompt for microphone access. If you miss the
prompt, allow it manually in System Settings > Privacy & Security > Microphone,
then re-run.

Usage:
    python live_monitor.py --machine_id id_00

    # if the wrong microphone gets picked, list devices first:
    python -m sounddevice
    python live_monitor.py --machine_id id_00 --device 2
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


def load_model_and_stats(machine_id):
    model_path = os.path.join(MODEL_DIR, f"{machine_id}_fan_autoencoder.h5")
    stats_path = os.path.join(MODEL_DIR, f"{machine_id}_norm_stats.npz")
    if not os.path.exists(model_path):
        raise SystemExit(f"No trained model found at {model_path} - run train_autoencoder.py first.")
    model = keras.models.load_model(model_path)
    stats = np.load(stats_path)
    return model, stats["mean"], stats["std"], float(stats["threshold"])


def score_audio(y, model, mean, std):
    log_mel = audio_to_log_mel(y)
    vectors = frames_to_vectors(log_mel)
    if vectors.shape[0] == 0:
        return None
    vectors_norm = (vectors - mean) / std
    pred = model.predict(vectors_norm, verbose=0)
    frame_errors = np.mean(np.square(vectors_norm - pred), axis=1)
    return float(np.mean(frame_errors))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--machine_id", default="id_00")
    parser.add_argument("--device", type=int, default=None,
                         help="Input device index - run `python -m sounddevice` to list options")
    args = parser.parse_args()

    model, mean, std, threshold = load_model_and_stats(args.machine_id)
    print(f"Loaded model for {args.machine_id}, anomaly threshold = {threshold:.4f}")
    print("Listening... Ctrl+C to stop.\n")

    RED = "\033[91m"
    GREEN = "\033[92m"
    RESET = "\033[0m"

    window_samples = int(WINDOW_SECONDS * SAMPLE_RATE)

    try:
        while True:
            recording = sd.rec(window_samples, samplerate=SAMPLE_RATE, channels=1,
                                dtype="float32", device=args.device)
            sd.wait()
            y = recording[:, 0]

            score = score_audio(y, model, mean, std)
            if score is None:
                print("(clip too quiet/short to score)")
                continue

            if score > threshold:
                verdict = f"{RED}DEFECT{RESET}"
            else:
                verdict = f"{GREEN}OKAY  {RESET}"
            print(f"[{time.strftime('%H:%M:%S')}]  {verdict}   (score={score:.4f}, threshold={threshold:.4f})")

    except KeyboardInterrupt:
        print("\nStopped.")


if __name__ == "__main__":
    main()
