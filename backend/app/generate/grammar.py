import random
from collections import defaultdict
from dataclasses import dataclass

from ..raga.db import Raga
from ..raga.swara import pc

LOW, HIGH = -5, 19
PAKAD_WEIGHT = 3.0
STAY_WEIGHT = 0.08
FLIP_PROB = 0.12
PAKAD_INSERT_PROB = 0.2
DURATIONS = [(0.5, 5), (1.0, 6), (0.25, 3), (1.5, 1), (2.0, 1)]


@dataclass
class GenNote:
    semitone: int
    beats: float


def _shift_all(seq: tuple[int, ...]) -> list[list[int]]:
    return [[n + o for n in seq] for o in (-12, 0, 12)]


def build_transitions(raga: Raga) -> tuple[dict[int, dict[int, float]], dict[int, dict[int, float]]]:
    up: dict[int, dict[int, float]] = defaultdict(lambda: defaultdict(float))
    down: dict[int, dict[int, float]] = defaultdict(lambda: defaultdict(float))

    def add(seq: list[int], w: float) -> None:
        for a, b in zip(seq, seq[1:]):
            if not (LOW <= a <= HIGH and LOW <= b <= HIGH) or a == b:
                continue
            (up if b > a else down)[a][b] += w

    for s in _shift_all(raga.arohana):
        add(s, 1.0)
    for s in _shift_all(raga.avarohana):
        add(s, 1.0)
    for p in raga.pakad:
        for s in _shift_all(p):
            add(s, PAKAD_WEIGHT)
    return up, down


def _pick(rng: random.Random, options: dict[int, float]) -> int:
    keys = list(options)
    return rng.choices(keys, weights=[options[k] for k in keys])[0]


def _duration(rng: random.Random) -> float:
    return rng.choices([d for d, _ in DURATIONS], weights=[w for _, w in DURATIONS])[0]


def generate(raga: Raga, bars: int = 8, beats_per_bar: int = 4, seed: int | None = None) -> list[GenNote]:
    rng = random.Random(seed)
    up, down = build_transitions(raga)
    total = bars * beats_per_bar
    notes: list[GenNote] = [GenNote(0, 1.0)]
    cur, going_up, elapsed = 0, True, 1.0

    while elapsed < total - 1.0:
        if rng.random() < PAKAD_INSERT_PROB and raga.pakad:
            phrase = list(rng.choice(raga.pakad))
            offset = 12 if cur >= 10 and max(phrase) + 12 <= HIGH else (-12 if cur <= -2 and min(phrase) - 12 >= LOW else 0)
            for n in phrase:
                d = _duration(rng)
                if elapsed + d > total - 1.0:
                    break
                notes.append(GenNote(n + offset, d))
                elapsed += d
            cur = notes[-1].semitone
            going_up = rng.random() < 0.5
            continue

        if rng.random() < FLIP_PROB:
            going_up = not going_up
        table = up if going_up else down
        opts = dict(table.get(cur, {}))
        if not opts:
            going_up = not going_up
            opts = dict((up if going_up else down).get(cur, {}))
        if not opts:
            cur = 0
            continue
        if cur > 12 and rng.random() < 0.5:
            going_up = False
        if cur < 0 and rng.random() < 0.5:
            going_up = True
        opts[cur] = STAY_WEIGHT * sum(opts.values())
        cur = _pick(rng, opts)
        d = min(_duration(rng), total - 1.0 - elapsed)
        notes.append(GenNote(cur, d))
        elapsed += d

    landing = 0 if abs(cur) <= 6 else (12 if cur > 6 else -12)
    if cur != landing:
        notes.append(GenNote(landing, total - elapsed))
    else:
        notes[-1].beats += total - elapsed
    return notes


def to_names(raga: Raga, notes: list[GenNote]) -> list[str]:
    out = []
    for n in notes:
        name = raga.names.get(pc(n.semitone), "?")
        out.append(name + ("'" * (n.semitone // 12) if n.semitone >= 12 else "," if n.semitone < 0 else ""))
    return out
