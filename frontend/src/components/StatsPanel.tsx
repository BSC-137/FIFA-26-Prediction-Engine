import type { Prediction } from "../api";

interface StatsPanelProps {
  prediction: Prediction;
}

function pct(n: number) {
  return `${(n * 100).toFixed(1)}%`;
}

function ProbRow({ label, value, accent }: { label: string; value: number; accent?: string }) {
  return (
    <div className="prob-row">
      <div className="prob-row-head">
        <span>{label}</span>
        <span className="mono">{pct(value)}</span>
      </div>
      <div className="prob-track">
        <div
          className="prob-fill"
          style={{ width: `${value * 100}%`, background: accent ?? "var(--accent)" }}
        />
      </div>
    </div>
  );
}

export default function StatsPanel({ prediction }: StatsPanelProps) {
  const { probabilities: p, expected_goals: xg, diagnostics: d, weather, knockout_markets: km } =
    prediction;
  const ou = p.over_under;

  return (
    <aside className="stats-panel">
      <div className="panel-head">
        <h2>Markets</h2>
      </div>

      <section className="stat-block">
        <h3>1X2 Outcome</h3>
        <ProbRow label="Home win" value={p.home_win} accent="#60a5fa" />
        <ProbRow label="Draw" value={p.draw} accent="#6ee7b7" />
        <ProbRow label="Away win" value={p.away_win} accent="#fb923c" />
      </section>

      <section className="stat-block">
        <h3>Expected goals pipeline</h3>
        <div className="xg-grid">
          <div className="xg-cell">
            <span className="xg-cell-label">Strength</span>
            <span className="mono">{xg.strength_home.toFixed(2)} – {xg.strength_away.toFixed(2)}</span>
          </div>
          <div className="xg-cell">
            <span className="xg-cell-label">Base</span>
            <span className="mono">{xg.base_home.toFixed(2)} – {xg.base_away.toFixed(2)}</span>
          </div>
          <div className="xg-cell highlight">
            <span className="xg-cell-label">Adjusted</span>
            <span className="mono">{xg.adjusted_home.toFixed(2)} – {xg.adjusted_away.toFixed(2)}</span>
          </div>
        </div>
      </section>

      <section className="stat-block">
        <h3>Goal markets</h3>
        <ProbRow label="Over 2.5" value={ou.over_2_5 ?? 0} />
        <ProbRow label="Under 2.5" value={ou.under_2_5 ?? 0} />
        <ProbRow label="BTTS Yes" value={p.btts_yes} accent="#a78bfa" />
        <ProbRow label="BTTS No" value={p.btts_no} />
      </section>

      {km && (
        <section className="stat-block">
          <h3>Knockout — to advance</h3>
          <ProbRow label="Home advances" value={km.advance_home} accent="#60a5fa" />
          <ProbRow label="Away advances" value={km.advance_away} accent="#fb923c" />
        </section>
      )}

      <section className="stat-block">
        <h3>Most likely scorelines</h3>
        <ul className="score-list">
          {p.top_scores.slice(0, 6).map((s) => (
            <li key={s.score}>
              <span className="score-line">{s.score}</span>
              <span className="mono">{pct(s.probability)}</span>
            </li>
          ))}
        </ul>
      </section>

      {weather && (
        <section className="stat-block">
          <h3>Kickoff conditions</h3>
          <div className="weather-grid">
            <span>{weather.weather_code ?? "—"}</span>
            <span>{weather.temperature_c != null ? `${weather.temperature_c}°C` : "—"}</span>
            <span>{weather.humidity_pct != null ? `${weather.humidity_pct}% humidity` : ""}</span>
            <span>{weather.wind_speed_kmh != null ? `${weather.wind_speed_kmh} km/h wind` : ""}</span>
          </div>
          {prediction.weather_explanations.length > 0 && (
            <ul className="explain-list">
              {prediction.weather_explanations.map((e) => (
                <li key={e}>{e}</li>
              ))}
            </ul>
          )}
        </section>
      )}

      {d && (
        <section className="stat-block">
          <h3>Model diagnostics</h3>
          <div className="diag-grid">
            <div><span>Home atk/def</span><span className="mono">{d.home_attack.toFixed(2)} / {d.home_defense.toFixed(2)}</span></div>
            <div><span>Away atk/def</span><span className="mono">{d.away_attack.toFixed(2)} / {d.away_defense.toFixed(2)}</span></div>
            <div><span>WC matches</span><span className="mono">{d.home_wc_matches} / {d.away_wc_matches}</span></div>
            <div><span>Training pool</span><span className="mono">{d.n_training_matches}</span></div>
          </div>
          {d.warnings.length > 0 && (
            <ul className="warning-list">
              {d.warnings.map((w) => (
                <li key={w}>{w.replaceAll("_", " ")}</li>
              ))}
            </ul>
          )}
        </section>
      )}

      {prediction.adjustments_applied.length > 0 && (
        <section className="stat-block compact">
          <h3>Adjustments</h3>
          <div className="tag-row">
            {prediction.adjustments_applied.map((a) => (
              <span key={a} className="tag">{a}</span>
            ))}
          </div>
        </section>
      )}
    </aside>
  );
}
