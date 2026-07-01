const API_BASE = import.meta.env.VITE_API_URL ?? "/api";

async function fetchJson<T>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`);
  if (!res.ok) {
    const detail = await res.text();
    throw new Error(detail || `HTTP ${res.status}`);
  }
  return res.json() as Promise<T>;
}

export interface Fixture {
  fixture_id: string;
  home_team_name: string;
  away_team_name: string;
  home_team_id: string;
  away_team_id: string;
  kickoff_utc: string;
  status: "scheduled" | "live" | "finished";
  stage: string;
  venue: string | null;
  venue_city: string | null;
  pitch_type: string;
  home_goals: number | null;
  away_goals: number | null;
}

export interface Prediction {
  fixture: Fixture;
  expected_goals: {
    strength_home: number;
    strength_away: number;
    base_home: number;
    base_away: number;
    adjusted_home: number;
    adjusted_away: number;
  };
  probabilities: {
    home_win: number;
    draw: number;
    away_win: number;
    btts_yes: number;
    btts_no: number;
    over_under: Record<string, number>;
    top_scores: { score: string; probability: number }[];
  };
  weather: {
    temperature_c: number | null;
    humidity_pct: number | null;
    wind_speed_kmh: number | null;
    precipitation_mm: number | null;
    weather_code: string | null;
    is_indoor: boolean;
  } | null;
  adjustments_applied: string[];
  weather_explanations: string[];
  diagnostics: {
    home_attack: number;
    away_attack: number;
    home_defense: number;
    away_defense: number;
    n_training_matches: number;
    home_wc_matches: number;
    away_wc_matches: number;
    host_boost_applied: number;
    warnings: string[];
  } | null;
  knockout_markets: {
    regulation_home_win: number;
    regulation_draw: number;
    regulation_away_win: number;
    advance_home: number;
    advance_away: number;
  } | null;
  model_version: string;
  generated_at: string;
}

export interface ModelInfo {
  model_version: string;
  dixon_coles_rho: number;
  tournament_min_total_xg: number;
  elo_blend_weight: number;
  host_nation_boost: number;
}

export function getFixtures(status?: string) {
  const q = status ? `?status=${status}&limit=200` : "?limit=200";
  return fetchJson<{ items: Fixture[]; source: string }>(`/fixtures${q}`);
}

export function refreshFixtures(status?: string) {
  const q = status ? `?status=${status}&limit=200` : "?limit=200";
  return fetchJson<{ items: Fixture[] }>(`/fixtures/refresh${q}`);
}

export function getPrediction(fixtureId: string) {
  return fetchJson<Prediction>(`/predict/${fixtureId}`);
}

export function getModelInfo() {
  return fetchJson<ModelInfo>("/model/info");
}
