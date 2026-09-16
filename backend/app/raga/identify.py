from dataclasses import dataclass

import numpy as np

from .db import Raga, load_ragas
from .swara import pc, pc_name

W_SET, W_TRANS, W_VADI, W_PAKAD = 0.4, 0.3, 0.15, 0.15
PRESENCE_THRESHOLD = 0.03


@dataclass
class Candidate:
    name: str
    tradition: str
    score: float
    reasons: list[str]


def collapse(seq: list[int]) -> list[int]:
    out: list[int] = []
    for n in seq:
        if not out or out[-1] != n:
            out.append(n)
    return out


def histogram(seq: list[int], weights: list[float] | None = None) -> np.ndarray:
    h = np.zeros(12)
    w = weights if weights is not None else [1.0] * len(seq)
    for n, wt in zip(seq, w):
        h[pc(n)] += wt
    return h / h.sum() if h.sum() > 0 else h


def _count_subseq(hay: list[int], needle: list[int]) -> int:
    k = len(needle)
    if k == 0 or k > len(hay):
        return 0
    return sum(1 for i in range(len(hay) - k + 1) if hay[i:i + k] == needle)


def score_raga(raga: Raga, seq: list[int], hist: np.ndarray) -> Candidate:
    reasons: list[str] = []

    in_mass = float(sum(hist[p] for p in raga.scale))
    present = sum(1 for p in raga.scale if hist[p] >= PRESENCE_THRESHOLD)
    coverage = present / len(raga.scale)
    set_score = in_mass * (0.5 + 0.5 * coverage)
    reasons.append(f"{in_mass:.0%} of note mass inside scale; {present}/{len(raga.scale)} scale swaras present")

    seq_c = collapse(seq)
    legal = total = 0
    for a, b in zip(seq_c, seq_c[1:]):
        total += 1
        pair = (pc(a), pc(b))
        if (b > a and pair in raga.up_pairs) or (b < a and pair in raga.down_pairs):
            legal += 1
    trans_score = legal / total if total else 0.5
    reasons.append(f"{legal}/{total} transitions follow arohana/avarohana")

    peak = hist.max() if hist.max() > 0 else 1.0
    vadi_score = 0.6 * hist[raga.vadi] / peak + 0.4 * hist[raga.samvadi] / peak
    reasons.append(f"vadi {pc_name(raga.vadi)} at {hist[raga.vadi]:.0%}, samvadi {pc_name(raga.samvadi)} at {hist[raga.samvadi]:.0%}")

    pcs_c = collapse([pc(n) for n in seq_c])
    hits = sum(_count_subseq(pcs_c, collapse([pc(n) for n in p])) for p in raga.pakad)
    pakad_score = min(1.0, hits / max(1, len(raga.pakad)))
    reasons.append(f"{hits} characteristic phrase hits")

    score = W_SET * set_score + W_TRANS * trans_score + W_VADI * vadi_score + W_PAKAD * pakad_score
    return Candidate(raga.name, raga.tradition, round(float(score), 4), reasons)


def identify(
    seq: list[int],
    hist: np.ndarray | None = None,
    tradition: str | None = None,
    top_k: int = 5,
) -> list[Candidate]:
    hist = histogram(seq) if hist is None else hist
    ragas = [r for r in load_ragas() if tradition is None or r.tradition == tradition]
    ranked = sorted((score_raga(r, seq, hist) for r in ragas), key=lambda c: c.score, reverse=True)
    return ranked[:top_k]
