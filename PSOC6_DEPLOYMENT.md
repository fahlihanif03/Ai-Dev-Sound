# Deploying the fan-anomaly autoencoders to the PSoC 6 AI Eval Kit

Reference doc for the on-device deployment of the DCASE fan-sound autoencoders
(`models_deepcraft/id_00/02/04/06_fan_autoencoder.h5`) to the
**CY8CKIT-062S2-AI** board, without DEEPCRAFT Studio (not installed on this
machine) - instead using raw TensorFlow Lite Micro via Infineon's
`ml-middleware` library, with a hand-ported C feature-extraction pipeline.

## Hardware / toolchain

- **Board**: CY8CKIT-062S2-AI (PSoC 6, part `CY8C624ABZI-S2D44`, **2MB flash**,
  1MB SRAM, onboard PDM mic). Connect via the **KitProg3** USB port (not the
  second "USB Device" port - that one enumerates as a different device, e.g.
  "DEEPCRAFT Streaming Device", and isn't programmable).
- **ModusToolbox**: installed at `/Applications/ModusToolbox/tools_3.8`.
  Programming tools (fw-loader, openocd) at `/Applications/ModusToolboxProgtools-1.9`.
- Confirm the board is detected:
  ```bash
  /Applications/ModusToolboxProgtools-1.9/fw-loader/bin/fw-loader --device-list
  ```
  Should show `KitProg3 CMSIS-DAP`.
- Serial console: shows up as `/dev/cu.usbmodemXXXXX` at 115200 baud (`screen
  -L /dev/cu.usbmodemXXXXX 115200`; logs to `screenlog.0` in the cwd; `Ctrl-A`
  `k` to quit, or `screen -S <name> -X quit` on a `-dmS`-started session).

## Two separate project locations

- **This repo** (`Ai Dev/Sound`, has a space in the path) - Python training
  pipeline, dataset, model conversion tooling.
- **`~/ModusToolbox-Projects/fan-anomaly-detector`** - the actual firmware
  project. ModusToolbox's build/project tools reject paths containing spaces,
  so the firmware **cannot** live inside this repo; it's a separate directory
  with generated C sources copied in from here.

## Why not DEEPCRAFT Studio

DEEPCRAFT Studio auto-generates the entire mic -> features -> network C
pipeline in one export (see `Ai-Dev-Sound-Windows/models/Gen/model.c` from an
earlier session). It's Windows-only and wasn't available here, so instead:

1. Models are exported as standard `.tflite` (int8-quantized) via TensorFlow.
2. The feature-extraction pipeline (sliding window -> Hamming -> RFFT -> mel
   filterbank -> log/clip -> contextual stacking) is hand-ported to C,
   matching `prepare_features_deepcraft.py` exactly, using CMSIS-DSP's
   `arm_rfft_fast_f32` for the FFT (from the `cmsis` ModusToolbox asset -
   already a dependency, no extra library needed).
3. Inference runs via Infineon's `ml-middleware` + `ml-tflite-micro`
   (`COMPONENTS=ML_TFLM CMSIS_DSP ML_INT8x8` in the Makefile) - a generic
   TFLite Micro wrapper, not tied to DEEPCRAFT's model format.

## The 2MB flash problem -> one model per build

A single float32 `.tflite` model is ~2.5MB - **doesn't fit** even alone.
`tools/convert_models.py` (in this repo) int8-quantizes each model
(~660KB each) and verifies the **window-level AUC** survives quantization
(not just raw output closeness - int8 noise feeds directly into the
reconstruction-error score) before accepting it. Even at 660KB, all four
resident simultaneously would still be tight, so **only one machine id's
model is ever compiled into a given firmware image**:

```bash
cd ~/ModusToolbox-Projects/fan-anomaly-detector
make build MACHINE_ID=id_00   # id_00 | id_02 | id_04 | id_06
make program MACHINE_ID=id_00
```

`Makefile`'s `CY_IGNORE` excludes the other three `models/id_XX/` folders
based on `MACHINE_ID` (default `id_00`), so switching machines means
rebuilding + reflashing, not a runtime button. Typical build: ~1.24MB /
2.10MB flash used.

## Regenerating models from scratch

```bash
cd "/Users/monmon/Desktop/Ai Dev/Sound"
source venv/bin/activate
python3 prepare_features_deepcraft.py          # -> features_deepcraft/
python3 train_autoencoder_deepcraft.py --machine_id id_00   # (and id_02/04/06)
python3 tools/convert_models.py                # -> tools/generated/*.h .c
```
`convert_models.py` also emits `mel_basis.h` / `hamming_window.h` (shared
across all 4, generated once from the same Python math the training pipeline
uses) and per-id `id_XX_params.h` (err_std + threshold).

Copy the generated files into the firmware project:
```bash
for id in id_00 id_02 id_04 id_06; do
  cp tools/generated/${id}_model_data.{c,h} tools/generated/${id}_params.h \
     ~/ModusToolbox-Projects/fan-anomaly-detector/models/$id/
done
```
Each `models/id_XX/active_model.h` is a small hand-written shim mapping the
id-specific symbol names to fixed `MODEL_BIN_DATA`/`MODEL_BIN_SIZE`/
`MODEL_THRESHOLD`/`MODEL_ERR_STD` names `main.c` uses - regenerate manually
if a param name changes.

## Firmware structure (`~/ModusToolbox-Projects/fan-anomaly-detector`)

- `main.c` - PDM mic capture (DMA double-buffer, reused from Infineon's
  `mtb-example-ml-deepcraft-deploy-audio` template - generic HAL/DMA setup,
  nothing DEEPCRAFT-specific), feature extraction, int8 quantize -> TFLite
  Micro inference -> dequantize, reconstruction-error scoring, LED/UART.
- `feature_extract/feature_extract.c` - the hand-ported DSP pipeline.
  **Verified** against the Python reference before ever touching hardware:
  see `host_test/main.c`, a native (Mac, not ARM) driver that reads a WAV,
  runs it through this exact C code, and diffs the output against
  `prepare_features_deepcraft.wav_to_deepcraft_features()` - matched to
  ~0.002 max diff (float32 rounding). Rebuild the host test with:
  ```bash
  CMSIS=~/ModusToolbox-Projects/mtb_shared/cmsis/release-v5.8.2/COMPONENT_CMSIS_DSP
  gcc -std=c99 -I "$CMSIS/Include" -I feature_extract \
    host_test/main.c feature_extract/feature_extract.c \
    $(find "$CMSIS/Source/TransformFunctions" -name '*.c' ! -name 'arm_mfcc*' ! -name 'arm_dct4*' ! -name 'arm_rfft_q1*' ! -name 'arm_rfft_q3*' ! -name 'arm_rfft_init_q1*' ! -name 'arm_rfft_init_q3*') \
    "$CMSIS"/Source/CommonTables/*.c -lm -o /tmp/fe_host_test
  ```
- `models/id_XX/` - per-machine model data + params (see above).
- `tools/patch_deepcraft_model.py` - **unused** in the current (non-DEEPCRAFT)
  build, kept from an earlier approach that namespaced DEEPCRAFT-generated
  `IMAI_*` symbols per machine id. Not needed for the TFLite Micro path.
- `tools/recalibrate_threshold.py` - see below.

## Scoring (must match `scoring.py` exactly)

Per-frame score = `mean((feature - reconstruction)^2 / err_std)` over 2048
dims. Window score = 90th percentile of frame scores over a 30-frame
(~2s) rolling window (`SCORE_WINDOW_FRAMES` / `SCORE_PERCENTILE` in
`main.c`). Anomaly if window score > threshold. `err_std` and threshold come
from `models/id_XX/id_XX_params.h`.

## LED indicator

No RGB LED on this board - `CYBSP_USER_LED1` (P5_3): blinks 3x at boot
(alive check, independent of serial), then **lit solid = anomaly**, **off =
normal**.

## Recalibrating thresholds for your actual hardware

The MIMII-dataset-derived thresholds assume MIMII's recording setup (mic,
distance, gain). This model type deliberately does **not** normalize input
loudness (to match what an on-device pipeline would do), so it's sensitive
to absolute recording level - a real fan on *this* mic at a different
distance/gain produces a different score scale entirely. Observed during
testing: id_00 scored ~1000 (threshold 0.89) with the fan held right next to
the mic (mic saturation/clipping), dropping to ~2.2 at a normal distance -
still needed recalibration since even that's a different scale than MIMII's.

**Process** (`tools/recalibrate_threshold.py`):
1. Flash the target machine id, let the fan run **normally** at a stable,
   reasonable distance from the mic.
2. Capture ~30s of live score output (the firmware already prints
   `score=X.XXXX` every window):
   ```bash
   screen -L -dmS calib /dev/cu.usbmodemXXXXX 115200
   sleep 30 && screen -S calib -X quit
   ```
3. Compute + patch the threshold (95th percentile of captured scores, same
   methodology as training):
   ```bash
   python3 tools/recalibrate_threshold.py screenlog.0 id_00 \
     ~/ModusToolbox-Projects/fan-anomaly-detector/models/id_00/id_00_params.h
   ```
4. Rebuild + reflash: `make build MACHINE_ID=id_00 && make program MACHINE_ID=id_00`

**Watch for transients contaminating the capture** - id_06's first
calibration caught a startup ramp (score climbing 5.5 -> 87 over 30s,
never plateauing), giving a threshold (80.2) way looser than the true
steady state (~6.4-7.0). A stable, flat trend across the whole capture
(spot-check with `grep -o "score=[0-9.]*" screenlog.0 | awk 'NR%50==0'`)
is the sign a capture is trustworthy before trusting its threshold.

## Current recalibrated thresholds (this hardware, as of last calibration)

| Machine | MIMII-derived threshold | Recalibrated threshold |
|---|---|---|
| id_00 | 0.8925 | 2.8507 |
| id_02 | 0.8093 | 10.0576 |
| id_04 | 0.8900 | 9.5341 |
| id_06 | 0.7170 | 7.0294 |

## Phone-speaker playback test (normal vs. abnormal WAV, post-recalibration)

With live-fan-calibrated thresholds in place, played MIMII `normal`/`abnormal`
clips for `id_00` through a phone speaker near the mic (~20s each, same clip
pair, same rough phone position). This is a genuinely different acoustic
domain from both the original MIMII mic rig and the live-fan calibration, so
absolute scores are expected to be off-scale relative to `id_XX_params.h`
thresholds - the useful signal is whether normal-vs-abnormal *separate* at
all, not whether they cross the live-fan threshold.

- **id_00**: inconsistent across two attempts - one run scored normal higher
  than abnormal (backwards), the other scored abnormal higher (correct) but
  with a steadily *escalating* abnormal trend (230 -> 1879 over 20s) more
  consistent with the hand-held phone drifting closer than with real
  content-driven separation. Given id_00's already-weak 82.7% training AUC,
  **don't trust id_00 outside its calibrated live-fan condition** - it's
  too sensitive to playback loudness/distance for this test method to say
  anything conclusive.
- **id_02**: consistent, meaningful separation - normal median 196.6 vs.
  abnormal median 599.2 (~3x), and both fluctuate *within* their own clip
  (17-213 normal, 192-842 abnormal) rather than monotonically drifting -
  much more consistent with genuine content-driven scoring than phone
  movement. This is real evidence id_02's model discriminates correctly;
  matches its strong 99% training AUC.
- id_04/id_06 not tested this way yet (session ended before covering them) -
  worth doing the same normal/abnormal phone-speaker comparison if picking
  this back up, ideally with the phone propped at a fixed distance rather
  than hand-held, to remove the position-drift confound seen with id_00.
- Board was left flashed with **id_02** at the end of this session.

## Known limitations / not yet validated

- Thresholds above are calibrated against **normal** fan operation only -
  none have been tested against an actual fault (no broken fan available to
  test with). The system reliably says "normal" for a healthy fan now, but
  its true-positive rate on real anomalies is unverified in the field
  (validated only offline, on the MIMII dataset, before deployment). The
  phone-speaker test above is the closest thing to a real anomaly test done
  so far, and even that only cleanly worked for id_02.
- `id_00` was the weakest model during training (82.7% AUC vs 95-99% for the
  other three) - treat its readings with more skepticism.
- Each model is trained on one specific physical fan unit from the MIMII
  dataset; generalization to a structurally different fan (blade count,
  motor type) is inherently limited by design, not a bug.
- Recalibration must be repeated per install location - if the board or mic
  ever move to a meaningfully different acoustic setup (room, distance,
  mounting), thresholds should be recaptured.
