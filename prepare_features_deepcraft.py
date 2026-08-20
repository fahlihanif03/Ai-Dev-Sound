"""
prepare_features_deepcraft.py

Same job as prepare_features.py (extract log-mel features from fan6db WAV
files, ready for training), but using the EXACT feature-extraction math
DEEPCRAFT Studio generates for the on-device Preprocessor pipeline -
confirmed by reading the actual generated C source in
models/Gen/model.c, not by guessing at the Studio UI's field labels.

Why this exists: DEEPCRAFT's "Imagimob Speech Features" preset computes a
different formula than librosa's power_to_db(ref=np.max) (see
prepare_features.py / audio_to_log_mel). Rather than fight to replicate
librosa's dynamic per-clip dB scale with DEEPCRAFT's static primitive
blocks, we retrain against DEEPCRAFT's own convention so the trained
model matches what will actually run on the board bit-for-bit (up to
float32 rounding).

Confirmed against models/Gen/model.c:
  - Sliding Window: 1024-sample frames, hop 512, NO edge padding (unlike
    librosa's default center=True reflect-padding - framing starts at
    sample 0, trailing incomplete frame is dropped)
  - Hamming window: exact numpy.hamming(1024), verified against the
    embedded coefficient table (max diff ~3e-8, float32 rounding only)
  - Real FFT -> magnitude: sqrt(real**2 + imag**2) per bin (verified via
    __norm_f32 in the generated source) - magnitude, NOT power
  - Mel filterbank: HTK mel scale, UNNORMALIZED triangular filters,
    bin edges = floor((n_fft+1)*hz/sr) - verified: independently
    recomputed bin edges matched the embedded filter-point table exactly
    (66/66 values, for 64 filters + 2 boundary points)
  - Add 1, then natural log (logf), then clip to [0, 4]
  - Frame stacking: 32 consecutive 64-dim frames, stride 1 (a new
    2048-dim vector for every incoming frame), frame-major flatten -
    same order as frames_to_vectors() below, verified via the generated
    fixwin_dequeuef32(..., 1) stride argument

Usage:
    python prepare_features_deepcraft.py
"""

import os
import numpy as np
import librosa
from tqdm import tqdm

from prepare_features import (
    DATASET_DIR, SAMPLE_RATE, N_MELS, N_FFT, HOP_LENGTH, FRAMES,
    find_machine_folders, frames_to_vectors,
)

OUTPUT_DIR = "features_deepcraft"


def _htk_mel_filter_bank(sr=SAMPLE_RATE, n_fft=N_FFT, n_mels=N_MELS, fmin=0, fmax=8000):
    """Reconstructs DEEPCRAFT's exact mel filterbank matrix: HTK mel scale
    bin edges (floor((n_fft+1)*hz/sr), confirmed byte-for-byte against the
    embedded filter-point table in models/Gen/model.c), and unnormalized
    triangular ramp weights (transcribed directly from __mel_f32 in that
    same generated source - NOT librosa's mel filter, which uses a
    different construction and does not match, verified separately)."""
    def hz_to_mel_htk(f):
        return 2595 * np.log10(1 + f / 700.0)

    def mel_to_hz_htk(m):
        return 700 * (10 ** (m / 2595.0) - 1)

    mel_pts = np.linspace(hz_to_mel_htk(fmin), hz_to_mel_htk(fmax), n_mels + 2)
    hz_pts = mel_to_hz_htk(mel_pts)
    bin_pts = np.floor((n_fft + 1) * hz_pts / sr).astype(int)

    n_freq = n_fft // 2 + 1
    basis = np.zeros((n_mels, n_freq), dtype=np.float32)
    for f in range(n_mels):
        n0, n1, n2 = bin_pts[f], bin_pts[f + 1], bin_pts[f + 2]
        c0, c1 = n1 - n0, n2 - n1
        for i in range(0, c0 + 1):
            basis[f, i + n0] += i / c0
        for i in range(1, c1 + 1):
            basis[f, i + n1] += 1.0 - i / c1
    return basis


_HAMMING = np.hamming(N_FFT).astype(np.float32)
_MEL_BASIS = _htk_mel_filter_bank()


def audio_to_deepcraft_features(y, sr=SAMPLE_RATE):
    """Per-frame log-mel-like features, matching DEEPCRAFT's on-device
    Preprocessor exactly. Returns shape (N_MELS, n_frames), same shape
    convention as audio_to_log_mel() in prepare_features.py, so
    frames_to_vectors() can stack it into 2048-dim vectors unchanged."""
    y = y.astype(np.float32)
    n_frames = 1 + (len(y) - N_FFT) // HOP_LENGTH
    if n_frames < 1:
        return np.empty((N_MELS, 0), dtype=np.float32)

    out = np.empty((N_MELS, n_frames), dtype=np.float32)
    for i in range(n_frames):
        start = i * HOP_LENGTH
        frame = y[start:start + N_FFT] * _HAMMING
        spectrum = np.fft.rfft(frame)
        magnitude = np.abs(spectrum).astype(np.float32)
        mel_energy = _MEL_BASIS @ magnitude
        out[:, i] = np.clip(np.log(mel_energy + 1.0), 0.0, 4.0)
    return out


def wav_to_deepcraft_features(path):
    y, sr = librosa.load(path, sr=SAMPLE_RATE, mono=True)
    return audio_to_deepcraft_features(y, sr)


def vectors_per_window(seconds, sr=SAMPLE_RATE):
    """Same purpose as prepare_features.vectors_per_window(), but using
    this module's no-padding framing - the original version would
    overcount since librosa's STFT pads the signal by default and this
    pipeline deliberately doesn't (see model.c's fixwin_dequeuef32)."""
    y = np.zeros(int(seconds * sr), dtype=np.float32)
    feats = audio_to_deepcraft_features(y, sr)
    return frames_to_vectors(feats).shape[0]


def process_folder(folder, label, prefix=None):
    import glob
    pattern = f"{prefix}*.wav" if prefix else "*.wav"
    wav_paths = sorted(glob.glob(os.path.join(folder, pattern)))
    all_vectors = []
    lengths = []
    for path in tqdm(wav_paths, desc=f"{label}: {folder}"):
        feats = wav_to_deepcraft_features(path)
        vectors = frames_to_vectors(feats)
        all_vectors.append(vectors)
        lengths.append(vectors.shape[0])
    if not all_vectors:
        return np.empty((0, N_MELS * FRAMES), dtype=np.float32), np.array([], dtype=np.int64)
    return np.concatenate(all_vectors, axis=0), np.array(lengths, dtype=np.int64)


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    if not os.path.isdir(DATASET_DIR):
        raise SystemExit(f"Can't find {DATASET_DIR}.")

    machine_folders = find_machine_folders(DATASET_DIR)
    if not machine_folders:
        raise SystemExit(f"No normal/abnormal folder pairs found anywhere under {DATASET_DIR}.")

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
