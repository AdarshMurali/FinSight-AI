"use client";
import { useEffect, useState, Suspense, type ReactNode } from "react";
import { useSearchParams } from "next/navigation";
import { getPortfolios, aiExplainPortfolio, aiNarrateChanges, aiRecommendations, Portfolio } from "@/lib/api";
import LoadingSpinner from "@/components/LoadingSpinner";
import { Sparkles, Brain, TrendingUp, Lightbulb, ChevronDown, ChevronUp, Zap, Database, type LucideIcon } from "lucide-react";

// ── Inline bold parser (avoids dangerouslySetInnerHTML) ───────────────────
function InlineText({ text }: { text: string }) {
  const parts = text.split(/(\*\*[^*]+\*\*)/g);
  return (
    <>
      {parts.map((part, i) =>
        part.startsWith("**") && part.endsWith("**")
          ? <strong key={i} className="text-[#E0E0E0] font-semibold">{part.slice(2, -2)}</strong>
          : <span key={i}>{part}</span>
      )}
    </>
  );
}

// ── Smart text renderer: turns AI plain text into structured elements ──────
function SmartText({ text, bulletColor }: { text: string; bulletColor: string }) {
  const lines = text.split("\n");
  const result: ReactNode[] = [];
  let bullets: string[] = [];
  let paraLines: string[] = [];

  const flushBullets = (key: string | number) => {
    if (!bullets.length) return;
    result.push(
      <ul key={`ul-${key}`} className="space-y-2 my-2 ml-1">
        {bullets.map((b, i) => (
          <li key={i} className="flex gap-2.5 items-start">
            <span className={`mt-[7px] w-1.5 h-1.5 rounded-full shrink-0 ${bulletColor}`} />
            <span className="text-[#888] text-xs leading-6"><InlineText text={b} /></span>
          </li>
        ))}
      </ul>
    );
    bullets = [];
  };

  const flushPara = (key: string | number) => {
    if (!paraLines.length) return;
    result.push(
      <p key={`p-${key}`} className="text-[#888] text-xs leading-6">
        <InlineText text={paraLines.join(" ")} />
      </p>
    );
    paraLines = [];
  };

  lines.forEach((line, i) => {
    const t = line.trim();
    if (!t) { flushBullets(i); flushPara(i); return; }

    const bulletMatch = t.match(/^[-•*]\s+(.+)/);
    const numberedMatch = t.match(/^\d+[.)]\s+(.+)/);

    if (bulletMatch || numberedMatch) {
      flushPara(i);
      bullets.push((bulletMatch ?? numberedMatch)![1]);
      return;
    }

    flushBullets(i);

    const isHeader =
      /^\*\*[^*]+\*\*:?$/.test(t) ||
      (t.endsWith(":") && t.length < 80 && !t.includes("."));

    if (isHeader) {
      flushPara(i);
      const label = t.replace(/^\*\*|\*\*:?$|:$/g, "").trim();
      result.push(
        <p key={`h-${i}`} className="text-[#E0E0E0] font-bold text-[10px] mt-5 mb-1 uppercase tracking-widest">
          {label}
        </p>
      );
      return;
    }

    paraLines.push(t);
  });

  flushBullets("end");
  flushPara("end");

  return <div className="space-y-1.5">{result}</div>;
}

// ── RAG sources collapsible ────────────────────────────────────────────────
function RagSources({ sources }: { sources: { collection: string; snippet: string }[] }) {
  const [open, setOpen] = useState(false);
  if (!sources.length) return null;
  return (
    <div className="pt-3 border-t border-[#1A1A1A]">
      <button
        onClick={() => setOpen(o => !o)}
        className="flex items-center gap-1.5 text-[#555] text-[10px] hover:text-[#888] transition-colors"
      >
        <Database size={10} />
        {open ? <ChevronUp size={10} /> : <ChevronDown size={10} />}
        {open ? "Hide" : `${sources.length}`} RAG sources used
      </button>
      {open && (
        <div className="mt-2 space-y-1.5">
          {sources.map((s, i) => (
            <div key={i} className="flex gap-2 text-[10px] bg-black px-2.5 py-1.5 border border-[#1A1A1A]">
              <span className="text-[#F5821F] font-mono shrink-0 opacity-80">{s.collection}</span>
              <span className="text-[#555] truncate">{s.snippet}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// ── Cost tag ──────────────────────────────────────────────────────────────
function CostTag({ cost }: { cost: number }) {
  return (
    <span className="text-white/70 text-[9px] font-mono border border-white/25 px-1.5 py-0.5 bg-black/15 shrink-0">
      ${cost.toFixed(4)} cost
    </span>
  );
}

// ── Shared orange gradient panel header (matches dashboard PanelHeader) ────
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
      style={{ background: "linear-gradient(to right, #FF8000, #7A2500)" }}
    >
      <div className="flex items-center gap-2.5">
        <Icon size={13} className="text-white" />
        <div>
          <p className="text-white text-[10px] font-bold tracking-[0.15em] uppercase">{title}</p>
          <p className="text-white/60 text-[9px] tracking-widest uppercase mt-0.5">{sub}</p>
        </div>
      </div>
      {right}
    </div>
  );
}

// ── 1. Portfolio State Explanation  (orange bullets) ────────────────────────
function ExplanationPanel({
  content, cost, sources,
}: {
  content: string;
  cost: number;
  sources: { collection: string; snippet: string }[];
}) {
  return (
    <div className="border border-[#2A2A2A] bg-[#0D0D0D]">
      <PanelHeaderBar icon={Brain} title="Portfolio State Explanation" sub="AI Analysis · GPT-4o" right={<CostTag cost={cost} />} />
      <div className="px-4 py-4 space-y-3">
        <div className="border-l-2 border-[#F5821F]/40 pl-4">
          <SmartText text={content} bulletColor="bg-[#F5821F]" />
        </div>
        <RagSources sources={sources} />
      </div>
    </div>
  );
}

// ── 2. Position Change Narrative  (yellow bullets) ──────────────────────────
function NarrativePanel({ content, cost }: { content: string; cost: number }) {
  return (
    <div className="border border-[#2A2A2A] bg-[#0D0D0D]">
      <PanelHeaderBar icon={TrendingUp} title="Position Change Narrative" sub="Last 6 Months · Timeline" right={<CostTag cost={cost} />} />
      <div className="px-4 py-4">
        <div className="border-l-2 border-[#FFB300]/40 pl-4">
          <SmartText text={content} bulletColor="bg-[#FFB300]" />
        </div>
      </div>
    </div>
  );
}

// ── 3. AI Recommendations  (green bullets) ──────────────────────────────────
function RecommendationsPanel({
  content, cost, ruleCount,
}: {
  content: string;
  cost: number;
  ruleCount: number;
}) {
  return (
    <div className="border border-[#2A2A2A] bg-[#0D0D0D]">
      <PanelHeaderBar
        icon={Lightbulb}
        title="AI Recommendations"
        sub="Strategy · Optimisation"
        right={
          <div className="flex items-center gap-2">
            <span className="flex items-center gap-1 text-[9px] text-white/80 bg-black/15 border border-white/25 px-2 py-0.5">
              <Zap size={9} />
              {ruleCount} rule-based signal{ruleCount !== 1 ? "s" : ""}
            </span>
            <CostTag cost={cost} />
          </div>
        }
      />
      <div className="px-4 py-4">
        <div className="border-l-2 border-[#00CC44]/40 pl-4">
          <SmartText text={content} bulletColor="bg-[#00CC44]" />
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
    <div className="max-w-4xl mx-auto space-y-6 font-mono">

      {/* Page header */}
      <div className="border-b border-[#2A2A2A] pb-4 flex items-center gap-3">
        <Sparkles size={18} className="text-[#F5821F]" />
        <div>
          <h1 className="text-[#E0E0E0] text-lg font-bold tracking-wider">AI INSIGHTS</h1>
          <p className="text-[#888] text-[10px] tracking-wider">GPT-4o POWERED PORTFOLIO ANALYSIS WITH RAG CONTEXT</p>
        </div>
      </div>

      {/* Controls */}
      <div className="border border-[#2A2A2A] bg-[#0D0D0D] p-4 flex items-end gap-4">
        <div className="flex-1">
          <label className="text-[#888] text-[10px] uppercase tracking-wider block mb-2">
            Portfolio
          </label>
          <select
            value={selectedId}
            onChange={e => setSelectedId(Number(e.target.value))}
            className="w-full bg-black border border-[#2A2A2A] text-[#E0E0E0] text-xs px-3 py-2 focus:outline-none focus:border-[#F5821F] transition-colors"
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
          className="flex items-center gap-2 px-5 py-2 bg-[#F5821F] text-black text-xs font-bold tracking-wider uppercase hover:bg-[#FFB300] transition-colors disabled:opacity-40 disabled:cursor-not-allowed whitespace-nowrap"
        >
          <Sparkles size={13} />
          {loading ? "Analyzing…" : "Run AI Analysis"}
        </button>
      </div>

      {/* Loading */}
      {loading && (
        <div className="space-y-2">
          <LoadingSpinner label="Running AI analysis — calling GPT-4o with RAG context…" />
          <p className="text-[#555] text-[11px] pl-7">
            3 AI calls running in parallel. Usually takes 15–30 seconds.
          </p>
        </div>
      )}

      {/* Error */}
      {error && (
        <div className="border border-[#FF4040]/30 bg-[#FF4040]/10 px-4 py-3 text-[#FF4040] text-xs">
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
        <div className="text-center py-20 text-[#555]">
          <Sparkles size={32} className="mx-auto mb-3 text-[#2A2A2A]" />
          <p className="text-sm">Select a portfolio and click Run AI Analysis</p>
          <p className="text-xs mt-1 text-[#555]">
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
