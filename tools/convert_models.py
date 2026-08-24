"""
convert_models.py

Converts the 4 trained fan-autoencoder .h5 models (models_deepcraft/id_XX_fan_autoencoder.h5)
into float32 TFLite models, verifies the conversion is numerically faithful against the
original Keras model, and emits everything the firmware needs as C source:

  - id_XX_model_data.c/.h : the .tflite file as a const byte array
  - id_XX_params.h        : ERR_STD[2048] and THRESHOLD for that machine id, from
                             models_deepcraft/id_XX_norm_stats.npz
  - mel_basis.h            : the 64x513 HTK mel filterbank matrix (shared across all ids)
  - hamming_window.h       : the 1024-tap Hamming window (shared across all ids)

Run from the Sound repo root:
    python tools/convert_models.py
"""
import os
import sys

os.environ["TF_USE_LEGACY_KERAS"] = "1"
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import tensorflow as tf
from tensorflow import keras

from prepare_features_deepcraft import _HAMMING, _MEL_BASIS, vectors_per_window
from prepare_features import WINDOW_SECONDS
from scoring import iter_windows, score_vectors
from sklearn.metrics import roc_auc_score

MACHINE_IDS = ["id_00", "id_02", "id_04", "id_06"]
MODEL_DIR = "models_deepcraft"
FEATURES_DIR = "features_deepcraft"
OUT_DIR = os.path.join("tools", "generated")
N_VERIFY_VECTORS = 200
TOLERANCE = 1e-4
N_REP_VECTORS = 500  # representative dataset size for int8 calibration
MAX_AUC_DROP = 0.03  # quantized AUC must be within this of the float32 AUC


class TFLiteModel:
    """Wraps a tf.lite.Interpreter so it exposes the same .predict(X) shape
    scoring.py's score_vectors()/fit_error_stats() already expect, handling
    int8 quantize-in/dequantize-out transparently so the exact same scoring
    code can be reused to compare float32 vs int8 AUC apples-to-apples."""

    def __init__(self, tflite_model):
        self.interpreter = tf.lite.Interpreter(model_content=tflite_model)
        self.interpreter.allocate_tensors()
        self.in_detail = self.interpreter.get_input_details()[0]
        self.out_detail = self.interpreter.get_output_details()[0]

    def predict(self, x, verbose=0):
        in_scale, in_zero = self.in_detail["quantization"]
        out_scale, out_zero = self.out_detail["quantization"]
        out = np.zeros_like(x, dtype=np.float32)
        for i, vec in enumerate(x):
            if self.in_detail["dtype"] != np.float32:
                q = np.round(vec / in_scale + in_zero).astype(self.in_detail["dtype"])
            else:
                q = vec.astype(np.float32)
            self.interpreter.set_tensor(self.in_detail["index"], q[np.newaxis, :])
            self.interpreter.invoke()
            raw = self.interpreter.get_tensor(self.out_detail["index"])[0]
            if self.out_detail["dtype"] != np.float32:
                out[i] = (raw.astype(np.float32) - out_zero) * out_scale
            else:
                out[i] = raw
        return out


def emit_c_byte_array(name, data: bytes, out_dir):
    c_path = os.path.join(out_dir, f"{name}.c")
    h_path = os.path.join(out_dir, f"{name}.h")
    guard = f"_{name.upper()}_H_"

    with open(h_path, "w") as f:
        f.write(f"#ifndef {guard}\n#define {guard}\n\n")
        f.write("#include <stddef.h>\n\n")
        f.write(f"extern const unsigned char {name}[];\n")
        f.write(f"extern const unsigned int {name}_len;\n\n")
        f.write(f"#endif /* {guard} */\n")

    with open(c_path, "w") as f:
        f.write(f'#include "{name}.h"\n\n')
        f.write(f"const unsigned char {name}[] = {{\n")
        for i in range(0, len(data), 16):
            chunk = data[i:i + 16]
            f.write("    " + ", ".join(f"0x{b:02x}" for b in chunk) + ",\n")
        f.write("};\n")
        f.write(f"const unsigned int {name}_len = {len(data)};\n")

    return c_path, h_path


def emit_float_array_header(name, array, out_dir, shape_comment=""):
    guard = f"_{name.upper()}_H_"
    h_path = os.path.join(out_dir, f"{name}.h")
    flat = array.astype(np.float32).flatten()
    with open(h_path, "w") as f:
        f.write(f"#ifndef {guard}\n#define {guard}\n\n")
        if shape_comment:
            f.write(f"/* shape: {shape_comment} */\n")
        f.write(f"#define {name.upper()}_COUNT ({flat.size})\n\n")
        f.write(f"static const float {name}[{flat.size}] = {{\n")
        for i in range(0, flat.size, 8):
            chunk = flat[i:i + 8]
            f.write("    " + ", ".join(f"{v:.8e}f" for v in chunk) + ",\n")
        f.write("};\n\n")
        f.write(f"#endif /* {guard} */\n")
    return h_path


def _window_scores(scorer, normal, normal_lengths, abnormal, abnormal_lengths, err_std):
    window_size = vectors_per_window(WINDOW_SECONDS)
    normal_scores = np.array([
        score_vectors(w, scorer, err_std) for w in iter_windows(normal, normal_lengths, window_size)
    ])
    abnormal_scores = np.array([
        score_vectors(w, scorer, err_std) for w in iter_windows(abnormal, abnormal_lengths, window_size)
    ])
    return normal_scores, abnormal_scores


def _auc(normal_scores, abnormal_scores):
    labels = np.concatenate([np.zeros(len(normal_scores)), np.ones(len(abnormal_scores))])
    scores = np.concatenate([normal_scores, abnormal_scores])
    return roc_auc_score(labels, scores)


def convert_and_verify(machine_id, out_dir):
    h5_path = os.path.join(MODEL_DIR, f"{machine_id}_fan_autoencoder.h5")
    model = keras.models.load_model(h5_path)

    normal = np.load(os.path.join(FEATURES_DIR, f"{machine_id}_normal.npy"))
    normal_lengths = np.load(os.path.join(FEATURES_DIR, f"{machine_id}_normal_lengths.npy"))
    abnormal = np.load(os.path.join(FEATURES_DIR, f"{machine_id}_abnormal.npy"))
    abnormal_lengths = np.load(os.path.join(FEATURES_DIR, f"{machine_id}_abnormal_lengths.npy"))
    stats = np.load(os.path.join(MODEL_DIR, f"{machine_id}_norm_stats.npz"))
    err_std = stats["err_std"].astype(np.float32).flatten()

    # --- float32 baseline (sanity check the .h5 -> .tflite step itself) ---
    float_converter = tf.lite.TFLiteConverter.from_keras_model(model)
    float_tflite = float_converter.convert()

    rng = np.random.default_rng(0)
    idx = rng.choice(len(normal), size=min(N_VERIFY_VECTORS, len(normal)), replace=False)
    verify_vectors = normal[idx].astype(np.float32)
    keras_out = model.predict(verify_vectors, verbose=0)
    float_tflite_model = TFLiteModel(float_tflite)
    float_out = float_tflite_model.predict(verify_vectors)
    max_diff = np.max(np.abs(keras_out - float_out))
    print(f"{machine_id}: max |keras - float32 tflite| = {max_diff:.3e} over {len(verify_vectors)} vectors")
    if max_diff > TOLERANCE:
        raise SystemExit(
            f"{machine_id}: float32 TFLite conversion diverges from Keras by {max_diff:.3e} "
            f"(tolerance {TOLERANCE:.1e}) - do not deploy, investigate the converter output."
        )
    float_normal_scores, float_abnormal_scores = _window_scores(
        float_tflite_model, normal, normal_lengths, abnormal, abnormal_lengths, err_std)
    float_auc = _auc(float_normal_scores, float_abnormal_scores)

    # --- int8 quantization: the CY8CKIT-062S2-AI's 2MB flash can't fit even
    # one float32 model (~2.5MB), so quantize to int8 (~4x smaller) and
    # verify the *window-level AUC* survives quantization noise, not just
    # per-vector closeness - int8 error feeds straight into the anomaly
    # score via (x - recon)^2, so this is the check that actually matters. ---
    rep_idx = rng.choice(len(normal), size=min(N_REP_VECTORS, len(normal)), replace=False)
    rep_vectors = normal[rep_idx].astype(np.float32)

    def representative_dataset():
        for vec in rep_vectors:
            yield [vec[np.newaxis, :]]

    quant_converter = tf.lite.TFLiteConverter.from_keras_model(model)
    quant_converter.optimizations = [tf.lite.Optimize.DEFAULT]
    quant_converter.representative_dataset = representative_dataset
    quant_converter.target_spec.supported_ops = [tf.lite.OpsSet.TFLITE_BUILTINS_INT8]
    quant_converter.inference_input_type = tf.int8
    quant_converter.inference_output_type = tf.int8
    tflite_model = quant_converter.convert()

    quant_tflite_model = TFLiteModel(tflite_model)
    quant_normal_scores, quant_abnormal_scores = _window_scores(
        quant_tflite_model, normal, normal_lengths, abnormal, abnormal_lengths, err_std)
    quant_auc = _auc(quant_normal_scores, quant_abnormal_scores)

    print(f"{machine_id}: window AUC float32={float_auc*100:.2f}%  int8={quant_auc*100:.2f}%  "
          f"(model size {len(tflite_model)/1024:.0f} KB, was {len(float_tflite)/1024:.0f} KB float32)")
    if float_auc - quant_auc > MAX_AUC_DROP:
        raise SystemExit(
            f"{machine_id}: int8 quantization dropped window AUC from {float_auc*100:.2f}% to "
            f"{quant_auc*100:.2f}% (> {MAX_AUC_DROP*100:.0f} pt tolerance) - do not deploy this "
            f"quantized model, the reconstruction-error signal is too degraded."
        )

    emit_c_byte_array(f"{machine_id}_model_data", tflite_model, out_dir)

    # Recalibrate the threshold on the *quantized* model's own score
    # distribution (95th percentile of normal windows) - int8 quantization
    # noise shifts the reconstruction-error scale, so the float32-derived
    # threshold in norm_stats.npz is no longer the right cutoff on-device.
    threshold = float(np.percentile(quant_normal_scores, 95))
    print(f"{machine_id}: recalibrated threshold for int8 model: {threshold:.4f} "
          f"(float32 model's was {float(stats['threshold']):.4f})")
    upper = machine_id.upper()
    with open(os.path.join(out_dir, f"{machine_id}_params.h"), "w") as f:
        guard = f"_{upper}_PARAMS_H_"
        f.write(f"#ifndef {guard}\n#define {guard}\n\n")
        f.write(f"#define {upper}_THRESHOLD ({threshold:.8e}f)\n\n")
        f.write(f"static const float {machine_id}_err_std[2048] = {{\n")
        for i in range(0, 2048, 8):
            chunk = err_std[i:i + 8]
            f.write("    " + ", ".join(f"{v:.8e}f" for v in chunk) + ",\n")
        f.write("};\n\n")
        f.write(f"#endif /* {guard} */\n")

    print(f"{machine_id}: wrote {machine_id}_model_data.c/.h and {machine_id}_params.h "
          f"(threshold={threshold:.4f})")


def main():
    os.makedirs(OUT_DIR, exist_ok=True)

    emit_float_array_header("hamming_window", _HAMMING, OUT_DIR, shape_comment="1024")
    emit_float_array_header("mel_basis", _MEL_BASIS, OUT_DIR, shape_comment="64 x 513, row-major")
    print(f"Wrote hamming_window.h ({_HAMMING.size} taps) and "
          f"mel_basis.h ({_MEL_BASIS.shape[0]}x{_MEL_BASIS.shape[1]})")

    for machine_id in MACHINE_IDS:
        convert_and_verify(machine_id, OUT_DIR)

    print(f"\nAll models converted and verified. Output in {OUT_DIR}/")


if __name__ == "__main__":
    main()
