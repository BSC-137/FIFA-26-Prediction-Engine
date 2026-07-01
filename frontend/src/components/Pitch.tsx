import type { Prediction } from "../api";

interface PitchProps {
  prediction: Prediction;
}

function pct(n: number) {
  return `${(n * 100).toFixed(1)}%`;
}

function pickLabel(prediction: Prediction): { label: string; key: "home" | "draw" | "away" } {
  const p = prediction.probabilities;
  const entries: ["home" | "draw" | "away", number][] = [
    ["home", p.home_win],
    ["draw", p.draw],
    ["away", p.away_win],
  ];
  entries.sort((a, b) => b[1] - a[1]);
  const [key] = entries[0];
  const labels = { home: "Home win", draw: "Draw", away: "Away win" };
  return { label: labels[key], key };
}

export default function Pitch({ prediction }: PitchProps) {
  const { fixture, expected_goals, probabilities: p } = prediction;
  const pick = pickLabel(prediction);
  const totalXg = expected_goals.adjusted_home + expected_goals.adjusted_away;

  return (
    <div className="pitch-wrap">
      <div className="pitch-header">
        <div>
          <span className="stage-pill">{fixture.stage}</span>
          {fixture.venue && (
            <span className="venue-meta">
              {fixture.venue}
              {fixture.venue_city ? ` · ${fixture.venue_city}` : ""}
            </span>
          )}
        </div>
        <div className="model-pick">
          Model pick: <strong>{pick.label}</strong>
          <span className="pick-pct">{pct(p[pick.key === "home" ? "home_win" : pick.key === "draw" ? "draw" : "away_win"])}</span>
        </div>
      </div>

      <svg className="pitch-svg" viewBox="0 0 900 520" role="img" aria-label="Football pitch with prediction overlay">
        <defs>
          <linearGradient id="grass" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="#1a5c32" />
            <stop offset="50%" stopColor="#22703f" />
            <stop offset="100%" stopColor="#1a5c32" />
          </linearGradient>
          <pattern id="stripes" width="60" height="520" patternUnits="userSpaceOnUse">
            <rect width="30" height="520" fill="rgba(255,255,255,0.03)" />
          </pattern>
        </defs>

        <rect width="900" height="520" fill="url(#grass)" rx="12" />
        <rect width="900" height="520" fill="url(#stripes)" rx="12" />

        {/* markings */}
        <g stroke="rgba(255,255,255,0.55)" strokeWidth="2.5" fill="none">
          <rect x="24" y="24" width="852" height="472" />
          <line x1="450" y1="24" x2="450" y2="496" />
          <circle cx="450" cy="260" r="68" />
          <circle cx="450" cy="260" r="4" fill="rgba(255,255,255,0.7)" />
          <rect x="24" y="148" width="120" height="224" />
          <rect x="756" y="148" width="120" height="224" />
          <rect x="24" y="198" width="48" height="124" />
          <rect x="828" y="198" width="48" height="124" />
          <path d="M 144 260 A 68 68 0 0 1 144 196" />
          <path d="M 756 260 A 68 68 0 0 0 756 324" />
        </g>

        {/* home half arc */}
        <path
          d="M 120 420 A 200 200 0 0 1 120 100"
          fill="none"
          stroke="rgba(96, 165, 250, 0.35)"
          strokeWidth={14 + p.home_win * 40}
          strokeLinecap="round"
        />
        {/* away half arc */}
        <path
          d="M 780 100 A 200 200 0 0 1 780 420"
          fill="none"
          stroke="rgba(251, 146, 60, 0.35)"
          strokeWidth={14 + p.away_win * 40}
          strokeLinecap="round"
        />

        {/* home team */}
        <g className="team-node home-node">
          <circle cx="200" cy="260" r="72" fill="rgba(15, 23, 42, 0.55)" stroke="rgba(96, 165, 250, 0.8)" strokeWidth="3" />
          <text x="200" y="228" textAnchor="middle" className="team-name-svg">
            {fixture.home_team_name}
          </text>
          <text x="200" y="262" textAnchor="middle" className="xg-svg">
            {expected_goals.adjusted_home.toFixed(2)}
          </text>
          <text x="200" y="286" textAnchor="middle" className="xg-label-svg">
            xG
          </text>
          <text x="200" y="318" textAnchor="middle" className="prob-svg home-prob">
            {pct(p.home_win)}
          </text>
        </g>

        {/* away team */}
        <g className="team-node away-node">
          <circle cx="700" cy="260" r="72" fill="rgba(15, 23, 42, 0.55)" stroke="rgba(251, 146, 60, 0.8)" strokeWidth="3" />
          <text x="700" y="228" textAnchor="middle" className="team-name-svg">
            {fixture.away_team_name}
          </text>
          <text x="700" y="262" textAnchor="middle" className="xg-svg">
            {expected_goals.adjusted_away.toFixed(2)}
          </text>
          <text x="700" y="286" textAnchor="middle" className="xg-label-svg">
            xG
          </text>
          <text x="700" y="318" textAnchor="middle" className="prob-svg away-prob">
            {pct(p.away_win)}
          </text>
        </g>

        {/* center draw bubble */}
        <g>
          <circle cx="450" cy="260" r="52" fill="rgba(15, 23, 42, 0.72)" stroke="rgba(167, 243, 208, 0.5)" strokeWidth="2" />
          <text x="450" y="248" textAnchor="middle" className="draw-label-svg">
            Draw
          </text>
          <text x="450" y="278" textAnchor="middle" className="draw-pct-svg">
            {pct(p.draw)}
          </text>
        </g>

        {/* bottom bar: total xG */}
        <rect x="300" y="468" width="300" height="28" rx="14" fill="rgba(15, 23, 42, 0.65)" />
        <text x="450" y="487" textAnchor="middle" className="total-xg-svg">
          Total xG {totalXg.toFixed(2)}
        </text>
      </svg>

      <div className="pitch-legend">
        <span><i className="dot home-dot" /> Home win {pct(p.home_win)}</span>
        <span><i className="dot draw-dot" /> Draw {pct(p.draw)}</span>
        <span><i className="dot away-dot" /> Away win {pct(p.away_win)}</span>
      </div>
    </div>
  );
}
