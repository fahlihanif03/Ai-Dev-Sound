"""
live_spectrogram_monitor.py

Shows a live scrolling spectrogram with the anomaly score and threshold
plotted directly underneath, sharing the same time axis - so you can
see exactly what the sound looked like whenever DEFECT gets flagged,
instead of just reading a number.

Also runs YAMNet (a general pretrained sound classifier) on the same
audio as a sanity check: it shows what the mic is actually hearing
("Mechanical fan", "Silence", "Speech", ...), so a DEFECT reading can be
told apart from "the anomaly score is meaningless because the mic isn't
even hearing the machine." YAMNet does NOT decide defect vs. okay -
that's still the trained autoencoder's job; YAMNet has never seen this
fan's faults and can't recognize them.

Requires: pip install matplotlib sounddevice tensorflow_hub

Usage:
    python live_spectrogram_monitor.py --machine_id id_00
    python live_spectrogram_monitor.py --machine_id id_00 --no-yamnet   # skip the sound-context check
"""
import os
os.environ["TF_USE_LEGACY_KERAS"] = "1"

from collections import deque

import argparse
import numpy as np
import sounddevice as sd
import matplotlib.pyplot as plt

from live_monitor import load_model_and_stats, score_audio
from prepare_features import audio_to_log_mel, N_MELS, SAMPLE_RATE, WINDOW_SECONDS
from mic_utils import require_input_device

MAX_WINDOWS = 60  # scrolling history length, shared by both panels
OKAY_COLOR = "#2f9e44"
DEFECT_COLOR = "#d43c2a"
NO_SIGNAL_COLOR = "#868e96"


def make_plot(threshold, machine_id, yamnet_enabled):
    plt.ion()
    fig, (ax_spec, ax_score) = plt.subplots(
        2, 1, figsize=(10, 7.6), sharex=True,
        gridspec_kw={"height_ratios": [2, 1]}
    )

    spec_buffer = np.full((N_MELS, MAX_WINDOWS), -80.0, dtype=np.float32)
    im = ax_spec.imshow(spec_buffer, aspect="auto", origin="lower",
                         extent=[0, MAX_WINDOWS, 0, N_MELS], vmin=-80, vmax=20,
                         cmap="magma")
    ax_spec.set_ylabel("mel band")
    ax_spec.set_title(f"Live spectrogram - {machine_id}")
    fig.colorbar(im, ax=ax_spec, label="dB", fraction=0.03, pad=0.02)

    scatter = ax_score.scatter([], [], s=50)
    ax_score.axhline(threshold, color="gray", linestyle="--", linewidth=1,
                      label=f"threshold = {threshold:.3f}")
    ax_score.set_xlim(0, MAX_WINDOWS)
    ax_score.set_xlabel("time (most recent windows, scrolling right)")
    ax_score.set_ylabel("anomaly score")
    ax_score.legend(loc="upper left")

    hearing_text = fig.text(0.5, 0.965, "", ha="center", va="top", fontsize=10.5)

    fig.tight_layout(rect=[0, 0, 1, 0.94] if yamnet_enabled else None)
    return fig, ax_spec, ax_score, im, scatter, spec_buffer, hearing_text


def update_plot(fig, ax_spec, ax_score, im, scatter, spec_buffer, column,
                 scores, colors, threshold, latest_score, latest_verdict, machine_id,
                 hearing_text, hearing_label, hearing_conf, machinery_score, machinery_min):
    spec_buffer = np.roll(spec_buffer, -1, axis=1)
    spec_buffer[:, -1] = column
    im.set_data(spec_buffer)

    n = len(scores)
    x_positions = list(range(MAX_WINDOWS - n, MAX_WINDOWS))
    scatter.set_offsets(np.column_stack([x_positions, list(scores)]) if n else np.empty((0, 2)))
    scatter.set_color(list(colors))
    ymax = max(max(scores) * 1.15, threshold * 1.2) if scores else threshold * 1.2
    ax_score.set_ylim(0, ymax)

    title_color = DEFECT_COLOR if latest_verdict == "DEFECT" else "black"
    ax_spec.set_title(f"Live spectrogram - {machine_id}  |  latest: {latest_verdict} (score={latest_score:.3f})",
                       color=title_color)

    if hearing_label is not None:
        if machinery_score < machinery_min:
            hearing_text.set_text(
                f"Hearing: \"{hearing_label}\" ({hearing_conf:.0%})  -  "
                f"low mechanical-sound confidence, anomaly score may not be meaningful right now"
            )
            hearing_text.set_color(NO_SIGNAL_COLOR)
        else:
            hearing_text.set_text(f"Hearing: \"{hearing_label}\" ({hearing_conf:.0%})")
            hearing_text.set_color("black")

    fig.canvas.draw_idle()
    return spec_buffer


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--machine_id", default="id_00")
    parser.add_argument("--device", type=int, default=None,
                         help="Input device index - run `python -m sounddevice` to list options")
    parser.add_argument("--no-yamnet", action="store_true",
                         help="Skip loading YAMNet - just the anomaly score, no sound-context check")
    parser.add_argument("--machinery-min", type=float, default=0.005,
                         help="YAMNet 'machinery-ish' confidence below which the anomaly score gets "
                              "flagged as possibly untrustworthy (mic not hearing the machine). "
                              "YAMNet's confidence varies a lot by recording domain - watch a few "
                              "known-normal windows first and raise/lower this to match what you see.")
    args = parser.parse_args()

    require_input_device(args.device)

    model, mean, std, err_std, threshold = load_model_and_stats(args.machine_id)
    print(f"Loaded model for {args.machine_id}, anomaly threshold = {threshold:.4f}")

    yamnet = None
    if not args.no_yamnet:
        from yamnet_helper import YAMNetClassifier
        yamnet = YAMNetClassifier()

    print("Listening... close the plot window or Ctrl+C to stop.\n")

    fig, ax_spec, ax_score, im, scatter, spec_buffer, hearing_text = make_plot(
        threshold, args.machine_id, yamnet_enabled=(yamnet is not None)
    )

    scores = deque(maxlen=MAX_WINDOWS)
    colors = deque(maxlen=MAX_WINDOWS)

    window_samples = int(WINDOW_SECONDS * SAMPLE_RATE)

    try:
        while plt.fignum_exists(fig.number):
            recording = sd.rec(window_samples, samplerate=SAMPLE_RATE, channels=1,
                                dtype="float32", device=args.device)
            sd.wait()
            y = recording[:, 0]

            log_mel = audio_to_log_mel(y)
            column = log_mel.mean(axis=1)  # one averaged spectrogram column for this window

            score = score_audio(y, model, mean, std, err_std)
            if score is None:
                continue

            verdict = "DEFECT" if score > threshold else "OKAY"
            scores.append(score)
            colors.append(DEFECT_COLOR if score > threshold else OKAY_COLOR)

            hearing_label = hearing_conf = machinery_score = None
            if yamnet is not None:
                top_labels, machinery_score = yamnet.classify(y, SAMPLE_RATE, top_n=1)
                hearing_label, hearing_conf = top_labels[0]

            spec_buffer = update_plot(fig, ax_spec, ax_score, im, scatter, spec_buffer, column,
                                       scores, colors, threshold, score, verdict, args.machine_id,
                                       hearing_text, hearing_label, hearing_conf, machinery_score,
                                       args.machinery_min)
            plt.pause(0.01)

    except KeyboardInterrupt:
        pass
    finally:
        print("\nStopped.")


if __name__ == "__main__":
    main()
