"""
yamnet_helper.py

Wraps Google's pretrained YAMNet (521-class general audio event
classifier) as a sanity-check signal alongside the trained anomaly
detector - NOT as a defect classifier itself. YAMNet has never seen this
fan or its faults, so it can't tell healthy from faulty; what it's good
for is confirming the mic is actually hearing mechanical/fan-like sound
at all, catching cases where the anomaly score is meaningless because
the room is silent, someone's talking near the mic, or the machine
simply isn't running - situations a reconstruction-error score alone
can't distinguish from a real anomaly.

Requires: pip install tensorflow_hub
"""
import csv
import numpy as np
import tensorflow_hub as hub

YAMNET_URL = "https://tfhub.dev/google/yamnet/1"

# Labels this project actually cares about hearing - used to compute a
# single "does this sound mechanical/fan-like at all" score, separate
# from the raw top-1 class (which is often a near-miss like "Vehicle" or
# "White noise" even on genuinely mechanical audio).
MACHINERY_LABELS = {
    "Mechanical fan", "Air conditioning", "Machinery", "Engine",
    "Vibration", "Hum", "White noise", "Static",
}


class YAMNetClassifier:
    def __init__(self):
        print("Loading YAMNet (first run downloads ~15MB from tfhub.dev)...")
        self.model = hub.load(YAMNET_URL)
        class_map_path = self.model.class_map_path().numpy().decode("utf-8")
        with open(class_map_path) as f:
            self.class_names = [row["display_name"] for row in csv.DictReader(f)]
        print("YAMNet ready.")

    def classify(self, y, sr, top_n=3):
        """y: mono float32 waveform in [-1, 1]. Returns (top_labels, machinery_score)
        where top_labels is [(label, score), ...] and machinery_score is the
        summed confidence across MACHINERY_LABELS (0-1ish, not a probability)."""
        if sr != 16000:
            raise ValueError("YAMNet expects 16kHz audio")
        scores, _embeddings, _spectrogram = self.model(y.astype(np.float32))
        mean_scores = scores.numpy().mean(axis=0)

        top_idx = np.argsort(mean_scores)[::-1][:top_n]
        top_labels = [(self.class_names[i], float(mean_scores[i])) for i in top_idx]

        machinery_score = sum(
            float(mean_scores[i]) for i, name in enumerate(self.class_names)
            if name in MACHINERY_LABELS
        )
        return top_labels, machinery_score
