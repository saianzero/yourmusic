import io
import math

import pretty_midi

from .grammar import GenNote

DRONE_PROGRAM = 104
MELODY_PROGRAM = 73


def tonic_to_midi(tonic_hz: float) -> int:
    return int(round(69 + 12 * math.log2(tonic_hz / 440.0)))


def render_midi(notes: list[GenNote], tonic_hz: float, tempo_bpm: float, drone: bool = True) -> bytes:
    pm = pretty_midi.PrettyMIDI(initial_tempo=tempo_bpm)
    base = tonic_to_midi(tonic_hz)
    spb = 60.0 / tempo_bpm

    melody = pretty_midi.Instrument(program=MELODY_PROGRAM, name="melody")
    t = 0.0
    for n in notes:
        end = t + n.beats * spb
        melody.notes.append(pretty_midi.Note(velocity=90, pitch=base + n.semitone, start=t, end=end - 0.02))
        t = end
    pm.instruments.append(melody)

    if drone:
        dr = pretty_midi.Instrument(program=DRONE_PROGRAM, name="drone")
        for p in (base - 12, base - 5):
            dr.notes.append(pretty_midi.Note(velocity=45, pitch=p, start=0.0, end=t))
        pm.instruments.append(dr)

    buf = io.BytesIO()
    pm.write(buf)
    return buf.getvalue()
