import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.raga.db import Raga, load_ragas
from app.raga.identify import identify
from app.raga.swara import parse_phrase


def synthetic_sequence(raga: Raga) -> list[int]:
    seq: list[int] = []
    for _ in range(3):
        seq += list(raga.arohana) + list(raga.avarohana)
    for p in raga.pakad:
        seq += list(p) * 2
    return seq


@pytest.mark.parametrize("raga", load_ragas(), ids=lambda r: r.name)
def test_synthetic_sequence_identifies_top1(raga: Raga):
    cands = identify(synthetic_sequence(raga), tradition=raga.tradition, top_k=3)
    assert cands[0].name == raga.name, [(c.name, c.score) for c in cands]


def test_cross_tradition_equivalents_tie_at_top():
    seq = parse_phrase("S R2 G3 P D2 S' D2 P G3 R2 S G3 P D2 S' D2 P G3")
    names = {c.name for c in identify(seq, top_k=2)}
    assert names == {"Mohanam", "Bhupali"}


def test_identify_endpoint():
    client = TestClient(app)
    r = client.post("/identify", json={"phrase": "N, R G M P D N S' N D P M G R S", "tradition": "hindustani"})
    assert r.status_code == 200
    body = r.json()
    assert body["candidates"][0]["name"] == "Yaman"
    assert len(body["swara_histogram"]) == 12


def test_bad_token_returns_400():
    client = TestClient(app)
    assert client.post("/identify", json={"phrase": "S X Y"}).status_code == 400
