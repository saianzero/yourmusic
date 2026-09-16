import base64
import io

import pretty_midi
import pytest
from fastapi.testclient import TestClient

from app.generate.grammar import generate, to_names
from app.generate.render import render_midi
from app.main import app
from app.raga.db import Raga, load_ragas
from app.raga.identify import identify
from app.raga.swara import pc


@pytest.mark.parametrize("raga", load_ragas(), ids=lambda r: r.name)
def test_generated_notes_stay_in_raga(raga: Raga):
    for seed in range(5):
        notes = generate(raga, bars=8, seed=seed)
        pcs = {pc(n.semitone) for n in notes}
        assert pcs <= raga.scale, (seed, pcs - raga.scale)
        assert abs(sum(n.beats for n in notes) - 32) < 1e-9
        assert all(n.beats > 0 for n in notes)


@pytest.mark.parametrize("raga", load_ragas(), ids=lambda r: r.name)
def test_generated_output_identifies_as_its_raga(raga: Raga):
    seq = [n.semitone for n in generate(raga, bars=16, seed=1)]
    top = identify(seq, tradition=raga.tradition, top_k=1)[0]
    assert top.name == raga.name, top


def test_seed_is_deterministic():
    raga = load_ragas()[0]
    a = generate(raga, bars=4, seed=42)
    b = generate(raga, bars=4, seed=42)
    assert [(n.semitone, n.beats) for n in a] == [(n.semitone, n.beats) for n in b]
    assert [(n.semitone, n.beats) for n in a] != [(n.semitone, n.beats) for n in generate(raga, bars=4, seed=43)]


def test_names_and_midi_render():
    raga = load_ragas()[0]
    notes = generate(raga, bars=4, seed=0)
    names = to_names(raga, notes)
    assert len(names) == len(notes) and "?" not in names
    pm = pretty_midi.PrettyMIDI(io.BytesIO(render_midi(notes, 220.0, 120.0)))
    assert [i.name for i in pm.instruments] == ["melody", "drone"]
    assert len(pm.instruments[0].notes) == len(notes)
    assert pm.instruments[0].notes[0].pitch == 57


def test_generate_endpoint():
    client = TestClient(app)
    r = client.post("/generate", json={"raga": "Yaman", "tonic_hz": 261.63, "tempo_bpm": 100, "bars": 4, "seed": 7})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["raga"] == "Yaman" and len(body["notes"]) > 4
    assert base64.b64decode(body["midi_base64"])[:4] == b"MThd"
    assert client.post("/generate", json={"raga": "Nope"}).status_code == 404
    assert client.post("/generate", json={"raga": "Yaman", "bars": 0}).status_code == 400
