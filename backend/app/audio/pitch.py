import os
from dataclasses import dataclass
from pathlib import Path

import librosa
import numpy as np

SR = 16000
HOP = 160
FMIN, FMAX = 50.0, 1100.0
DEVICE = os.environ.get("RAGA_DEVICE", "cpu")
CREPE_MODEL = os.environ.get("RAGA_CREPE_MODEL", "tiny")


@dataclass
class PitchTrack:
    times: np.ndarray
    f0: np.ndarray
    confidence: np.ndarray
    hop_seconds: float = HOP / SR


def _crepe(audio: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    import torch
    import torchcrepe

    x = torch.from_numpy(audio).float()[None]
    f0, pd = torchcrepe.predict(
        x, SR, hop_length=HOP, fmin=FMIN, fmax=FMAX, model=CREPE_MODEL,
        return_periodicity=True, batch_size=512, device=DEVICE,
    )
    pd = torchcrepe.filter.median(pd, 3)
    f0 = torchcrepe.filter.median(f0, 3)
    return f0[0].cpu().numpy(), pd[0].cpu().numpy()


def _pyin(audio: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    f0, _, prob = librosa.pyin(audio, fmin=FMIN, fmax=FMAX, sr=SR, hop_length=HOP)
    return np.nan_to_num(f0), prob


def extract_pitch(path: Path, backend: str = "crepe") -> PitchTrack:
    audio, _ = librosa.load(path, sr=SR, mono=True)
    if backend == "crepe":
        try:
            f0, conf = _crepe(audio)
        except ImportError:
            f0, conf = _pyin(audio)
    else:
        f0, conf = _pyin(audio)
    n = min(len(f0), len(conf))
    times = np.arange(n) * HOP / SR
    return PitchTrack(times, f0[:n], conf[:n])
