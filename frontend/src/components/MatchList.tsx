import type { Fixture } from "../api";

interface MatchListProps {
  fixtures: Fixture[];
  selectedId: string | null;
  filter: "all" | "scheduled" | "live" | "finished";
  onFilter: (f: "all" | "scheduled" | "live" | "finished") => void;
  onSelect: (id: string) => void;
  loading: boolean;
}

function formatKickoff(iso: string) {
  const d = new Date(iso);
  return d.toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export default function MatchList({
  fixtures,
  selectedId,
  filter,
  onFilter,
  onSelect,
  loading,
}: MatchListProps) {
  const filtered =
    filter === "all" ? fixtures : fixtures.filter((f) => f.status === filter);

  return (
    <aside className="match-list-panel">
      <div className="panel-head">
        <h2>Matches</h2>
        <span className="count">{filtered.length}</span>
      </div>

      <div className="filter-row">
        {(["all", "scheduled", "live", "finished"] as const).map((f) => (
          <button
            key={f}
            type="button"
            className={`filter-btn ${filter === f ? "active" : ""}`}
            onClick={() => onFilter(f)}
          >
            {f}
          </button>
        ))}
      </div>

      <div className={`match-scroll ${loading ? "loading" : ""}`}>
        {filtered.map((fx) => {
          const score =
            fx.home_goals != null && fx.away_goals != null
              ? `${fx.home_goals}–${fx.away_goals}`
              : null;
          return (
            <button
              key={fx.fixture_id}
              type="button"
              className={`match-card ${selectedId === fx.fixture_id ? "selected" : ""}`}
              onClick={() => onSelect(fx.fixture_id)}
            >
              <div className="match-card-top">
                <span className={`status-chip ${fx.status}`}>{fx.status}</span>
                <span className="kickoff">{formatKickoff(fx.kickoff_utc)}</span>
              </div>
              <div className="match-teams">
                <span>{fx.home_team_name}</span>
                <span className="vs">{score ?? "vs"}</span>
                <span>{fx.away_team_name}</span>
              </div>
              <div className="match-stage">{fx.stage}</div>
            </button>
          );
        })}
        {!loading && filtered.length === 0 && (
          <p className="empty-msg">No matches in this filter.</p>
        )}
      </div>
    </aside>
  );
}
