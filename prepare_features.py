"""
prepare_features.py

Extracts log-mel spectrogram features from MIMII fan WAV files and saves
them as numpy arrays, ready for training.

Expects this folder layout (after you've downloaded + unzipped the fan
data from https://zenodo.org/records/3384388):

    dataset/
      fan/
        id_00/
          normal/    *.wav
          abnormal/  *.wav
        id_02/
          normal/    *.wav
          abnormal/  *.wav
        id_04/ ...
        id_06/ ...

Adjust DATASET_DIR below if you extracted the files somewhere else.

Usage:
    python prepare_features.py
"""

import os
import glob
import numpy as np
import librosa
from tqdm import tqdm

# ---- config ----
DATASET_DIR = r"C:\Users\USER\Ai-Dev-Sound-Windows\fan6db"  # your extracted fan data
SAMPLE_RATE = 16000                # matches the board's mic sample rate
N_MELS = 64
N_FFT = 1024
HOP_LENGTH = 512
FRAMES = 32                        # widened from 5 -> 32: more temporal context per window,
                                    # cheap for this dense architecture (validated on fan6db,
                                    # see DCASE_Fan6dB_Improved_Report.md)
OUTPUT_DIR = "features"
WINDOW_SECONDS = 2.0                # length of one live_monitor.py mic capture; also used by
                                    # train_autoencoder.py so offline validation is pooled over
                                    # the same amount of audio a live window actually sees


def audio_to_log_mel(y, sr=SAMPLE_RATE):
    """Same feature extraction as wav_to_log_mel, but takes an in-memory
    audio array instead of a file path - used by live_monitor.py so mic
    capture goes through the identical pipeline as training data.

    dB is computed relative to this clip's own loudest frame (ref=np.max),
    not an absolute scale - otherwise the model just learns "how loud was
    MIMII's mic", and any live capture at a different gain/distance/mic
    sensitivity reads as anomalous regardless of whether the fan is
    actually healthy. This is the same normalization the DCASE PyTorch
    scripts already use (librosa.power_to_db(..., ref=np.max))."""
    mel = librosa.feature.melspectrogram(
        y=y, sr=sr, n_fft=N_FFT, hop_length=HOP_LENGTH, n_mels=N_MELS
    )
    log_mel = librosa.power_to_db(mel, ref=np.max)
    return log_mel.astype(np.float32)  # shape: (N_MELS, time_frames)


def wav_to_log_mel(path):
    y, sr = librosa.load(path, sr=SAMPLE_RATE, mono=True)
    return audio_to_log_mel(y, sr)


def frames_to_vectors(log_mel):
    """Stack FRAMES consecutive time-steps into single feature vectors."""
    n_mels, n_frames = log_mel.shape
    n_vectors = n_frames - FRAMES + 1
    if n_vectors < 1:
        return np.empty((0, n_mels * FRAMES), dtype=np.float32)
    vectors = np.zeros((n_vectors, n_mels * FRAMES), dtype=np.float32)
    for t in range(FRAMES):
        vectors[:, n_mels * t: n_mels * (t + 1)] = log_mel[:, t: t + n_vectors].T
    return vectors


def vectors_per_window(seconds, sr=SAMPLE_RATE):
    """How many frame-vectors a `seconds`-long capture produces once run
    through audio_to_log_mel + frames_to_vectors - used to make offline
    validation (train_autoencoder.py) pool over the same amount of audio
    a live rolling window actually sees, instead of a whole 10s file."""
    y = np.zeros(int(seconds * sr), dtype=np.float32)
    log_mel = audio_to_log_mel(y, sr)
    return frames_to_vectors(log_mel).shape[0]


def find_machine_folders(dataset_dir):
    """Recursively find every 'normal' folder under dataset_dir that has a
    sibling 'abnormal' folder, and infer the machine id from the parent
    folder name. Handles both flat (fan6db/id_00/normal) and nested
    (fan6db/fan/id_00/normal) extraction layouts without guessing which
    one you got.

    Also handles the flat Train_Normal_XX / Test_Validation_XX layout (no
    normal/abnormal subfolders - class is encoded in the filename prefix
    instead, and Test_Validation_XX mixes normal_*/anomaly_* together)."""
    found = {}
    for normal_dir in glob.glob(os.path.join(dataset_dir, "**", "normal"), recursive=True):
        parent = os.path.dirname(normal_dir)
        abnormal_dir = os.path.join(parent, "abnormal")
        if os.path.isdir(abnormal_dir):
            machine_id = os.path.basename(parent)
            found[machine_id] = (normal_dir, None, abnormal_dir, None)

    for train_dir in glob.glob(os.path.join(dataset_dir, "Train_Normal_*")):
        suffix = os.path.basename(train_dir)[len("Train_Normal_"):]
        test_dir = os.path.join(dataset_dir, f"Test_Validation_{suffix}")
        if os.path.isdir(test_dir):
            found[f"id_{suffix}"] = (train_dir, "normal_", test_dir, "anomaly_")

    return found


def process_folder(folder, label, prefix=None):
    """Returns (vectors, lengths): the concatenated frame vectors for every
    file, plus how many vectors came from each file (in the same order) -
    so downstream code can regroup vectors back into per-file or
    per-window pools without re-touching audio."""
    pattern = f"{prefix}*.wav" if prefix else "*.wav"
    wav_paths = sorted(glob.glob(os.path.join(folder, pattern)))
    all_vectors = []
    lengths = []
    for path in tqdm(wav_paths, desc=f"{label}: {folder}"):
        log_mel = wav_to_log_mel(path)
        vectors = frames_to_vectors(log_mel)
        all_vectors.append(vectors)
        lengths.append(vectors.shape[0])
    if not all_vectors:
        return np.empty((0, N_MELS * FRAMES), dtype=np.float32), np.array([], dtype=np.int64)
    return np.concatenate(all_vectors, axis=0), np.array(lengths, dtype=np.int64)


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    if not os.path.isdir(DATASET_DIR):
        raise SystemExit(
            f"Can't find {DATASET_DIR}. Download + unzip the fan data from "
            f"https://zenodo.org/records/3384388 first, then update DATASET_DIR."
        )

    machine_folders = find_machine_folders(DATASET_DIR)
    if not machine_folders:
        raise SystemExit(
            f"No normal/abnormal folder pairs found anywhere under {DATASET_DIR}. "
            f"Run: find \"{DATASET_DIR}\" -maxdepth 4 -type d   to see what's actually in there."
        )

    for machine_id, (normal_dir, normal_prefix, abnormal_dir, abnormal_prefix) in sorted(machine_folders.items()):
        normal_vectors, normal_lengths = process_folder(normal_dir, "normal", normal_prefix)
        abnormal_vectors, abnormal_lengths = process_folder(abnormal_dir, "abnormal", abnormal_prefix)

        np.save(os.path.join(OUTPUT_DIR, f"{machine_id}_normal.npy"), normal_vectors)
        np.save(os.path.join(OUTPUT_DIR, f"{machine_id}_normal_lengths.npy"), normal_lengths)
        np.save(os.path.join(OUTPUT_DIR, f"{machine_id}_abnormal.npy"), abnormal_vectors)
        np.save(os.path.join(OUTPUT_DIR, f"{machine_id}_abnormal_lengths.npy"), abnormal_lengths)

        print(f"{machine_id}: {normal_vectors.shape[0]} normal vectors, "
              f"{abnormal_vectors.shape[0]} abnormal vectors")


if __name__ == "__main__":
    main()