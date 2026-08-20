import os
import glob
import random
import numpy as np
import librosa
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, TensorDataset, random_split
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import roc_auc_score
from joblib import Parallel, delayed

# ==========================================
# 0. Configuration
# ==========================================
N_MELS = 128
FRAMES = 32          # widened from the 10-frame baseline; cheap for a dense model
TRAIN_HOLDOUT = 0.2  # fraction of normal files reserved for test (matches DCASE-style split)
VAL_SPLIT = 0.1
EARLY_STOP_PATIENCE = 5
SCORE_PERCENTILE = 90  # per-file score = this percentile of per-frame scores, not the mean

# ==========================================
# 1. Feature Extraction (Log-Mel + Framing)
# ==========================================
def extract_features(file_path, n_mels=N_MELS, frames=FRAMES, n_fft=1024, hop_length=512):
    """Loads 16kHz audio, computes Log-Mel spectrogram, and creates temporal sliding windows."""
    y, sr = librosa.load(file_path, sr=16000)
    mel_spec = librosa.feature.melspectrogram(
        y=y, sr=sr, n_fft=n_fft, hop_length=hop_length, n_mels=n_mels
    )
    log_mel = librosa.power_to_db(mel_spec, ref=np.max)

    vectors = []
    for t in range(log_mel.shape[1] - frames + 1):
        vector = log_mel[:, t : t + frames].flatten()
        vectors.append(vector)

    return np.array(vectors, dtype=np.float32)

def load_or_extract_features(file_list, cache_filename):
    if os.path.exists(cache_filename):
        print(f"Loading pre-cached features from: {cache_filename}")
        return np.load(cache_filename)
    else:
        print(f"Extracting features from {len(file_list)} files using multi-core parallel processing...")
        feats_list = Parallel(n_jobs=-1, prefer="threads")(
            delayed(extract_features)(f) for f in file_list
        )
        X = np.vstack(feats_list)
        np.save(cache_filename, X)
        print(f"Saved feature cache to: {cache_filename}")
        return X

# ==========================================
# 2. Autoencoder Model Architecture
# ==========================================
class DeepAutoencoder(nn.Module):
    def __init__(self, input_dim):
        super(DeepAutoencoder, self).__init__()
        self.encoder = nn.Sequential(
            nn.Linear(input_dim, 128), nn.BatchNorm1d(128), nn.ReLU(),
            nn.Linear(128, 128), nn.BatchNorm1d(128), nn.ReLU(),
            nn.Linear(128, 16)
        )
        self.decoder = nn.Sequential(
            nn.Linear(16, 128), nn.BatchNorm1d(128), nn.ReLU(),
            nn.Linear(128, 128), nn.BatchNorm1d(128), nn.ReLU(),
            nn.Linear(128, input_dim)
        )

    def forward(self, x):
        return self.decoder(self.encoder(x))

# ==========================================
# 3. Per-Machine-ID Training & Evaluation Loop
# ==========================================
base_dir = "/Users/monmon/Desktop/Ai Dev/Sound/fan6db"
cache_dir = os.path.join(base_dir, "cache_1d_improved")
os.makedirs(cache_dir, exist_ok=True)

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
# NOTE: MPS produced intermittent NaN losses on this model's wider 4096-dim input
# (not seen at the 1280-dim baseline). The dense model is cheap enough (~1M MACs/window)
# that CPU is plenty fast and avoids the instability entirely.
machine_ids = ["id_00", "id_02", "id_04", "id_06"]

auc_list = []
pauc_list = []

print(f"Device set to: {device}")
print(f"Config: FRAMES={FRAMES}, score_percentile={SCORE_PERCENTILE}, train_holdout={TRAIN_HOLDOUT}")
print("=== Starting fan6db 1D Dense Pipeline (improved scoring) ===")

for machine_id in machine_ids:
    print(f"\n----------------------------------------")
    print(f" Processing Fan Machine: {machine_id}")
    print(f"----------------------------------------")

    normal_files = sorted(glob.glob(os.path.join(base_dir, machine_id, "normal", "*.wav")))
    abnormal_files = sorted(glob.glob(os.path.join(base_dir, machine_id, "abnormal", "*.wav")))
    if len(normal_files) == 0:
        print(f"Warning: No normal files found for {machine_id}")
        continue

    rng = random.Random(42)
    normal_shuffled = normal_files[:]
    rng.shuffle(normal_shuffled)
    n_test_normal = int(len(normal_shuffled) * TRAIN_HOLDOUT)
    test_normal_files = normal_shuffled[:n_test_normal]
    train_files = normal_shuffled[n_test_normal:]
    test_files = test_normal_files + abnormal_files
    test_labels = [0] * len(test_normal_files) + [1] * len(abnormal_files)
    print(f"Train (normal): {len(train_files)} | Test: {len(test_normal_files)} normal + {len(abnormal_files)} abnormal")

    cache_path = os.path.join(cache_dir, f"X_train_{machine_id}_f{FRAMES}.npy")
    X_train = load_or_extract_features(train_files, cache_path)

    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)

    train_tensor = torch.tensor(X_train_scaled, dtype=torch.float32)
    full_dataset = TensorDataset(train_tensor, train_tensor)

    val_size = int(len(full_dataset) * VAL_SPLIT)
    train_size = len(full_dataset) - val_size
    train_subset, val_subset = random_split(
        full_dataset, [train_size, val_size],
        generator=torch.Generator().manual_seed(42)
    )

    train_loader = DataLoader(train_subset, batch_size=512, shuffle=True, pin_memory=(device.type == "cuda"))
    val_loader = DataLoader(val_subset, batch_size=512, shuffle=False, pin_memory=(device.type == "cuda"))
    print(f"Train windows: {train_size} | Val windows: {val_size}")

    input_dim = X_train_scaled.shape[1]
    model = DeepAutoencoder(input_dim).to(device)
    optimizer = torch.optim.Adam(model.parameters(), lr=1e-3)
    criterion = nn.MSELoss()

    epochs = 40
    best_val_loss = float("inf")
    epochs_without_improvement = 0
    best_state = None

    for epoch in range(epochs):
        model.train()
        train_loss_sum, train_count = 0.0, 0
        for batch_x, _ in train_loader:
            batch_x = batch_x.to(device, non_blocking=True)
            optimizer.zero_grad()
            reconstruction = model(batch_x)
            loss = criterion(reconstruction, batch_x)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=5.0)
            optimizer.step()
            train_loss_sum += loss.item() * batch_x.size(0)
            train_count += batch_x.size(0)
        train_loss = train_loss_sum / train_count

        model.eval()
        val_loss_sum, val_count = 0.0, 0
        with torch.no_grad():
            for batch_x, _ in val_loader:
                batch_x = batch_x.to(device, non_blocking=True)
                reconstruction = model(batch_x)
                loss = criterion(reconstruction, batch_x)
                val_loss_sum += loss.item() * batch_x.size(0)
                val_count += batch_x.size(0)
        val_loss = val_loss_sum / val_count

        print(f"  Epoch {epoch + 1:>2}/{epochs} | train_loss: {train_loss:.5f} | val_loss: {val_loss:.5f}")

        if val_loss < best_val_loss:
            best_val_loss = val_loss
            epochs_without_improvement = 0
            best_state = {k: v.detach().clone() for k, v in model.state_dict().items()}
        else:
            epochs_without_improvement += 1
            if epochs_without_improvement >= EARLY_STOP_PATIENCE:
                print(f"  Early stopping at epoch {epoch + 1} (no val improvement in {EARLY_STOP_PATIENCE} epochs)")
                break

    if best_state is not None:
        model.load_state_dict(best_state)
    model.eval()

    # ---- Fit per-dimension error statistics on the held-out validation windows ----
    # (diagonal-Mahalanobis: normalizes each of the 4096 error dimensions by its own
    #  variance under normal conditions, instead of treating every dimension equally)
    val_errors = []
    with torch.no_grad():
        for batch_x, _ in val_loader:
            batch_x = batch_x.to(device, non_blocking=True)
            reconstruction = model(batch_x)
            err = (batch_x - reconstruction) ** 2
            val_errors.append(err.cpu().numpy())
    val_errors = np.vstack(val_errors)
    err_mean = val_errors.mean(axis=0)
    err_std = val_errors.std(axis=0) + 1e-8

    # 3. Evaluate on the held-out normal + abnormal test set
    print(f"Evaluating {len(test_files)} test files...")
    test_feats_list = Parallel(n_jobs=-1, prefer="threads")(
        delayed(extract_features)(f) for f in test_files
    )

    id_y_true = []
    id_y_scores = []
    with torch.no_grad():
        for f, label, feats in zip(test_files, test_labels, test_feats_list):
            feats_scaled = scaler.transform(feats)
            feats_tensor = torch.tensor(feats_scaled, dtype=torch.float32).to(device)

            reconstructed = model(feats_tensor)
            sq_err = ((feats_tensor - reconstructed) ** 2).cpu().numpy()

            # per-dimension normalized error, averaged per frame -> "diagonal Mahalanobis" score
            frame_scores = np.mean(sq_err / err_std, axis=1)
            # percentile pooling instead of mean: emphasizes the worst frames in the clip
            file_anomaly_score = np.percentile(frame_scores, SCORE_PERCENTILE)

            id_y_true.append(label)
            id_y_scores.append(file_anomaly_score)

    id_auc = roc_auc_score(id_y_true, id_y_scores)
    id_pauc = roc_auc_score(id_y_true, id_y_scores, max_fpr=0.1)

    print(f"[{machine_id}] AUC: {id_auc * 100:.2f}% | pAUC (max_fpr=0.1): {id_pauc * 100:.2f}%")

    auc_list.append(id_auc)
    pauc_list.append(id_pauc)

# ==========================================
# 4. Summary
# ==========================================
mean_auc = np.mean(auc_list)
mean_pauc = np.mean(pauc_list)

print("\n==========================================")
print(f"Mean AUC across all IDs:  {mean_auc * 100:.2f}%")
print(f"Mean pAUC across all IDs: {mean_pauc * 100:.2f}%")
print("==========================================")
