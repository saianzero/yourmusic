from collections import Counter
from dataclasses import dataclass
from pathlib import Path

import librosa
import numpy as np

from .pitch import PitchTrack

CONF_MIN = 0.5
MIN_NOTE_FRAMES = 5


@dataclass
class Note:
    semitone: int
    frames: int


def swara_sequence(track: PitchTrack, tonic_hz: float, conf_min: float = CONF_MIN) -> list[Note]:
    voiced = (track.confidence >= conf_min) & (track.f0 > 0)
    semis = np.full(len(track.f0), np.nan)
    semis[voiced] = np.round(12 * np.log2(track.f0[voiced] / tonic_hz))

    notes: list[Note] = []
    cur, run = None, 0
    for s in semis:
        if np.isnan(s):
            if cur is not None and run >= MIN_NOTE_FRAMES:
                notes.append(Note(int(cur), run))
            cur, run = None, 0
        elif s == cur:
            run += 1
        else:
            if cur is not None and run >= MIN_NOTE_FRAMES:
                notes.append(Note(int(cur), run))
            cur, run = s, 1
    if cur is not None and run >= MIN_NOTE_FRAMES:
        notes.append(Note(int(cur), run))
    return notes


def gamaka_ratio(track: PitchTrack, notes: list[Note], conf_min: float = CONF_MIN) -> float:
    voiced = int(((track.confidence >= conf_min) & (track.f0 > 0)).sum())
    stable = sum(n.frames for n in notes)
    return round(1 - stable / voiced, 3) if voiced else 0.0


def motifs(notes: list[Note], n_min: int = 3, n_max: int = 5, top: int = 10) -> list[tuple[list[int], int]]:
    pcs = [n.semitone % 12 for n in notes]
    counts: Counter = Counter()
    for k in range(n_min, n_max + 1):
        for i in range(len(pcs) - k + 1):
            gram = tuple(pcs[i:i + k])
            if len(set(gram)) > 1:
                counts[gram] += 1
    return [(list(g), c) for g, c in counts.most_common(top) if c > 1]


def tempo_bpm(path: Path) -> float:
    y, sr = librosa.load(path, sr=22050, mono=True, duration=120)
    t, _ = librosa.beat.beat_track(y=y, sr=sr)
    return round(float(np.atleast_1d(t)[0]), 1)
