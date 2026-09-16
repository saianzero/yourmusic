CARNATIC = {
    "S": 0, "R1": 1, "R2": 2, "R3": 3, "G1": 2, "G2": 3, "G3": 4,
    "M1": 5, "M2": 6, "P": 7, "D1": 8, "D2": 9, "D3": 10, "N1": 9, "N2": 10, "N3": 11,
}
HINDUSTANI = {
    "S": 0, "r": 1, "R": 2, "g": 3, "G": 4, "m": 5, "M": 6,
    "P": 7, "d": 8, "D": 9, "n": 10, "N": 11,
}
PC_NAMES = ["S", "R1/r", "R2/R", "G2/g", "G3/G", "M1/m", "M2/M", "P", "D1/d", "D2/D", "N2/n", "N3/N"]


def parse_token(tok: str) -> int:
    octave = 0
    while tok.endswith("'"):
        octave += 12
        tok = tok[:-1]
    while tok.endswith(","):
        octave -= 12
        tok = tok[:-1]
    if tok in CARNATIC:
        return CARNATIC[tok] + octave
    if tok in HINDUSTANI:
        return HINDUSTANI[tok] + octave
    raise ValueError(f"unknown swara token: {tok!r}")


def parse_phrase(phrase: str) -> list[int]:
    return [parse_token(t) for t in phrase.split()]


def pc(n: int) -> int:
    return n % 12


def pc_name(n: int) -> str:
    return PC_NAMES[pc(n)]
