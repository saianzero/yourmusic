import { useState } from "react";
import Analyze from "./pages/Analyze";
import "./App.css";

const TABS = ["Analyze", "Similar", "Generate"] as const;
type Tab = (typeof TABS)[number];

export default function App() {
  const [tab, setTab] = useState<Tab>("Analyze");
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
      {tab === "Analyze" && <Analyze />}
      {tab !== "Analyze" && <p className="stage">{tab} coming soon.</p>}
    </main>
  );
}
