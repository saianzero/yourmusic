from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

import yaml

from .swara import parse_phrase, parse_token, pc

RAGAS_PATH = Path(__file__).with_name("ragas.yaml")


def _pairs(seq: list[int]) -> set[tuple[int, int]]:
    return {(pc(a), pc(b)) for a, b in zip(seq, seq[1:]) if a != b}


@dataclass(frozen=True)
class Raga:
    name: str
    tradition: str
    aliases: tuple[str, ...]
    parent: str
    arohana: tuple[int, ...]
    avarohana: tuple[int, ...]
    vadi: int
    samvadi: int
    pakad: tuple[tuple[int, ...], ...]
    names: dict[int, str]
    scale: frozenset[int] = field(init=False)
    up_pairs: frozenset[tuple[int, int]] = field(init=False)
    down_pairs: frozenset[tuple[int, int]] = field(init=False)

    def __post_init__(self):
        object.__setattr__(self, "scale", frozenset(pc(n) for n in self.arohana + self.avarohana))
        object.__setattr__(self, "up_pairs", frozenset(_pairs(list(self.arohana))))
        object.__setattr__(self, "down_pairs", frozenset(_pairs(list(self.avarohana))))


def _swara_names(*phrases: str) -> dict[int, str]:
    names: dict[int, str] = {}
    for tok in " ".join(phrases).split():
        bare = tok.rstrip("',")
        names.setdefault(pc(parse_token(bare)), bare)
    return names


def _from_yaml(d: dict) -> Raga:
    return Raga(
        names=_swara_names(d["arohana"], d["avarohana"]),
        name=d["name"],
        tradition=d["tradition"],
        aliases=tuple(d.get("aliases", [])),
        parent=d.get("parent", ""),
        arohana=tuple(parse_phrase(d["arohana"])),
        avarohana=tuple(parse_phrase(d["avarohana"])),
        vadi=pc(parse_token(d["vadi"])),
        samvadi=pc(parse_token(d["samvadi"])),
        pakad=tuple(tuple(parse_phrase(p)) for p in d.get("pakad", [])),
    )


@lru_cache
def load_ragas(path: Path = RAGAS_PATH) -> tuple[Raga, ...]:
    with open(path) as f:
        return tuple(_from_yaml(d) for d in yaml.safe_load(f))


def get_raga(name: str) -> Raga:
    for r in load_ragas():
        if r.name.lower() == name.lower():
            return r
    raise KeyError(name)
