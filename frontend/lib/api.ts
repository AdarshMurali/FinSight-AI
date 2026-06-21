const BASE = "http://localhost:8000";

async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) throw new Error(`API ${path} → ${res.status}`);
  return res.json();
}

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
): Promise<void> {
  const res = await fetch(`${BASE}/api/analysis/ai/chat`, {
    method:  "POST",
    headers: { "Content-Type": "application/json" },
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
