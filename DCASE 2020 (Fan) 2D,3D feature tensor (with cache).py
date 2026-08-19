import os
import glob
import numpy as np
import librosa
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, TensorDataset
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import roc_auc_score
from joblib import Parallel, delayed

# ==========================================
# 1. Feature Extraction (2D Log-Mel Tensors)
# ==========================================
def extract_features(file_path, n_mels=128, frames=10, n_fft=1024, hop_length=512):
    """Loads 16kHz audio and computes 2D Log-Mel tensor windows (1, n_mels, frames)."""
    y, sr = librosa.load(file_path, sr=16000)
    
    mel_spec = librosa.feature.melspectrogram(
        y=y, sr=sr, n_fft=n_fft, hop_length=hop_length, n_mels=n_mels
    )
    log_mel = librosa.power_to_db(mel_spec, ref=np.max)
    
    vectors = []
    for t in range(log_mel.shape[1] - frames + 1):
        # Format as 2D spatial patch with 1 channel: Shape (1, n_mels, frames)
        patch = log_mel[:, t : t + frames][np.newaxis, :, :]
        vectors.append(patch)
        
    return np.array(vectors, dtype=np.float32)

def load_or_extract_features(file_list, cache_filename):
    """Checks if cached .npy features exist on disk. If not, extracts in parallel."""
    if os.path.exists(cache_filename):
        print(f"Loading pre-cached features from: {cache_filename}")
        return np.load(cache_filename)
    else:
        print(f"Extracting 2D features from {len(file_list)} files using multi-core processing...")
        feats_list = Parallel(n_jobs=-1, prefer="threads")(
            delayed(extract_features)(f) for f in file_list
        )
        X = np.vstack(feats_list)
        np.save(cache_filename, X)
        print(f"Saved feature cache to: {cache_filename}")
        return X

# ==========================================
# 2. 2D Convolutional Autoencoder Architecture
# ==========================================
class Conv2DAutoencoder(nn.Module):
    def __init__(self):
        super(Conv2DAutoencoder, self).__init__()
        # Encoder downsamples frequency dimensions while preserving temporal context
        self.encoder = nn.Sequential(
            nn.Conv2d(1, 32, kernel_size=3, stride=(2, 1), padding=1),
            nn.BatchNorm2d(32),
            nn.ReLU(),
            nn.Conv2d(32, 64, kernel_size=3, stride=(2, 1), padding=1),
            nn.BatchNorm2d(64),
            nn.ReLU(),
            nn.Conv2d(64, 128, kernel_size=3, stride=(2, 1), padding=1),
            nn.BatchNorm2d(128),
            nn.ReLU()
        )
        # Decoder reconstructs the 2D feature map
        self.decoder = nn.Sequential(
            nn.ConvTranspose2d(128, 64, kernel_size=3, stride=(2, 1), padding=1, output_padding=(1, 0)),
            nn.BatchNorm2d(64),
            nn.ReLU(),
            nn.ConvTranspose2d(64, 32, kernel_size=3, stride=(2, 1), padding=1, output_padding=(1, 0)),
            nn.BatchNorm2d(32),
            nn.ReLU(),
            nn.ConvTranspose2d(32, 1, kernel_size=3, stride=(2, 1), padding=1, output_padding=(1, 0))
        )

    def forward(self, x):
        encoded = self.encoder(x)
        decoded = self.decoder(encoded)
        return decoded

# ==========================================
# 3. Per-Machine-ID Training & Evaluation Loop
# ==========================================
base_dir = r"D:\MIMII Dataset\PSoC6_Fan_Project"
train_dir = os.path.join(base_dir, "Train_Normal")
test_dir = os.path.join(base_dir, "Test_Validation")
cache_dir = os.path.join(base_dir, "cache_2d")
os.makedirs(cache_dir, exist_ok=True)

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
machine_ids = ["id_00"]

auc_list = []
pauc_list = []

print(f"Device set to: {device}")
print("=== Starting 2D ConvAutoencoder Pipeline ===")

for machine_id in machine_ids:
    print(f"\n----------------------------------------")
    print(f" Processing Fan Machine: {machine_id}")
    print(f"----------------------------------------")
    
    # 1. Load Training Files
    train_files = glob.glob(os.path.join(train_dir, f"normal_{machine_id}_*.wav"))
    if len(train_files) == 0:
        print(f"Warning: No training files found for {machine_id} in {train_dir}")
        continue

    cache_path = os.path.join(cache_dir, f"X_train_2d_{machine_id}.npy")
    X_train = load_or_extract_features(train_files, cache_path)
    
    # Flatten 2D shapes (N, 1, 128, 10) to scale and reshape back
    N, C, H, W = X_train.shape
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train.reshape(N, -1)).reshape(N, C, H, W)
    
    train_tensor = torch.tensor(X_train_scaled, dtype=torch.float32)
    train_loader = DataLoader(
        TensorDataset(train_tensor, train_tensor), 
        batch_size=512, 
        shuffle=True, 
        pin_memory=(device.type == "cuda")
    )
    
    # 2. Train dedicated 2D Autoencoder
    model = Conv2DAutoencoder().to(device)
    optimizer = torch.optim.Adam(model.parameters(), lr=1e-3)
    criterion = nn.MSELoss()
    
    model.train()
    epochs = 40
    for epoch in range(epochs):
        for batch_x, _ in train_loader:
            batch_x = batch_x.to(device, non_blocking=True)
            optimizer.zero_grad()
            reconstruction = model(batch_x)
            loss = criterion(reconstruction, batch_x)
            loss.backward()
            optimizer.step()
            
    # 3. Test on specific Machine ID test set
    model.eval()
    test_files = glob.glob(os.path.join(test_dir, f"*{machine_id}_*.wav"))
    
    id_y_true = []
    id_y_scores = []
    
    print(f"Evaluating {len(test_files)} test files...")
    test_feats_list = Parallel(n_jobs=-1, prefer="threads")(
        delayed(extract_features)(f) for f in test_files
    )
    
    with torch.no_grad():
        for f, feats in zip(test_files, test_feats_list):
            filename = os.path.basename(f)
            label = 1 if "anomaly" in filename else 0
            
            # Scale test batch features using trained scaler
            N_t, C_t, H_t, W_t = feats.shape
            feats_scaled = scaler.transform(feats.reshape(N_t, -1)).reshape(N_t, C_t, H_t, W_t)
            feats_tensor = torch.tensor(feats_scaled, dtype=torch.float32).to(device)
            
            reconstructed = model(feats_tensor)
            
            # Compute MSE across spatial/channel dims (1, 2, 3)
            mse_per_frame = torch.mean((feats_tensor - reconstructed) ** 2, dim=(1, 2, 3))
            file_anomaly_score = torch.mean(mse_per_frame).item()
            
            id_y_true.append(label)
            id_y_scores.append(file_anomaly_score)
            
    # 4. Compute metrics for current Machine ID
    id_auc = roc_auc_score(id_y_true, id_y_scores)
    id_pauc = roc_auc_score(id_y_true, id_y_scores, max_fpr=0.1)
    
    print(f"[{machine_id}] AUC: {id_auc * 100:.2f}% | pAUC (max_fpr=0.1): {id_pauc * 100:.2f}%")
    
    auc_list.append(id_auc)
    pauc_list.append(id_pauc)

# ==========================================
# 4. Official DCASE Dataset Evaluation
# ==========================================
mean_auc = np.mean(auc_list)
mean_pauc = np.mean(pauc_list)

print("\n==========================================")
print(f"Official Mean AUC across all IDs:  {mean_auc * 100:.2f}%")
print(f"Official Mean pAUC across all IDs: {mean_pauc * 100:.2f}%")
print("==========================================")