import argparse
from pathlib import Path

from app.audio.pipeline import analyze_file
from app.raga.swara import PC_NAMES


def main():
    p = argparse.ArgumentParser(description="Analyze an audio file and rank likely ragas")
    p.add_argument("path", type=Path)
    p.add_argument("--tonic", type=float, help="tonic (Sa) in Hz, skips detection")
    p.add_argument("--tradition", choices=["carnatic", "hindustani"])
    p.add_argument("--no-separate", action="store_true", help="skip Demucs vocal separation")
    p.add_argument("--pyin", action="store_true", help="use librosa pyin instead of torchcrepe")
    a = p.parse_args()

    r = analyze_file(
        a.path, tonic_hz=a.tonic, tradition=a.tradition, separate=not a.no_separate,
        pitch_backend="pyin" if a.pyin else "crepe", progress=lambda s: print(f"[{s}]"),
    )
    print(f"\ntonic: {r.tonic_hz} Hz   tempo: {r.tempo_bpm} bpm   notes: {r.n_notes}   gamaka: {r.gamaka_ratio}")
    print("tonic candidates:", ", ".join(f"{c.hz}Hz s={c.strength} fit={c.raga_fit:.2f} ({c.best_raga})" for c in r.tonic_candidates))
    print("\nswara histogram:")
    for name, v in zip(PC_NAMES, r.swara_histogram):
        print(f"  {name:6s} {'#' * int(v * 60):60s} {v:.1%}")
    print("\nragas:")
    for c in r.candidates:
        print(f"  {c.score:.3f}  {c.name} ({c.tradition})")
        for reason in c.reasons:
            print(f"           - {reason}")
    if r.motifs:
        print("\nmotifs:", "; ".join(" ".join(PC_NAMES[x] for x in m) + f" x{n}" for m, n in r.motifs[:5]))


if __name__ == "__main__":
    main()
