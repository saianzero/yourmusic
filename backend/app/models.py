from typing import Literal

from pydantic import BaseModel


class RagaCandidate(BaseModel):
    name: str
    tradition: str
    score: float
    reasons: list[str]


class IdentifyRequest(BaseModel):
    phrase: str
    tradition: str | None = None
    top_k: int = 5


class IdentifyResponse(BaseModel):
    swara_histogram: list[float]
    candidates: list[RagaCandidate]


class TonicOut(BaseModel):
    hz: float
    strength: float
    raga_fit: float
    best_raga: str


class MotifOut(BaseModel):
    pcs: list[int]
    count: int


class AnalysisOut(BaseModel):
    tonic_hz: float
    tonic_candidates: list[TonicOut]
    swara_histogram: list[float]
    candidates: list[RagaCandidate]
    tempo_bpm: float
    gamaka_ratio: float
    n_notes: int
    motifs: list[MotifOut]


class AnalyzeJob(BaseModel):
    id: str
    status: Literal["running", "done", "error"]
    stage: str
    result: AnalysisOut | None = None
    error: str | None = None


class TonicOverride(BaseModel):
    tonic_hz: float


class GenerateRequest(BaseModel):
    raga: str
    tonic_hz: float = 220.0
    tempo_bpm: float = 90.0
    bars: int = 8
    seed: int | None = None
    drone: bool = True


class GenNoteOut(BaseModel):
    semitone: int
    beats: float
    name: str


class GenerateResponse(BaseModel):
    raga: str
    tonic_hz: float
    tempo_bpm: float
    notes: list[GenNoteOut]
    midi_base64: str
