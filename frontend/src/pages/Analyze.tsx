import { useEffect, useRef, useState } from "react";
import { type Analysis, type AnalyzeJob, PC_NAMES, getAnalyze, hzToNote, overrideTonic, startAnalyze } from "../api";

const STAGES: Record<string, string> = {
  queued: "Queued",
  separating: "Separating vocals (Demucs)",
  pitch: "Tracking pitch",
  tonic: "Detecting tonic",
  identify: "Matching ragas",
  tempo: "Estimating tempo",
};

export default function Analyze() {
  const [file, setFile] = useState<File | null>(null);
  const [tradition, setTradition] = useState("");
  const [separate, setSeparate] = useState(true);
  const [job, setJob] = useState<AnalyzeJob | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const timer = useRef<number | null>(null);

  useEffect(() => {
    if (!job || job.status !== "running") return;
    timer.current = window.setTimeout(async () => {
      try {
        setJob(await getAnalyze(job.id));
      } catch (e) {
        setError(String(e));
      }
    }, 1500);
    return () => {
      if (timer.current) clearTimeout(timer.current);
    };
  }, [job]);

  async function run() {
    if (!file) return;
    setError(null);
    setBusy(true);
    try {
      setJob(await startAnalyze(file, tradition, separate));
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  }

  async function pickTonic(hz: number) {
    if (!job) return;
    try {
      setJob(await overrideTonic(job.id, hz));
    } catch (e) {
      setError(String(e));
    }
  }

  const result = job?.result ?? null;

  return (
    <section>
      <div className="controls">
        <input type="file" accept="audio/*,.mp3,.wav,.flac,.m4a" onChange={(e) => setFile(e.target.files?.[0] ?? null)} />
        <select value={tradition} onChange={(e) => setTradition(e.target.value)}>
          <option value="">Both traditions</option>
          <option value="carnatic">Carnatic</option>
          <option value="hindustani">Hindustani</option>
        </select>
        <label>
          <input type="checkbox" checked={separate} onChange={(e) => setSeparate(e.target.checked)} /> Separate vocals
        </label>
        <button onClick={run} disabled={!file || busy || job?.status === "running"}>
          Analyze
        </button>
      </div>

      {error && <p className="error">{error}</p>}
      {job?.status === "running" && <p className="stage">{STAGES[job.stage] ?? job.stage}…</p>}
      {job?.status === "error" && <p className="error">{job.error}</p>}
      {result && <Result r={result} onPickTonic={pickTonic} />}
    </section>
  );
}

function Result({ r, onPickTonic }: { r: Analysis; onPickTonic: (hz: number) => void }) {
  const max = Math.max(...r.swara_histogram, 1e-6);
  return (
    <div className="result">
      <div className="stats">
        <span>
          Tonic <b>{hzToNote(r.tonic_hz)}</b> ({r.tonic_hz} Hz)
        </span>
        <span>
          Tempo <b>{r.tempo_bpm}</b> bpm
        </span>
        <span>
          Notes <b>{r.n_notes}</b>
        </span>
        <span>
          Gamaka <b>{Math.round(r.gamaka_ratio * 100)}%</b>
        </span>
      </div>

      <h3>Tonic candidates</h3>
      <div className="tonics">
        {r.tonic_candidates.map((c) => (
          <button key={c.hz} className={c.hz === r.tonic_hz ? "active" : ""} onClick={() => onPickTonic(c.hz)}>
            {hzToNote(c.hz)} {c.hz} Hz · fit {c.raga_fit.toFixed(2)} ({c.best_raga})
          </button>
        ))}
      </div>

      <h3>Swara distribution</h3>
      <div className="hist">
        {r.swara_histogram.map((v, i) => (
          <div key={i} className="bar">
            <div className="fill" style={{ height: `${(v / max) * 100}%` }} title={`${(v * 100).toFixed(1)}%`} />
            <span>{PC_NAMES[i]}</span>
          </div>
        ))}
      </div>

      <h3>Raga candidates</h3>
      <ol className="ragas">
        {r.candidates.map((c) => (
          <li key={c.name}>
            <div className="raga-head">
              <b>{c.name}</b> <em>{c.tradition}</em> <span className="score">{c.score.toFixed(3)}</span>
            </div>
            <ul>
              {c.reasons.map((x, i) => (
                <li key={i}>{x}</li>
              ))}
            </ul>
          </li>
        ))}
      </ol>

      {r.motifs.length > 0 && (
        <>
          <h3>Recurring motifs</h3>
          <ul className="motifs">
            {r.motifs.map((m, i) => (
              <li key={i}>
                {m.pcs.map((p) => PC_NAMES[p].split("/")[0]).join(" ")} <span>×{m.count}</span>
              </li>
            ))}
          </ul>
        </>
      )}
    </div>
  );
}
