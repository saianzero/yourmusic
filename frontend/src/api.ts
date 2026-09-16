export const API = import.meta.env.VITE_API_URL ?? "http://localhost:8010";

export type RagaCandidate = { name: string; tradition: string; score: number; reasons: string[] };
export type TonicCandidate = { hz: number; strength: number; raga_fit: number; best_raga: string };
export type Motif = { pcs: number[]; count: number };
export type Analysis = {
  tonic_hz: number;
  tonic_candidates: TonicCandidate[];
  swara_histogram: number[];
  candidates: RagaCandidate[];
  tempo_bpm: number;
  gamaka_ratio: number;
  n_notes: number;
  motifs: Motif[];
};
export type AnalyzeJob = {
  id: string;
  status: "running" | "done" | "error";
  stage: string;
  result: Analysis | null;
  error: string | null;
};

export const PC_NAMES = ["S", "R1/r", "R2/R", "G2/g", "G3/G", "M1/m", "M2/M", "P", "D1/d", "D2/D", "N2/n", "N3/N"];

const NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"];
export function hzToNote(hz: number): string {
  const midi = Math.round(12 * Math.log2(hz / 440) + 69);
  return `${NOTE_NAMES[midi % 12]}${Math.floor(midi / 12) - 1}`;
}

async function check<T>(r: Response): Promise<T> {
  if (!r.ok) throw new Error((await r.json().catch(() => ({})))?.detail ?? r.statusText);
  return r.json();
}

export async function startAnalyze(file: File, tradition: string, separate: boolean): Promise<AnalyzeJob> {
  const fd = new FormData();
  fd.append("file", file);
  if (tradition) fd.append("tradition", tradition);
  fd.append("separate", String(separate));
  return check(await fetch(`${API}/analyze`, { method: "POST", body: fd }));
}

export async function getAnalyze(id: string): Promise<AnalyzeJob> {
  return check(await fetch(`${API}/analyze/${id}`));
}

export async function overrideTonic(id: string, tonic_hz: number): Promise<AnalyzeJob> {
  return check(
    await fetch(`${API}/analyze/${id}/tonic`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ tonic_hz }),
    }),
  );
}
