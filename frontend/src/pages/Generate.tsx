import { useEffect, useRef, useState } from "react";
import * as Tone from "tone";
import { Midi } from "@tonejs/midi";
import { type GenerateResponse, type RagaInfo, generateMusic, hzToNote, listRagas } from "../api";

export default function Generate({ initialTonic, initialRaga }: { initialTonic?: number; initialRaga?: string }) {
  const [ragas, setRagas] = useState<RagaInfo[]>([]);
  const [raga, setRaga] = useState(initialRaga ?? "");
  const [tonic, setTonic] = useState(initialTonic ?? 220);
  const [tempo, setTempo] = useState(90);
  const [bars, setBars] = useState(8);
  const [seed, setSeed] = useState<number>(() => Math.floor(Math.random() * 10000));
  const [drone, setDrone] = useState(true);
  const [result, setResult] = useState<GenerateResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [playing, setPlaying] = useState(false);
  const synths = useRef<Tone.PolySynth[]>([]);

  useEffect(() => {
    listRagas()
      .then((r) => {
        setRagas(r);
        if (!raga && r.length) setRaga(r[0].name);
      })
      .catch((e) => setError(String(e)));
    return stop;
  }, []);

  async function run() {
    setError(null);
    setBusy(true);
    stop();
    try {
      setResult(await generateMusic({ raga, tonic_hz: tonic, tempo_bpm: tempo, bars, seed, drone }));
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  }

  function stop() {
    Tone.getTransport().stop();
    Tone.getTransport().cancel();
    synths.current.forEach((s) => s.dispose());
    synths.current = [];
    setPlaying(false);
  }

  async function play() {
    if (!result) return;
    await Tone.start();
    stop();
    const midi = new Midi(Uint8Array.from(atob(result.midi_base64), (c) => c.charCodeAt(0)));
    const transport = Tone.getTransport();
    transport.bpm.value = result.tempo_bpm;
    for (const track of midi.tracks) {
      const isDrone = track.name === "drone";
      const synth = new Tone.PolySynth(Tone.Synth, {
        oscillator: { type: isDrone ? "sawtooth" : "triangle" },
        envelope: isDrone ? { attack: 0.5, release: 1 } : { attack: 0.02, decay: 0.1, sustain: 0.6, release: 0.3 },
        volume: isDrone ? -18 : -6,
      }).toDestination();
      synths.current.push(synth);
      for (const n of track.notes) {
        transport.schedule((time) => synth.triggerAttackRelease(n.name, n.duration, time, n.velocity), n.time);
      }
    }
    transport.schedule(() => setPlaying(false), midi.duration + 0.5);
    transport.start();
    setPlaying(true);
  }

  function download() {
    if (!result) return;
    const bytes = Uint8Array.from(atob(result.midi_base64), (c) => c.charCodeAt(0));
    const url = URL.createObjectURL(new Blob([bytes], { type: "audio/midi" }));
    const a = document.createElement("a");
    a.href = url;
    a.download = `${result.raga}-${hzToNote(result.tonic_hz)}-${seed}.mid`;
    a.click();
    URL.revokeObjectURL(url);
  }

  return (
    <section>
      <div className="controls">
        <select value={raga} onChange={(e) => setRaga(e.target.value)}>
          {ragas.map((r) => (
            <option key={r.name} value={r.name}>
              {r.name} ({r.tradition})
            </option>
          ))}
        </select>
        <label>
          Tonic Hz <input type="number" value={tonic} min={40} max={1000} step={0.01} onChange={(e) => setTonic(Number(e.target.value))} />
          <small> {hzToNote(tonic)}</small>
        </label>
        <label>
          Tempo <input type="number" value={tempo} min={30} max={300} onChange={(e) => setTempo(Number(e.target.value))} />
        </label>
        <label>
          Bars <input type="number" value={bars} min={1} max={64} onChange={(e) => setBars(Number(e.target.value))} />
        </label>
        <label>
          Seed <input type="number" value={seed} onChange={(e) => setSeed(Number(e.target.value))} />
        </label>
        <label>
          <input type="checkbox" checked={drone} onChange={(e) => setDrone(e.target.checked)} /> Drone
        </label>
        <button onClick={run} disabled={!raga || busy}>
          Generate
        </button>
      </div>

      {error && <p className="error">{error}</p>}

      {result && (
        <div className="result">
          <div className="controls">
            <button onClick={playing ? stop : play}>{playing ? "Stop" : "Play"}</button>
            <button onClick={download}>Download .mid</button>
            <span className="stage">
              {result.raga} · Sa = {hzToNote(result.tonic_hz)} · {result.tempo_bpm} bpm · {result.notes.length} notes
            </span>
          </div>
          <h3>Swaras</h3>
          <p className="swaras">
            {result.notes.map((n, i) => (
              <span key={i} style={{ minWidth: `${n.beats * 1.6}em` }} title={`${n.beats} beats`}>
                {n.name}
              </span>
            ))}
          </p>
        </div>
      )}
    </section>
  );
}
