"use client";
import { useEffect, useState, Suspense, type ReactNode } from "react";
import { useSearchParams } from "next/navigation";
import { getPortfolios, aiExplainPortfolio, aiNarrateChanges, aiRecommendations, Portfolio } from "@/lib/api";
import LoadingSpinner from "@/components/LoadingSpinner";
import { SmartText, RagSources, CostTag } from "@/components/AiTextRenderer";
import { Sparkles, Brain, TrendingUp, Lightbulb, Zap, type LucideIcon } from "lucide-react";
import { manrope, GOLD, AMBER_DARK, WHITE, MUTED, RED, NEAR_BLACK, BORDER } from "@/lib/theme";

// ── Shared gold gradient panel header (matches the dashboard's card style) ──
function PanelHeaderBar({
  icon: Icon, title, sub, right,
}: {
  icon: LucideIcon;
  title: string;
  sub: string;
  right?: ReactNode;
}) {
  return (
    <div
      className="flex items-center justify-between px-4 py-2.5"
      style={{ background: `linear-gradient(to right, ${GOLD}, ${AMBER_DARK})` }}
    >
      <div className="flex items-center gap-2.5">
        <Icon size={13} className="text-black" />
        <div>
          <p className="text-black text-[11px] font-bold tracking-wide uppercase">{title}</p>
          <p className="text-black/55 text-[10px] tracking-wide uppercase mt-0.5">{sub}</p>
        </div>
      </div>
      {right}
    </div>
  );
}

// ── 1. Portfolio State Explanation ──────────────────────────────────────────
function ExplanationPanel({
  content, cost, sources,
}: {
  content: string;
  cost: number;
  sources: { collection: string; snippet: string }[];
}) {
  return (
    <div className="rounded-2xl overflow-hidden" style={{ background: NEAR_BLACK, border: `1px solid ${BORDER}` }}>
      <PanelHeaderBar icon={Brain} title="Portfolio State Explanation" sub="AI Analysis · GPT-4o" right={<CostTag cost={cost} />} />
      <div className="px-4 py-4 space-y-3">
        <div className="pl-4" style={{ borderLeft: `2px solid ${GOLD}4d` }}>
          <SmartText text={content} bulletColor="bg-[#fabd49]" />
        </div>
        <RagSources sources={sources} />
      </div>
    </div>
  );
}

// ── 2. Position Change Narrative ────────────────────────────────────────────
function NarrativePanel({ content, cost }: { content: string; cost: number }) {
  return (
    <div className="rounded-2xl overflow-hidden" style={{ background: NEAR_BLACK, border: `1px solid ${BORDER}` }}>
      <PanelHeaderBar icon={TrendingUp} title="Position Change Narrative" sub="Last 6 Months · Timeline" right={<CostTag cost={cost} />} />
      <div className="px-4 py-4">
        <div className="pl-4" style={{ borderLeft: `2px solid ${GOLD}4d` }}>
          <SmartText text={content} bulletColor="bg-[#fabd49]" />
        </div>
      </div>
    </div>
  );
}

// ── 3. AI Recommendations ───────────────────────────────────────────────────
function RecommendationsPanel({
  content, cost, ruleCount,
}: {
  content: string;
  cost: number;
  ruleCount: number;
}) {
  return (
    <div className="rounded-2xl overflow-hidden" style={{ background: NEAR_BLACK, border: `1px solid ${BORDER}` }}>
      <PanelHeaderBar
        icon={Lightbulb}
        title="AI Recommendations"
        sub="Strategy · Optimisation"
        right={
          <div className="flex items-center gap-2">
            <span className="flex items-center gap-1 text-[9px] text-black/70 bg-black/10 border border-black/20 px-2 py-0.5 rounded-full">
              <Zap size={9} />
              {ruleCount} rule-based signal{ruleCount !== 1 ? "s" : ""}
            </span>
            <CostTag cost={cost} />
          </div>
        }
      />
      <div className="px-4 py-4">
        <div className="pl-4" style={{ borderLeft: `2px solid ${GOLD}4d` }}>
          <SmartText text={content} bulletColor="bg-[#fabd49]" />
        </div>
      </div>
    </div>
  );
}

// ── Main page ─────────────────────────────────────────────────────────────
function AIInsightsContent() {
  const searchParams = useSearchParams();
  const defaultPid = Number(searchParams.get("portfolio")) || 0;

  const [portfolios, setPortfolios]   = useState<Portfolio[]>([]);
  const [selectedId, setSelectedId]   = useState(defaultPid);
  const [loading, setLoading]         = useState(false);
  const [error, setError]             = useState("");

  const [explanation, setExplanation]    = useState<{ text: string; cost: number; sources: { collection: string; snippet: string }[] } | null>(null);
  const [narrative, setNarrative]        = useState<{ text: string; cost: number } | null>(null);
  const [recommendations, setRecommends] = useState<{ text: string; cost: number; ruleCount: number } | null>(null);

  useEffect(() => {
    getPortfolios().then(p => {
      setPortfolios(p);
      if (!selectedId && p.length) setSelectedId(p[0].portfolio_id);
    });
  }, []);

  async function runAnalysis() {
    if (!selectedId) return;
    setLoading(true);
    setError("");
    setExplanation(null);
    setNarrative(null);
    setRecommends(null);

    const sixMonthsAgo = new Date();
    sixMonthsAgo.setMonth(sixMonthsAgo.getMonth() - 6);
    const startDate = sixMonthsAgo.toISOString().slice(0, 10);
    const endDate   = new Date().toISOString().slice(0, 10);

    try {
      const [exp, nar, rec] = await Promise.all([
        aiExplainPortfolio(selectedId, "What are the main risks and opportunities in this portfolio?"),
        aiNarrateChanges(selectedId, startDate, endDate),
        aiRecommendations(selectedId),
      ]);

      setExplanation({ text: exp.explanation, cost: exp.llm_usage.total_cost_usd, sources: exp.rag_sources });
      setNarrative({ text: nar.narrative, cost: nar.llm_usage.total_cost_usd });
      setRecommends({
        text: rec.ai_recommendations,
        cost: rec.llm_usage.total_cost_usd,
        ruleCount: rec.rule_based.recommendations_count,
      });
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "AI analysis failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className={`max-w-4xl mx-auto space-y-6 ${manrope.className}`}>

      {/* Page header */}
      <div className="flex items-center gap-3">
        <div className="p-2 rounded-lg" style={{ background: "rgba(250,189,73,0.12)" }}>
          <Sparkles size={18} style={{ color: GOLD }} />
        </div>
        <div>
          <h1 className="text-[18px] font-bold" style={{ color: WHITE }}>AI Insights</h1>
          <p className="text-[11px] tracking-wide" style={{ color: MUTED }}>GPT-4o powered portfolio analysis with RAG context</p>
        </div>
      </div>

      {/* Controls */}
      <div className="rounded-2xl p-4 flex items-end gap-4" style={{ background: NEAR_BLACK, border: `1px solid ${BORDER}` }}>
        <div className="flex-1">
          <label className="text-[10px] uppercase tracking-wide block mb-2" style={{ color: MUTED }}>
            Portfolio
          </label>
          <select
            value={selectedId}
            onChange={e => setSelectedId(Number(e.target.value))}
            className="w-full text-xs px-3 py-2.5 rounded-lg focus:outline-none transition-colors"
            style={{ background: "#000", border: `1px solid ${BORDER}`, color: WHITE }}
          >
            {portfolios.map(p => (
              <option key={p.portfolio_id} value={p.portfolio_id}>
                #{p.portfolio_id} — {p.portfolio_name} · {p.strategy_type ?? "unknown"} (Customer #{p.customer_id})
              </option>
            ))}
          </select>
        </div>
        <button
          onClick={runAnalysis}
          disabled={loading || !selectedId}
          className="flex items-center gap-2 px-5 py-2.5 rounded-full text-black text-xs font-bold tracking-wide uppercase transition-colors disabled:opacity-40 disabled:cursor-not-allowed whitespace-nowrap"
          style={{ background: GOLD }}
        >
          <Sparkles size={13} />
          {loading ? "Analyzing…" : "Run AI Analysis"}
        </button>
      </div>

      {/* Loading */}
      {loading && (
        <div className="space-y-2">
          <LoadingSpinner label="Running AI analysis — calling GPT-4o with RAG context…" />
          <p className="text-[11px] pl-7" style={{ color: MUTED }}>
            3 AI calls running in parallel. Usually takes 15–30 seconds.
          </p>
        </div>
      )}

      {/* Error */}
      {error && (
        <div className="rounded-xl px-4 py-3 text-xs" style={{ border: `1px solid ${RED}4d`, background: `${RED}1a`, color: RED }}>
          {error}
        </div>
      )}

      {/* Results */}
      {explanation && (
        <ExplanationPanel
          content={explanation.text}
          cost={explanation.cost}
          sources={explanation.sources}
        />
      )}

      {narrative && (
        <NarrativePanel
          content={narrative.text}
          cost={narrative.cost}
        />
      )}

      {recommendations && (
        <RecommendationsPanel
          content={recommendations.text}
          cost={recommendations.cost}
          ruleCount={recommendations.ruleCount}
        />
      )}

      {/* Empty state */}
      {!loading && !explanation && !error && (
        <div className="text-center py-20" style={{ color: MUTED }}>
          <Sparkles size={32} className="mx-auto mb-3" style={{ color: BORDER }} />
          <p className="text-sm">Select a portfolio and click Run AI Analysis</p>
          <p className="text-xs mt-1" style={{ color: MUTED }}>
            Combines portfolio data, ChromaDB RAG context, and GPT-4o
          </p>
        </div>
      )}
    </div>
  );
}

export default function AIInsightsPage() {
  return (
    <Suspense fallback={<LoadingSpinner label="Loading…" />}>
      <AIInsightsContent />
    </Suspense>
  );
}
