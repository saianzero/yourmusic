import time
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app
from tests.test_audio_pipeline import synth_raga_wav


def test_analyze_job_flow_and_tonic_override(tmp_path: Path):
    wav = tmp_path / "hamsadhwani.wav"
    synth_raga_wav(wav, "Hamsadhwani")
    client = TestClient(app)

    with open(wav, "rb") as f:
        r = client.post("/analyze", files={"file": ("x.wav", f, "audio/wav")}, data={"tradition": "carnatic", "separate": "false"})
    assert r.status_code == 200, r.text
    job_id = r.json()["id"]

    for _ in range(120):
        body = client.get(f"/analyze/{job_id}").json()
        if body["status"] != "running":
            break
        time.sleep(0.5)
    assert body["status"] == "done", body
    assert body["result"]["candidates"][0]["name"] == "Hamsadhwani"
    assert abs(body["result"]["tonic_hz"] - 220.0) < 4

    r = client.post(f"/analyze/{job_id}/tonic", json={"tonic_hz": 246.94})
    assert r.status_code == 200
    assert r.json()["result"]["tonic_hz"] == 246.94
    assert r.json()["result"]["candidates"][0]["name"] != "Hamsadhwani"


def test_analyze_rejects_bad_suffix():
    client = TestClient(app)
    r = client.post("/analyze", files={"file": ("x.txt", b"hi", "text/plain")})
    assert r.status_code == 400
