import base64
import shutil
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from .audio.pipeline import AnalysisResult, analyze_track, extract_track
from .audio.pitch import PitchTrack
from .generate.grammar import generate, to_names
from .generate.render import render_midi
from .models import (
    AnalysisOut, AnalyzeJob, GenerateRequest, GenerateResponse, GenNoteOut, IdentifyRequest, IdentifyResponse,
    MotifOut, RagaCandidate, TonicOverride,
)
from .raga.db import get_raga, load_ragas
from .raga.identify import histogram, identify
from .raga.swara import parse_phrase

UPLOAD_DIR = Path(__file__).resolve().parents[1] / "uploads"
ALLOWED_SUFFIXES = {".mp3", ".wav", ".flac", ".m4a", ".ogg", ".aac"}

app = FastAPI(title="Raga API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:5174"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@dataclass
class Job:
    id: str
    path: Path
    tradition: str | None
    separate: bool
    status: str = "running"
    stage: str = "queued"
    track: PitchTrack | None = None
    result: AnalysisResult | None = None
    error: str | None = None


_jobs: dict[str, Job] = {}
_executor = ThreadPoolExecutor(max_workers=1)


def _to_out(r: AnalysisResult) -> AnalysisOut:
    return AnalysisOut(
        tonic_hz=r.tonic_hz,
        tonic_candidates=[asdict(c) for c in r.tonic_candidates],
        swara_histogram=r.swara_histogram,
        candidates=[RagaCandidate(**asdict(c)) for c in r.candidates],
        tempo_bpm=r.tempo_bpm,
        gamaka_ratio=r.gamaka_ratio,
        n_notes=r.n_notes,
        motifs=[MotifOut(pcs=p, count=c) for p, c in r.motifs],
    )


def _job_out(j: Job) -> AnalyzeJob:
    return AnalyzeJob(
        id=j.id, status=j.status, stage=j.stage,
        result=_to_out(j.result) if j.result else None, error=j.error,
    )


def _run(job: Job) -> None:
    def progress(stage: str) -> None:
        job.stage = stage

    try:
        job.track = extract_track(job.path, separate=job.separate, progress=progress)
        job.result = analyze_track(job.track, job.path, tradition=job.tradition, progress=progress)
        job.status, job.stage = "done", "done"
    except Exception as e:
        job.status, job.stage, job.error = "error", "error", f"{type(e).__name__}: {e}"


@app.get("/health")
def health():
    return {"ok": True, "ragas": len(load_ragas())}


@app.get("/ragas")
def ragas():
    return [{"name": r.name, "tradition": r.tradition, "aliases": r.aliases} for r in load_ragas()]


@app.post("/identify", response_model=IdentifyResponse)
def identify_phrase(req: IdentifyRequest):
    try:
        seq = parse_phrase(req.phrase)
    except ValueError as e:
        raise HTTPException(400, str(e))
    hist = histogram(seq)
    cands = identify(seq, hist, tradition=req.tradition, top_k=req.top_k)
    return IdentifyResponse(
        swara_histogram=hist.round(4).tolist(),
        candidates=[RagaCandidate(**asdict(c)) for c in cands],
    )


@app.post("/analyze", response_model=AnalyzeJob)
def analyze(
    file: UploadFile = File(...),
    tradition: str | None = Form(None),
    separate: bool = Form(True),
):
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in ALLOWED_SUFFIXES:
        raise HTTPException(400, f"unsupported file type {suffix!r}")
    if tradition not in (None, "", "carnatic", "hindustani"):
        raise HTTPException(400, "tradition must be carnatic or hindustani")
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    job_id = uuid.uuid4().hex
    dest = UPLOAD_DIR / f"{job_id}{suffix}"
    with open(dest, "wb") as f:
        shutil.copyfileobj(file.file, f)
    job = Job(job_id, dest, tradition or None, separate)
    _jobs[job_id] = job
    _executor.submit(_run, job)
    return _job_out(job)


@app.get("/analyze/{job_id}", response_model=AnalyzeJob)
def analyze_status(job_id: str):
    job = _jobs.get(job_id)
    if job is None:
        raise HTTPException(404, "job not found")
    return _job_out(job)


@app.post("/generate", response_model=GenerateResponse)
def generate_music(req: GenerateRequest):
    try:
        raga = get_raga(req.raga)
    except KeyError:
        raise HTTPException(404, f"unknown raga {req.raga!r}")
    if not 40 <= req.tonic_hz <= 1000 or not 30 <= req.tempo_bpm <= 300 or not 1 <= req.bars <= 64:
        raise HTTPException(400, "tonic_hz, tempo_bpm or bars out of range")
    notes = generate(raga, bars=req.bars, seed=req.seed)
    midi = render_midi(notes, req.tonic_hz, req.tempo_bpm, drone=req.drone)
    return GenerateResponse(
        raga=raga.name,
        tonic_hz=req.tonic_hz,
        tempo_bpm=req.tempo_bpm,
        notes=[GenNoteOut(semitone=n.semitone, beats=n.beats, name=nm) for n, nm in zip(notes, to_names(raga, notes))],
        midi_base64=base64.b64encode(midi).decode(),
    )


@app.post("/analyze/{job_id}/tonic", response_model=AnalyzeJob)
def analyze_override_tonic(job_id: str, body: TonicOverride):
    job = _jobs.get(job_id)
    if job is None or job.track is None:
        raise HTTPException(404, "job not found or not finished")
    if not 40 <= body.tonic_hz <= 1000:
        raise HTTPException(400, "tonic_hz out of range")
    prev = job.result
    job.result = analyze_track(job.track, job.path, tonic_hz=body.tonic_hz, tradition=job.tradition)
    if prev:
        job.result.tonic_candidates = prev.tonic_candidates
    return _job_out(job)
