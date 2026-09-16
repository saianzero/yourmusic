from dataclasses import dataclass

import numpy as np
from scipy.ndimage import gaussian_filter1d
from scipy.signal import find_peaks

from ..raga.identify import histogram, identify
from .features import CONF_MIN, swara_sequence
from .pitch import PitchTrack

BIN_CENTS = 10
N_BINS = 1200 // BIN_CENTS
REF_HZ = 27.5
TONIC_LO, TONIC_HI = 110.0, 330.0


@dataclass
class TonicCandidate:
    hz: float
    strength: float
    raga_fit: float = 0.0
    best_raga: str = ""


def folded_histogram(track: PitchTrack, conf_min: float = CONF_MIN) -> np.ndarray:
    m = (track.confidence >= conf_min) & (track.f0 > 0)
    cents = 1200 * np.log2(track.f0[m] / REF_HZ)
    bins = (np.round(cents / BIN_CENTS).astype(int)) % N_BINS
    h = np.bincount(bins, weights=track.confidence[m], minlength=N_BINS).astype(float)
    return h / h.sum() if h.sum() > 0 else h


def _bin_to_hz(b: int, f0_voiced: np.ndarray) -> float:
    base = REF_HZ * 2 ** (b * BIN_CENTS / 1200)
    best_hz, best_mass = base, -1
    for k in range(1, 6):
        hz = base * 2 ** k
        if not TONIC_LO / 2 <= hz < TONIC_HI * 2:
            continue
        lo, hi = hz * 2 ** (-3 / 12), hz * 2 ** (14 / 12)
        mass = int(((f0_voiced >= lo) & (f0_voiced < hi)).sum())
        if mass > best_mass:
            best_hz, best_mass = hz, mass
    return round(best_hz, 2)


def tonic_candidates(track: PitchTrack, k: int = 4) -> list[TonicCandidate]:
    f0_voiced = track.f0[(track.confidence >= CONF_MIN) & (track.f0 > 0)]
    h = folded_histogram(track)
    ext = gaussian_filter1d(np.concatenate([h, h, h]), sigma=2)
    peaks, props = find_peaks(ext, height=ext.max() * 0.1, distance=6)
    keep = (peaks >= N_BINS) & (peaks < 2 * N_BINS)
    peaks, heights = peaks[keep] - N_BINS, props["peak_heights"][keep]
    order = np.argsort(heights)[::-1][:k]
    top = [(int(peaks[i]), float(heights[i])) for i in order]
    mx = top[0][1] if top else 1.0
    return [TonicCandidate(_bin_to_hz(b, f0_voiced), round(s / mx, 3)) for b, s in top]


def choose_tonic(track: PitchTrack, tradition: str | None = None) -> list[TonicCandidate]:
    cands = tonic_candidates(track)
    for c in cands:
        notes = swara_sequence(track, c.hz)
        seq = [n.semitone for n in notes]
        if not seq:
            continue
        hist = histogram(seq, [float(n.frames) for n in notes])
        best = identify(seq, hist, tradition=tradition, top_k=1)[0]
        c.raga_fit, c.best_raga = best.score, best.name
    cands.sort(key=lambda c: 0.35 * c.strength + 0.65 * c.raga_fit, reverse=True)
    return cands
