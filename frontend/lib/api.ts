const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    ...options,
    credentials: "include",   // send the httpOnly JWT cookie (Task 6.4)
    headers: {
      "Content-Type": "application/json",
      "ngrok-skip-browser-warning": "1",   // bypass ngrok free-tier interstitial
      ...(options?.headers ?? {}),
    },
  });
  if (!res.ok) throw new Error(`API ${path} → ${res.status}`);
  return res.json();
}

// ── Auth ──────────────────────────────────────────────────────────────────────
export interface CurrentUser {
  user_id: number;
  email: string;
  full_name: string;
  role: "fund_manager" | "admin";
}

export async function login(email: string, password: string): Promise<CurrentUser> {
  const res = await fetch(`${BASE}/auth/login`, {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || "Invalid email or password");
  }
  return res.json();
}

export const logout = () =>
  apiFetch<{ status: string }>("/auth/logout", { method: "POST" });

export const getCurrentUser = () =>
  apiFetch<CurrentUser>("/auth/me");

// ── Portfolios ────────────────────────────────────────────────────────────────
export const getPortfolios = () =>
  apiFetch<Portfolio[]>("/api/portfolios?limit=100");

export const getPortfolio = (id: number) =>
  apiFetch<PortfolioDetail>(`/api/portfolios/${id}`);

export const getPositions = (id: number) =>
  apiFetch<Position[]>(`/api/portfolios/${id}/positions`);

export const getPerformance = (id: number, limit = 30) =>
  apiFetch<Performance[]>(`/api/portfolios/${id}/performance?limit=${limit}`);

export const getHistory = (id: number, limit = 50) =>
  apiFetch<Transaction[]>(`/api/portfolios/${id}/history?limit=${limit}`);

// PDF download — not JSON, so bypasses apiFetch's res.json() and instead
// triggers a browser download directly from the response blob.
export async function downloadPortfolioReport(id: number): Promise<void> {
  const res = await fetch(`${BASE}/api/portfolios/${id}/report`, {
    credentials: "include",
    headers: { "ngrok-skip-browser-warning": "1" },
  });
  if (!res.ok) throw new Error(`Report generation failed → ${res.status}`);

  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `finsight-report-portfolio-${id}.pdf`;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

// ── Market Events ─────────────────────────────────────────────────────────────
export const getMarketEvents = (limit = 50) =>
  apiFetch<MarketEvent[]>(`/api/market-events?limit=${limit}`);

export const getMarketEvent = (id: number) =>
  apiFetch<MarketEvent>(`/api/market-events/${id}`);

export const getAffectedPortfolios = (id: number) =>
  apiFetch<AffectedPortfolio[]>(`/api/market-events/${id}/affected-portfolios`);

// ── Analysis ──────────────────────────────────────────────────────────────────
export const analyzePortfolioState = (portfolio_id: number) =>
  apiFetch<PortfolioAnalysis>("/api/analysis/portfolio-state", {
    method: "POST",
    body: JSON.stringify({ portfolio_id }),
  });

// ── AI Analysis ───────────────────────────────────────────────────────────────
export const aiExplainPortfolio = (portfolio_id: number, question?: string) =>
  apiFetch<AIExplanation>("/api/analysis/ai/explain-portfolio", {
    method: "POST",
    body: JSON.stringify({ portfolio_id, question }),
  });

export const aiNarrateChanges = (
  portfolio_id: number,
  start_date: string,
  end_date: string
) =>
  apiFetch<AIChanges>("/api/analysis/ai/narrate-changes", {
    method: "POST",
    body: JSON.stringify({ portfolio_id, start_date, end_date, threshold_percent: 3 }),
  });

export const aiAnalyzeEvent = (event_id: number, portfolio_id: number) =>
  apiFetch<AIEventAnalysis>("/api/analysis/ai/analyze-event", {
    method: "POST",
    body: JSON.stringify({ event_id, portfolio_ids: [portfolio_id], depth: "quick" }),
  });

export const aiRecommendations = (portfolio_id: number) =>
  apiFetch<AIRecommendations>("/api/analysis/ai/recommendations", {
    method: "POST",
    body: JSON.stringify({ portfolio_id, optimization_goal: "balanced" }),
  });

export const getSuggestedQuestions = () =>
  apiFetch<{ questions: string[] }>("/api/analysis/ai/chat/suggested-questions");

/**
 * Stream a chat response token-by-token via SSE.
 * @param portfolio_id  Portfolio to ground the conversation in.
 * @param message       Current user message.
 * @param history       Prior conversation turns [{role, content}].
 * @param onToken       Called with each text chunk as it arrives.
 * @param onDone        Called when the stream closes (success or error).
 */
export async function aiChatStream(
  portfolio_id: number,
  message: string,
  history: ChatMessage[],
  onToken: (token: string) => void,
  onError: (err: string) => void,
  onDone: () => void,
  onToolCall?: (toolName: string) => void,
): Promise<void> {
  const res = await fetch(`${BASE}/api/analysis/ai/chat`, {
    method:      "POST",
    credentials: "include",   // send the httpOnly JWT cookie (Task 6.4)
    headers: {
      "Content-Type": "application/json",
      "ngrok-skip-browser-warning": "1",
    },
    body:    JSON.stringify({ portfolio_id, message, conversation_history: history }),
  });

  if (!res.ok) {
    onError(`API error ${res.status}`);
    onDone();
    return;
  }

  const reader  = res.body!.getReader();
  const decoder = new TextDecoder();

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    const raw   = decoder.decode(value, { stream: true });
    const lines = raw.split("\n");

    for (const line of lines) {
      if (!line.startsWith("data: ")) continue;
      const data = line.slice(6).trim();
      if (data === "[DONE]") { onDone(); return; }
      try {
        const parsed = JSON.parse(data);
        if (parsed.error) { onError(parsed.error); onDone(); return; }
        if (parsed.tool_call) { onToolCall?.(parsed.tool_call); continue; }
        if (parsed.token) onToken(parsed.token);
      } catch {
        // partial JSON chunk — skip
      }
    }
  }
  onDone();
}

// ── Types ─────────────────────────────────────────────────────────────────────
export interface Portfolio {
  portfolio_id: number;
  portfolio_name: string;
  customer_id: number;
  total_value: number | null;
  cash_balance: number | null;
  currency: string;
  strategy_type: string | null;
  inception_date: string | null;
}

export interface PortfolioDetail extends Portfolio {
  positions_count: number;
  total_positions_value: number;
  customer: Customer | null;
}

export interface Customer {
  customer_id: number;
  customer_name: string;
  institution_type: string | null;
  aum: number | null;
  risk_profile: string | null;
}

export interface Position {
  position_id: number;
  portfolio_id: number;
  security_id: number;
  quantity: number;
  avg_cost_basis: number;
  current_price: number;
  market_value: number | null;
  weight: number | null;
  position_type: string;
  opened_date: string | null;
  security: Security | null;
}

export interface Security {
  security_id: number;
  ticker_symbol: string;
  security_name: string | null;
  security_type: string | null;
  sector: string | null;
  industry: string | null;
  country: string | null;
}

export interface Performance {
  performance_id: number;
  portfolio_id: number;
  as_of_date: string;
  total_value: number | null;
  daily_return: number | null;
  mtd_return: number | null;
  ytd_return: number | null;
  volatility: number | null;
  sharpe_ratio: number | null;
  max_drawdown: number | null;
}

export interface Transaction {
  transaction_id: number;
  portfolio_id: number;
  security_id: number;
  transaction_type: string;
  quantity: number;
  price: number;
  transaction_date: string;
  fees: number | null;
  security: Security | null;
}

export interface MarketEvent {
  event_id: number;
  event_date: string;
  event_type: string | null;
  event_title: string | null;
  event_description: string | null;
  affected_sectors: string | null;
  affected_regions: string | null;
  impact_level: string | null;
  source_url: string | null;
}

export interface AffectedPortfolio {
  portfolio_id: number;
  portfolio_name: string;
  changes_count: number;
  total_weight_change: number;
}

export interface PortfolioAnalysis {
  portfolio_id: number;
  portfolio_name: string;
  total_value: number;
  sector_allocation: Record<string, number>;
  region_allocation: Record<string, number>;
  risk_metrics: { volatility?: number; sharpe_ratio?: number; max_drawdown?: number };
  concentration_risk: { top_positions?: { ticker: string; weight: number }[] };
  performance_summary: { ytd_return?: number; mtd_return?: number };
}

export interface AIExplanation {
  explanation: string;
  rag_sources: { collection: string; snippet: string }[];
  llm_usage: { total_cost_usd: number; total_input_tokens: number; total_output_tokens: number };
}

export interface AIChanges {
  narrative: string;
  changes_count: number;
  rag_sources: { collection: string; snippet: string }[];
  llm_usage: { total_cost_usd: number };
}

export interface AIEventAnalysis {
  ai_assessment: string;
  event_data: { event_title: string; portfolios_affected: number };
  rag_sources: { collection: string; snippet: string }[];
  llm_usage: { total_cost_usd: number };
}

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
}

export interface AIRecommendations {
  ai_recommendations: string;
  rule_based: { recommendations_count: number; recommendations: { type: string; priority: number; title: string; description: string }[] };
  llm_usage: { total_cost_usd: number };
}

// ── Risk Analytics ────────────────────────────────────────────────────────────
export interface VarData {
  historical?: {
    var_95_1d_pct: number;
    var_99_1d_pct: number;
    var_95_10d_pct: number;
    var_99_10d_pct: number;
  };
  parametric?: {
    var_95_1d_pct: number;
    var_99_1d_pct: number;
  };
  distribution?: {
    daily_vol_pct: number;
    annualized_vol_pct: number;
    skewness: number;
    excess_kurtosis: number;
  };
  tickers_used?: string[];
  tickers_missing?: string[];
  observations?: number;
  price_date?: string;
  error?: string;
}

export interface StressTest {
  name: string;
  label: string;
  portfolio_impact_pct: number;
  worst_position: string;
  worst_position_pct: number;
  tickers_with_data: number;
  tickers_total: number;
}

export interface FactorExposure {
  factors?: Record<string, { beta: number; r_squared: number; ticker: string }>;
  market_interp?: string;
  observations?: number;
  error?: string;
}

export interface RiskMetrics {
  status: "ok" | "not_computed" | "computing";
  portfolio_id?: number;
  computed_at?: string;
  price_date?: string;
  var?: VarData;
  stress_tests?: StressTest[];
  factor_exposure?: FactorExposure;
}

export const getRiskMetrics = (portfolio_id: number) =>
  apiFetch<RiskMetrics>(`/api/risk/${portfolio_id}`);

export const refreshRiskMetrics = (portfolio_id: number) =>
  apiFetch<{ status: string; portfolio_id: number }>(`/api/risk/${portfolio_id}/refresh`, {
    method: "POST",
  });

export interface RiskHistoryPoint {
  computed_at:      string;
  price_date:       string | null;
  var_95_1d_pct:    number | null;
  var_99_1d_pct:    number | null;
  stress_worst_pct: number | null;
}

export const getRiskHistory = (portfolio_id: number, days = 30) =>
  apiFetch<RiskHistoryPoint[]>(`/api/risk/${portfolio_id}/history?days=${days}`);

// ── Alerts ────────────────────────────────────────────────────────────────────
export interface AlertItem {
  alert_id:     number;
  portfolio_id: number | null;
  alert_type:   "threshold" | "event" | "ai";
  severity:     "critical" | "warning" | "info";
  title:        string;
  message:      string;
  is_read:      boolean;
  triggered_at: string;
}

export const getAlerts = (params?: { portfolio_id?: number; unread_only?: boolean; limit?: number }) => {
  const q = new URLSearchParams();
  if (params?.portfolio_id !== undefined) q.set("portfolio_id", String(params.portfolio_id));
  if (params?.unread_only)               q.set("unread_only", "true");
  if (params?.limit)                     q.set("limit", String(params.limit));
  return apiFetch<AlertItem[]>(`/api/alerts?${q.toString()}`);
};

export const getUnreadCount = (portfolio_id?: number) => {
  const q = portfolio_id !== undefined ? `?portfolio_id=${portfolio_id}` : "";
  return apiFetch<{ count: number }>(`/api/alerts/unread-count${q}`);
};

export const markAlertRead = (alert_id: number) =>
  apiFetch<{ status: string }>(`/api/alerts/${alert_id}/read`, { method: "PATCH" });

export const markAllAlertsRead = (portfolio_id?: number) => {
  const q = portfolio_id !== undefined ? `?portfolio_id=${portfolio_id}` : "";
  return apiFetch<{ status: string }>(`/api/alerts/read-all${q}`, { method: "PATCH" });
};
