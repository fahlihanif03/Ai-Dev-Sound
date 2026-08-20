import os
os.environ["TF_USE_LEGACY_KERAS"] = "1"
import glob
import numpy as np
import librosa
from tqdm import tqdm
from tensorflow import keras
from tensorflow.keras import layers
from sklearn.metrics import roc_auc_score

from prepare_features import N_MELS, FRAMES, WINDOW_SECONDS, frames_to_vectors, N_FFT, HOP_LENGTH, SAMPLE_RATE
from prepare_features_deepcraft import _HAMMING, _MEL_BASIS
from scoring import fit_error_stats, score_vectors, iter_windows

INPUT_DIM = N_MELS * FRAMES
EPS = 1e-6


def audio_to_features_v5(y, sr=SAMPLE_RATE):
    """True wide-dynamic-range log-power (natural log, no +1 compression,
    no per-file division) - a fixed global reference only, applied later
    as ordinary (x-mean)/std standardization, so it's deployable on-device
    as constants rather than a dynamic per-file computation."""
    y = y.astype(np.float32)
    n_frames = 1 + (len(y) - N_FFT) // HOP_LENGTH
    if n_frames < 1:
        return np.empty((N_MELS, 0), dtype=np.float32)
    out = np.empty((N_MELS, n_frames), dtype=np.float32)
    for i in range(n_frames):
        start = i * HOP_LENGTH
        frame = y[start:start + N_FFT] * _HAMMING
        spectrum = np.fft.rfft(frame)
        power = (np.abs(spectrum) ** 2).astype(np.float32)
        mel_energy = _MEL_BASIS @ power
        out[:, i] = np.log(mel_energy + EPS)
    return out


def vectors_per_window_v5(seconds, sr=SAMPLE_RATE):
    y = np.zeros(int(seconds * sr), dtype=np.float32)
    feats = audio_to_features_v5(y, sr)
    return frames_to_vectors(feats).shape[0]


def process_folder(folder, prefix):
    wav_paths = sorted(glob.glob(os.path.join(folder, f"{prefix}*.wav")))
    all_vectors, lengths = [], []
    for path in tqdm(wav_paths, desc=folder):
        y, sr = librosa.load(path, sr=SAMPLE_RATE, mono=True)
        feats = audio_to_features_v5(y, sr)
        vectors = frames_to_vectors(feats)
        all_vectors.append(vectors)
        lengths.append(vectors.shape[0])
    return np.concatenate(all_vectors, axis=0), np.array(lengths, dtype=np.int64)


normal, normal_lengths = process_folder("fan6db/Train_Normal_00", "normal_")
abnormal, abnormal_lengths = process_folder("fan6db/Test_Validation_00", "anomaly_")
print(f"normal: {normal.shape}, abnormal: {abnormal.shape}")

n_files = len(normal_lengths)
n_val_files = max(1, int(0.1 * n_files))
rng = np.random.default_rng(42)
file_order = rng.permutation(n_files)
val_files, train_files = set(file_order[:n_val_files]), set(file_order[n_val_files:])
file_starts = np.concatenate([[0], np.cumsum(normal_lengths)])
train_mask = np.zeros(len(normal), dtype=bool)
for i in train_files:
    train_mask[file_starts[i]: file_starts[i + 1]] = True

# fixed GLOBAL standardization - deployable on-device as constants,
# computed once from the training split only
mean = normal[train_mask].mean(axis=0, keepdims=True)
std = normal[train_mask].std(axis=0, keepdims=True) + 1e-6
normal_norm = (normal - mean) / std
abnormal_norm = (abnormal - mean) / std

x_train = normal_norm[train_mask]
x_val_normal = normal_norm[~train_mask]
val_lengths = normal_lengths[sorted(val_files)]

inputs = keras.Input(shape=(INPUT_DIM,))
x = layers.Dense(128, activation="relu")(inputs)
x = layers.Dense(128, activation="relu")(x)
x = layers.Dense(128, activation="relu")(x)
x = layers.Dense(8, activation="relu")(x)
x = layers.Dense(128, activation="relu")(x)
x = layers.Dense(128, activation="relu")(x)
x = layers.Dense(128, activation="relu")(x)
outputs = layers.Dense(INPUT_DIM, activation=None)(x)
model = keras.Model(inputs, outputs)
model.compile(optimizer=keras.optimizers.Adam(1e-3), loss="mse")

model.fit(x_train, x_train, validation_split=0.1, epochs=50, batch_size=512, shuffle=True, verbose=2)

err_mean, err_std = fit_error_stats(model, x_val_normal)
window_size = vectors_per_window_v5(WINDOW_SECONDS)
normal_scores = np.array([score_vectors(w, model, err_std) for w in iter_windows(x_val_normal, val_lengths, window_size)])
abnormal_scores = np.array([score_vectors(w, model, err_std) for w in iter_windows(abnormal_norm, abnormal_lengths, window_size)])

labels = np.concatenate([np.zeros(len(normal_scores)), np.ones(len(abnormal_scores))])
scores = np.concatenate([normal_scores, abnormal_scores])
print(f"\n[DIAGNOSTIC v5 - true log-power + global standardization] AUC: {roc_auc_score(labels, scores)*100:.2f}%  pAUC: {roc_auc_score(labels, scores, max_fpr=0.1)*100:.2f}%")
