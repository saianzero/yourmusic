from pathlib import Path

import numpy as np
import pytest
import soundfile as sf

from app.audio.pipeline import analyze_file
from app.raga.db import get_raga

SR = 16000
TONIC = 220.0


def synth_raga_wav(path: Path, raga_name: str, note_sec: float = 0.3) -> None:
    raga = get_raga(raga_name)
    seq = (list(raga.arohana) + list(raga.avarohana)) * 3
    for p in raga.pakad:
        seq += list(p) * 2
    out = []
    for semi in seq:
        f = TONIC * 2 ** (semi / 12)
        t = np.arange(int(SR * note_sec)) / SR
        env = np.minimum(1, np.minimum(t, note_sec - t) * 40)
        out.append(0.5 * env * np.sin(2 * np.pi * f * t))
    sf.write(path, np.concatenate(out).astype(np.float32), SR)


@pytest.mark.parametrize("raga_name,tradition", [("Mohanam", "carnatic"), ("Kalyani", "carnatic"), ("Bhairavi", "hindustani")])
def test_synthetic_audio_end_to_end(tmp_path: Path, raga_name: str, tradition: str):
    wav = tmp_path / f"{raga_name}.wav"
    synth_raga_wav(wav, raga_name)
    r = analyze_file(wav, tradition=tradition, separate=False, pitch_backend="pyin")

    cents_err = abs(1200 * np.log2(r.tonic_hz / TONIC))
    assert cents_err < 30, r.tonic_candidates
    assert r.candidates[0].name == raga_name, [(c.name, c.score) for c in r.candidates]
    assert r.n_notes > 20
