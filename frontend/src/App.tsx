import { useState } from "react";
import Analyze from "./pages/Analyze";
import Generate from "./pages/Generate";
import "./App.css";

const TABS = ["Analyze", "Similar", "Generate"] as const;
type Tab = (typeof TABS)[number];

export default function App() {
  const [tab, setTab] = useState<Tab>("Analyze");
  const [seed, setSeed] = useState<{ tonic: number; raga: string } | null>(null);

  function useForGenerate(tonic: number, raga: string) {
    setSeed({ tonic, raga });
    setTab("Generate");
  }

  return (
    <main>
      <header>
        <h1>Raga Lab</h1>
        <nav>
          {TABS.map((t) => (
            <button key={t} className={t === tab ? "active" : ""} onClick={() => setTab(t)}>
              {t}
            </button>
          ))}
        </nav>
      </header>
      <div style={{ display: tab === "Analyze" ? "block" : "none" }}>
        <Analyze onUseForGenerate={useForGenerate} />
      </div>
      {tab === "Generate" && <Generate key={`${seed?.tonic}-${seed?.raga}`} initialTonic={seed?.tonic} initialRaga={seed?.raga} />}
      {tab === "Similar" && <p className="stage">Similar coming soon.</p>}
    </main>
  );
}
