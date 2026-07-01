import { useCallback, useEffect, useState } from "react";
import {
  getFixtures,
  getModelInfo,
  getPrediction,
  refreshFixtures,
  type Fixture,
  type ModelInfo,
  type Prediction,
} from "./api";
import AccuracyPanel from "./components/AccuracyPanel";
import MatchList from "./components/MatchList";
import Pitch from "./components/Pitch";
import StatsPanel from "./components/StatsPanel";

export default function App() {
  const [fixtures, setFixtures] = useState<Fixture[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [prediction, setPrediction] = useState<Prediction | null>(null);
  const [modelInfo, setModelInfo] = useState<ModelInfo | null>(null);
  const [filter, setFilter] = useState<"all" | "scheduled" | "live" | "finished">("scheduled");
  const [loadingList, setLoadingList] = useState(true);
  const [loadingPred, setLoadingPred] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [refreshing, setRefreshing] = useState(false);

  const loadFixtures = useCallback(async (refresh = false) => {
    setLoadingList(true);
    setError(null);
    try {
      const data = refresh ? await refreshFixtures() : await getFixtures();
      const sorted = [...data.items].sort(
        (a, b) => new Date(a.kickoff_utc).getTime() - new Date(b.kickoff_utc).getTime(),
      );
      setFixtures(sorted);
      if (!selectedId && sorted.length > 0) {
        const next =
          sorted.find((f) => f.status === "scheduled") ??
          sorted.find((f) => f.status === "live") ??
          sorted[sorted.length - 1];
        setSelectedId(next.fixture_id);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load fixtures");
    } finally {
      setLoadingList(false);
    }
  }, [selectedId]);

  useEffect(() => {
    loadFixtures();
    getModelInfo().then(setModelInfo).catch(() => undefined);
  }, [loadFixtures]);

  useEffect(() => {
    if (!selectedId) return;
    let cancelled = false;
    setLoadingPred(true);
    setError(null);
    getPrediction(selectedId)
      .then((p) => {
        if (!cancelled) setPrediction(p);
      })
      .catch((e) => {
        if (!cancelled) setError(e instanceof Error ? e.message : "Prediction failed");
      })
      .finally(() => {
        if (!cancelled) setLoadingPred(false);
      });
    return () => {
      cancelled = true;
    };
  }, [selectedId]);

  const handleRefresh = async () => {
    setRefreshing(true);
    await loadFixtures(true);
    setRefreshing(false);
  };

  return (
    <div className="app-shell">
      <header className="top-bar">
        <div className="brand">
          <span className="brand-icon">⚽</span>
          <div>
            <h1>FIFA 26 Prediction Pitch</h1>
            <p className="subtitle">
              Weather-aware Poisson model
              {modelInfo && (
                <span className="version-tag"> · {modelInfo.model_version}</span>
              )}
            </p>
          </div>
        </div>
        <div className="top-actions">
          <button
            type="button"
            className="btn ghost"
            onClick={handleRefresh}
            disabled={refreshing}
          >
            {refreshing ? "Syncing…" : "Sync data"}
          </button>
          <a
            className="btn ghost"
            href={import.meta.env.DEV ? "/api/docs" : "/docs"}
            target="_blank"
            rel="noreferrer"
          >
            API docs
          </a>
        </div>
      </header>

      {error && (
        <div className="error-banner" role="alert">
          {error}
          <span className="error-hint">Start the API: .\scripts\run_api.ps1</span>
        </div>
      )}

      <main className="layout">
        <MatchList
          fixtures={fixtures}
          selectedId={selectedId}
          filter={filter}
          onFilter={setFilter}
          onSelect={setSelectedId}
          loading={loadingList}
        />

        <section className="center-stage">
          {loadingPred && !prediction && (
            <div className="center-placeholder">
              <div className="spinner" />
              <p>Running simulation…</p>
            </div>
          )}
          {prediction && (
            <>
              <Pitch prediction={prediction} />
              {loadingPred && <div className="refresh-overlay">Updating…</div>}
            </>
          )}
          {!loadingPred && !prediction && !error && (
            <div className="center-placeholder">
              <p>Select a match to see the pitch forecast.</p>
            </div>
          )}
        </section>

        {prediction && <StatsPanel prediction={prediction} />}
      </main>

      <AccuracyPanel />

      <footer className="footer-note">
        Unique layers: tournament-only strength · Elo blend · weather affinity · host boost · Dixon–Coles
      </footer>
    </div>
  );
}
