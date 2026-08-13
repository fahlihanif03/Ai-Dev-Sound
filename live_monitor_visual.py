"""
live_monitor_visual.py

Same idea as live_monitor.py, but shows a live scrolling graph instead
of text - green dots for OKAY, red dots for DEFECT, with the threshold
drawn as a dashed line. Works from VS Code (a plot window opens
alongside your editor) or a plain terminal.

Requires: pip install matplotlib sounddevice

Usage:
    python live_monitor_visual.py --machine_id id_00
"""
import os
os.environ["TF_USE_LEGACY_KERAS"] = "1"

from collections import deque

import argparse
import numpy as np
import sounddevice as sd
import matplotlib.pyplot as plt

from live_monitor import load_model_and_stats, score_audio, WINDOW_SECONDS
from prepare_features import SAMPLE_RATE

MAX_POINTS = 60  # rolling window - 60 readings * 2s ~= last 2 minutes
OKAY_COLOR = "#2f9e44"
DEFECT_COLOR = "#d43c2a"


def make_plot(threshold, machine_id):
    plt.ion()
    fig, ax = plt.subplots(figsize=(9, 5))
    scatter = ax.scatter([], [], s=60)
    ax.axhline(threshold, color="gray", linestyle="--", linewidth=1,
               label=f"threshold = {threshold:.3f}")
    ax.set_xlabel("reading #")
    ax.set_ylabel("reconstruction error (score)")
    ax.set_title(f"Live monitor - {machine_id}")
    ax.legend(loc="upper left")
    fig.tight_layout()
    return fig, ax, scatter


def update_plot(fig, ax, scatter, times, scores, colors, threshold, latest_score, latest_verdict, machine_id):
    scatter.set_offsets(np.column_stack([list(times), list(scores)]) if times else np.empty((0, 2)))
    scatter.set_color(list(colors))
    ax.set_xlim(max(0, times[-1] - MAX_POINTS + 1) if times else 0, (times[-1] if times else 0) + 1)
    ymax = max(max(scores) * 1.15, threshold * 1.2) if scores else threshold * 1.2
    ax.set_ylim(0, ymax)
    ax.set_title(f"Live monitor - {machine_id}  |  latest: {latest_verdict} (score={latest_score:.3f})")
    fig.canvas.draw_idle()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--machine_id", default="id_00")
    parser.add_argument("--device", type=int, default=None,
                         help="Input device index - run `python -m sounddevice` to list options")
    args = parser.parse_args()

    model, mean, std, threshold = load_model_and_stats(args.machine_id)
    print(f"Loaded model for {args.machine_id}, anomaly threshold = {threshold:.4f}")
    print("Listening... close the plot window or Ctrl+C to stop.\n")

    fig, ax, scatter = make_plot(threshold, args.machine_id)

    times = deque(maxlen=MAX_POINTS)
    scores = deque(maxlen=MAX_POINTS)
    colors = deque(maxlen=MAX_POINTS)

    window_samples = int(WINDOW_SECONDS * SAMPLE_RATE)
    reading_num = 0

    try:
        while plt.fignum_exists(fig.number):
            recording = sd.rec(window_samples, samplerate=SAMPLE_RATE, channels=1,
                                dtype="float32", device=args.device)
            sd.wait()
            score = score_audio(recording[:, 0], model, mean, std)
            if score is None:
                continue

            reading_num += 1
            verdict = "DEFECT" if score > threshold else "OKAY"

            times.append(reading_num)
            scores.append(score)
            colors.append(DEFECT_COLOR if score > threshold else OKAY_COLOR)

            update_plot(fig, ax, scatter, times, scores, colors, threshold, score, verdict, args.machine_id)
            plt.pause(0.01)

    except KeyboardInterrupt:
        pass
    finally:
        print("\nStopped.")


if __name__ == "__main__":
    main()
