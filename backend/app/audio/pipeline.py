from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from ..raga.identify import Candidate, histogram, identify
from .features import gamaka_ratio, motifs, swara_sequence, tempo_bpm
from .pitch import PitchTrack, extract_pitch
from .tonic import TonicCandidate, choose_tonic

Progress = Callable[[str], None]


@dataclass
class AnalysisResult:
    tonic_hz: float
    tonic_candidates: list[TonicCandidate]
    swara_histogram: list[float]
    candidates: list[Candidate]
    tempo_bpm: float
    gamaka_ratio: float
    n_notes: int
    motifs: list[tuple[list[int], int]] = field(default_factory=list)


def extract_track(
    path: Path,
    separate: bool = True,
    pitch_backend: str = "crepe",
    progress: Progress = lambda _: None,
) -> PitchTrack:
    melody_path = path
    if separate:
        progress("separating")
        from .separate import separate_vocals

        melody_path = separate_vocals(path)
    progress("pitch")
    return extract_pitch(melody_path, backend=pitch_backend)


def analyze_track(
    track: PitchTrack,
    path: Path,
    tonic_hz: float | None = None,
    tradition: str | None = None,
    progress: Progress = lambda _: None,
) -> AnalysisResult:
    progress("tonic")
    cands = choose_tonic(track, tradition) if tonic_hz is None else [TonicCandidate(tonic_hz, 1.0)]
    tonic = cands[0].hz if cands else 220.0

    progress("identify")
    notes = swara_sequence(track, tonic)
    seq = [n.semitone for n in notes]
    hist = histogram(seq, [float(n.frames) for n in notes])
    ragas = identify(seq, hist, tradition=tradition) if seq else []

    progress("tempo")
    return AnalysisResult(
        tonic_hz=tonic,
        tonic_candidates=cands,
        swara_histogram=hist.round(4).tolist(),
        candidates=ragas,
        tempo_bpm=tempo_bpm(path),
        gamaka_ratio=gamaka_ratio(track, notes),
        n_notes=len(notes),
        motifs=motifs(notes),
    )


def analyze_file(
    path: Path,
    tonic_hz: float | None = None,
    tradition: str | None = None,
    separate: bool = True,
    pitch_backend: str = "crepe",
    progress: Progress = lambda _: None,
) -> AnalysisResult:
    track = extract_track(path, separate, pitch_backend, progress)
    return analyze_track(track, path, tonic_hz, tradition, progress)
