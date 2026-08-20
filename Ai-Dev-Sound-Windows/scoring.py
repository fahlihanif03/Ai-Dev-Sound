"""
scoring.py

Shared anomaly-scoring logic used by train_autoencoder.py, evaluate_wav.py,
calibrate_threshold.py, live_monitor.py and live_spectrogram_monitor.py -
one canonical implementation instead of five copies drifting apart.

Two changes from the original flat-mean-MSE score (validated on fan6db,
see DCASE_Fan6dB_Improved_Report.md - this took mean pAUC from 56% to 78%
on the equivalent PyTorch experiment):

  1. Per-dimension error normalization ("diagonal Mahalanobis"): each
     feature dimension's squared reconstruction error is divided by that
     dimension's own variance (measured on held-out normal data), so
     naturally-noisy mel bins don't drown out bins that actually shift
     under a real fault.
  2. Percentile pooling instead of mean pooling across a window's frames:
     a short anomalous burst inside an otherwise-normal window survives
     instead of being averaged away.
"""
import numpy as np

SCORE_PERCENTILE = 90  # window score = this percentile of per-frame scores


def fit_error_stats(model, x_normal):
    """Compute per-dimension mean/std of squared reconstruction error on
    known-normal vectors (call this on a held-out normal validation set,
    never on training data itself)."""
    pred = model.predict(x_normal, verbose=0)
    sq_err = np.square(x_normal - pred)
    err_mean = sq_err.mean(axis=0)
    err_std = sq_err.std(axis=0) + 1e-8
    return err_mean, err_std


def iter_windows(vectors, lengths, window_size):
    """Regroup a flat (vectors, per-file lengths) pair - as saved by
    prepare_features.py - into fixed-size, non-overlapping windows,
    matching how live_monitor.py actually pools frames from one rolling
    mic capture. Windows never cross a file boundary, and a trailing
    remainder shorter than window_size is dropped (too little context to
    be a fair comparison to a full live window)."""
    pos = 0
    for length in lengths:
        file_vectors = vectors[pos: pos + length]
        pos += length
        for start in range(0, length - window_size + 1, window_size):
            yield file_vectors[start: start + window_size]


def score_vectors(vectors_norm, model, err_std, percentile=SCORE_PERCENTILE):
    """Score a batch of already-normalized feature vectors (one window's
    worth of frames) and return a single anomaly score for the window."""
    if vectors_norm.shape[0] == 0:
        return None
    pred = model.predict(vectors_norm, verbose=0)
    sq_err = np.square(vectors_norm - pred)
    frame_scores = np.mean(sq_err / err_std, axis=1)
    return float(np.percentile(frame_scores, percentile))
