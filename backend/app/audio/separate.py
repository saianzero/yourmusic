import hashlib
import os
from functools import lru_cache
from pathlib import Path

import librosa
import numpy as np
import soundfile as sf
import torch

CACHE_DIR = Path(__file__).resolve().parents[2] / "cache" / "stems"
DEVICE = os.environ.get("RAGA_DEVICE", "cpu")


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


@lru_cache
def _model():
    from demucs.pretrained import get_model

    m = get_model("htdemucs")
    m.eval()
    return m.to(DEVICE)


def separate_vocals(path: Path) -> Path:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    out = CACHE_DIR / f"{file_sha256(path)}_vocals.wav"
    if out.exists():
        return out

    from demucs.apply import apply_model

    model = _model()
    audio, _ = librosa.load(path, sr=model.samplerate, mono=False)
    if audio.ndim == 1:
        audio = np.stack([audio, audio])
    wav = torch.from_numpy(audio).float()
    ref = wav.mean(0)
    wav = (wav - ref.mean()) / (ref.std() + 1e-8)
    with torch.no_grad():
        sources = apply_model(model, wav[None], device=DEVICE, progress=False, shifts=1)[0]
    vocals = sources[model.sources.index("vocals")] * (ref.std() + 1e-8) + ref.mean()
    sf.write(out, vocals.cpu().numpy().T, model.samplerate)
    return out
