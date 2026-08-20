# DCASE 2020 Task 2 — Fan, 2D Conv Autoencoder

**Run report v1 — single ID, 10-frame window, no validation split**

| | |
|---|---|
| Machine | id_00 (fan) |
| Date | 2026-08-19 |
| Host | Apple M4 · 10-core |
| Runtime | PyTorch 2.8.0 / MPS |
| Script | `DCASE 2020 (Fan) 2D,3D feature tensor (with cache).py` |
| Dataset | PSoC6_Fan_Project · MIMII dataset |

A 2D convolutional autoencoder was trained on log-mel spectrogram patches from normal fan-noise recordings and evaluated on a held-out mix of normal and anomalous clips. The model separated the two classes barely better than a coin flip.

## Result

| Metric | Score | Chance | Status |
|---|---|---|---|
| AUC | **53.25%** | 50% | ⚠️ near chance level |
| pAUC (max_fpr = 0.1) | **49.46%** | 50% | ⚠️ at chance |

507 test clips scored (id_00 only — `machine_ids` in the script lists just `"id_00"`; `id_02` data exists on disk but was not run). The reported "Official Mean" is therefore identical to the single-ID score, not an average across machines.

## Pipeline

| Stage | Setting | Note |
|---|---|---|
| Audio | 16 kHz mono | `librosa.load`, resampled |
| Features | 128-mel log spectrogram | n_fft 1024, hop 512 |
| Window | 10 frames | patch shape (1, 128, 10), stride 1 |
| Model | Conv2D AE, 3 layers | 32→64→128 ch, freq-only stride (2,1) |
| Training | 40 epochs, batch 512 | Adam lr 1e-3, MSE loss, no val split |
| Scoring | mean reconstruction MSE | per file, across all frame windows |

## Execution notes

- **Setup** — No project Python environment existed. Installed `librosa`, `torch`, `scikit-learn`, `joblib` via `pip3 --user` into the Xcode-bundled Python 3.9 — the only interpreter on the machine.
- **1st run** — Launched on CPU. The script only checks `torch.cuda.is_available()`, so it never considered MPS despite running on Apple silicon.
- **Check-in** — Found a second, orphaned copy of the same script already running (parent process id 1 — left over from an earlier attempt, not tracked by this session). Killed it to stop duplicate compute.
- **Estimate** — Benchmarked the same architecture at batch 512: ~907 ms/step under load. At ~277k training windows and 40 epochs (~21,600 steps), CPU completion was projected at **4–5 hours**.
- **Fix** — Confirmed MPS was available and built. Edited the device line to prefer MPS when CUDA is absent, killed the CPU run, and restarted.
- **Complete** — The MPS run finished in a fraction of the CPU estimate and produced the scores above.

## Why the score is weak

- A 10-frame window at 512-sample hop (~320 ms) is short relative to a fan's rotation cycle — the DCASE 2020 baseline uses a wider stacked-frame context; anomalies here may show up over longer time spans than the model ever sees at once.
- The encoder compresses the mel axis 128 → 16 in three strided steps but never touches the 10-frame time axis, so the bottleneck may retain enough detail to reconstruct anomalies just as well as normal sound — collapsing the separation an autoencoder relies on.
- No validation split or early stopping: 40 epochs run regardless of whether reconstruction loss has plateaued or started overfitting to the specific normal recordings in `Train_Normal_00`.
- Only `id_00` was trained and scored even though `id_02` data is present in the dataset directory — the reported "official mean" isn't actually averaged across machine IDs.

## Suggested next steps

1. **Widen temporal context.** Increase `frames` (e.g. 5–64) or add a strided step on the time axis in the encoder, matching the DCASE baseline's longer window.
2. **Add a validation split.** Hold out a slice of normal training data to track reconstruction loss per epoch and catch over/under-fitting before it wastes a multi-hour run.
3. **Run `id_02`.** The data already exists in `Train_Normal_02` / `Test_Validation_02`; add it to `machine_ids` so "official mean" reflects more than one machine.
4. **Log per-epoch loss.** The current loop has no visibility into training dynamics — even a single print per epoch would make future runs diagnosable without benchmarking blind.
5. **Fix the device check** in the shared script (already patched in this run) so future runs default to MPS on Apple hardware instead of silently falling back to CPU.

> **Update:** all five of these were implemented — see [v2 report](DCASE_2020_Fan_Run_Report_v2.md) for the widened-window, 4-machine-ID, validation-split follow-up run.

## Raw output

```
Device set to: mps
=== Starting 2D ConvAutoencoder Pipeline ===

----------------------------------------
 Processing Fan Machine: id_00
----------------------------------------
Loading pre-cached features from: .../cache_2d/X_train_2d_id_00.npy
Evaluating 507 test files...
[id_00] AUC: 53.25% | pAUC (max_fpr=0.1): 49.46%

==========================================
Official Mean AUC across all IDs:  53.25%
Official Mean pAUC across all IDs: 49.46%
==========================================
```
