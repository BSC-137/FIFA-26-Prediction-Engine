import { useEffect, useState } from "react";

const API_BASE = import.meta.env.VITE_API_URL ?? "/api";

interface AccuracySummary {
  n_matches: number;
  accuracy_1x2: number;
  brier_score: number;
  log_loss: number;
  mae_total_goals: number;
  ou_25_hit_rate: number;
  btts_hit_rate: number;
  model_version: string;
}

function pct(n: number) {
  return `${(n * 100).toFixed(1)}%`;
}

export default function AccuracyPanel() {
  const [summary, setSummary] = useState<AccuracySummary | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetch(`${API_BASE}/accuracy/summary`)
      .then((res) => (res.ok ? res.json() : Promise.reject(new Error("No ledger data yet"))))
      .then(setSummary)
      .catch((e) => setError(e instanceof Error ? e.message : "Unavailable"));
  }, []);

  return (
    <section className="accuracy-panel">
      <div className="panel-head">
        <h2>Ledger accuracy</h2>
      </div>
      {error && <p className="accuracy-empty">{error}</p>}
      {summary && summary.n_matches === 0 && (
        <p className="accuracy-empty">No finished predictions in ledger yet. Sync upcoming fixtures first.</p>
      )}
      {summary && summary.n_matches > 0 && (
        <div className="accuracy-grid">
          <div className="accuracy-stat">
            <span className="label">Matches</span>
            <span className="value">{summary.n_matches}</span>
          </div>
          <div className="accuracy-stat">
            <span className="label">1X2</span>
            <span className="value accent">{pct(summary.accuracy_1x2)}</span>
          </div>
          <div className="accuracy-stat">
            <span className="label">O/U 2.5</span>
            <span className="value">{pct(summary.ou_25_hit_rate)}</span>
          </div>
          <div className="accuracy-stat">
            <span className="label">BTTS</span>
            <span className="value">{pct(summary.btts_hit_rate)}</span>
          </div>
          <div className="accuracy-stat wide">
            <span className="label">Goal MAE</span>
            <span className="value mono">{summary.mae_total_goals.toFixed(2)}</span>
          </div>
        </div>
      )}
    </section>
  );
}
