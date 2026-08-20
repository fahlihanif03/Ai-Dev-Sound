import os
os.environ["TF_USE_LEGACY_KERAS"] = "1"
import numpy as np
from tensorflow import keras
from sklearn.metrics import roc_auc_score

from prepare_features import N_MELS, FRAMES, WINDOW_SECONDS, vectors_per_window
from scoring import fit_error_stats, score_vectors, iter_windows

FEATURES_DIR = "features"
INPUT_DIM = N_MELS * FRAMES

normal = np.load(os.path.join(FEATURES_DIR, "id_00_normal.npy"))
normal_lengths = np.load(os.path.join(FEATURES_DIR, "id_00_normal_lengths.npy"))
abnormal = np.load(os.path.join(FEATURES_DIR, "id_00_abnormal.npy"))
abnormal_lengths = np.load(os.path.join(FEATURES_DIR, "id_00_abnormal_lengths.npy"))

mean = normal.mean(axis=0, keepdims=True)
std = normal.std(axis=0, keepdims=True) + 1e-6
normal_norm = (normal - mean) / std
abnormal_norm = (abnormal - mean) / std

n_files = len(normal_lengths)
n_val_files = max(1, int(0.1 * n_files))
rng = np.random.default_rng(42)
file_order = rng.permutation(n_files)
val_files, train_files = set(file_order[:n_val_files]), set(file_order[n_val_files:])
file_starts = np.concatenate([[0], np.cumsum(normal_lengths)])
train_mask = np.zeros(len(normal_norm), dtype=bool)
for i in train_files:
    train_mask[file_starts[i]: file_starts[i + 1]] = True

x_val_normal = normal_norm[~train_mask]
val_lengths = normal_lengths[sorted(val_files)]

model = keras.models.load_model("models/id_00_fan_autoencoder.h5")

err_mean, err_std = fit_error_stats(model, x_val_normal)
window_size = vectors_per_window(WINDOW_SECONDS)
normal_scores = np.array([score_vectors(w, model, err_std) for w in iter_windows(x_val_normal, val_lengths, window_size)])
abnormal_scores = np.array([score_vectors(w, model, err_std) for w in iter_windows(abnormal_norm, abnormal_lengths, window_size)])

labels = np.concatenate([np.zeros(len(normal_scores)), np.ones(len(abnormal_scores))])
scores = np.concatenate([normal_scores, abnormal_scores])
print(f"\n[BASELINE - existing original model, same held-out split] AUC: {roc_auc_score(labels, scores)*100:.2f}%  pAUC: {roc_auc_score(labels, scores, max_fpr=0.1)*100:.2f}%")
