"use client";
import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { getMarketEvent, getAffectedPortfolios, aiAnalyzeEvent, MarketEvent, AffectedPortfolio, AIEventAnalysis } from "@/lib/api";
import LoadingSpinner from "@/components/LoadingSpinner";
import SectionHeader from "@/components/SectionHeader";
import { SmartText, RagSources, CostTag } from "@/components/AiTextRenderer";
import { Radio, Sparkles } from "lucide-react";
import Link from "next/link";

function impactBadge(level: string | null) {
  if (!level) return null;
  const cls = level === "high" ? "badge-high" : level === "medium" ? "badge-medium" : "badge-low";
  return <span className={`badge ${cls}`}>{level.toUpperCase()}</span>;
}

export default function MarketEventDetail() {
  const { id } = useParams<{ id: string }>();
  const [event, setEvent]       = useState<MarketEvent | null>(null);
  const [affected, setAffected] = useState<AffectedPortfolio[]>([]);
  const [loading, setLoading]   = useState(true);

  const [analyzingId, setAnalyzingId] = useState<number | null>(null);
  const [analyses, setAnalyses]       = useState<Record<number, AIEventAnalysis>>({});
  const [analysisErrors, setAnalysisErrors] = useState<Record<number, string>>({});

  useEffect(() => {
    const eid = Number(id);
    Promise.all([getMarketEvent(eid), getAffectedPortfolios(eid)])
      .then(([ev, aff]) => { setEvent(ev); setAffected(aff); })
      .finally(() => setLoading(false));
  }, [id]);

  async function handleAnalyze(portfolioId: number) {
    setAnalyzingId(portfolioId);
    setAnalysisErrors(prev => { const next = { ...prev }; delete next[portfolioId]; return next; });
    try {
      const result = await aiAnalyzeEvent(Number(id), portfolioId);
      setAnalyses(prev => ({ ...prev, [portfolioId]: result }));
    } catch (e: unknown) {
      setAnalysisErrors(prev => ({
        ...prev,
        [portfolioId]: e instanceof Error ? e.message : "AI event analysis failed",
      }));
    } finally {
      setAnalyzingId(null);
    }
  }

  if (loading) return <LoadingSpinner label="Loading event..." />;
  if (!event) return <p className="text-[#FF4040] text-sm font-mono">Event not found.</p>;

  let sectors: string[] = [];
  let regions: string[] = [];
  try { sectors = JSON.parse(event.affected_sectors || "[]"); } catch {}
  try { regions = JSON.parse(event.affected_regions || "[]"); } catch {}

  return (
    <div className="max-w-4xl mx-auto space-y-4 font-mono">
      {/* Header */}
      <div className="border-b border-[#2A2A2A] pb-4">
        <div className="flex items-center gap-2 mb-2">
          <Radio size={16} className="text-[#FFB300]" />
          <span className="badge badge-blue">{event.event_type}</span>
          {impactBadge(event.impact_level)}
        </div>
        <h1 className="text-[#E0E0E0] text-lg font-bold tracking-wider">{event.event_title?.toUpperCase()}</h1>
        <p className="text-[#888] text-[10px] mt-1 tracking-wider">{event.event_date?.slice(0, 10)}</p>
      </div>

      {/* Description */}
      {event.event_description && (
        <div className="border border-[#2A2A2A] bg-[#0D0D0D]">
          <SectionHeader title="Event Summary" />
          <div className="px-4 py-4">
            <p className="text-[#AAA] text-sm leading-6">{event.event_description}</p>
          </div>
        </div>
      )}

      {/* Metadata */}
      <div className="grid grid-cols-2 gap-4">
        <div className="border border-[#2A2A2A] bg-[#0D0D0D]">
          <SectionHeader title="Affected Sectors" />
          <div className="px-4 py-4">
            {sectors.length ? (
              <div className="flex flex-wrap gap-2">
                {sectors.map(s => <span key={s} className="badge badge-yellow">{s}</span>)}
              </div>
            ) : <p className="text-[#555] text-xs">None specified</p>}
          </div>
        </div>
        <div className="border border-[#2A2A2A] bg-[#0D0D0D]">
          <SectionHeader title="Affected Regions" />
          <div className="px-4 py-4">
            {regions.length ? (
              <div className="flex flex-wrap gap-2">
                {regions.map(r => <span key={r} className="badge badge-blue">{r}</span>)}
              </div>
            ) : <p className="text-[#555] text-xs">None specified</p>}
          </div>
        </div>
      </div>

      {/* Affected portfolios */}
      <div className="border border-[#2A2A2A] bg-[#0D0D0D]">
        <SectionHeader title="Affected Portfolios" sub={`${affected.length} PORTFOLIOS WITH RELATED POSITION CHANGES`} />
        {affected.length === 0 ? (
          <p className="text-[#555] text-xs p-4">No portfolios with linked position changes.</p>
        ) : (
          <table>
            <thead>
              <tr>
                <th>Portfolio</th>
                <th className="text-right">Position Changes</th>
                <th className="text-right">Net Weight Δ</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {affected.map(a => (
                <tr key={a.portfolio_id}>
                  <td className="text-[#E0E0E0] font-medium text-xs">{a.portfolio_name}</td>
                  <td className="text-right text-[#888]">{a.changes_count}</td>
                  <td className={`text-right font-medium ${a.total_weight_change >= 0 ? "positive" : "negative"}`}>
                    {a.total_weight_change >= 0 ? "+" : ""}{(a.total_weight_change * 100).toFixed(2)}%
                  </td>
                  <td className="text-right whitespace-nowrap">
                    <Link href={`/portfolios/${a.portfolio_id}`} className="text-[#F5821F] hover:text-[#FFA040] transition-colors text-xs mr-3">
                      View portfolio
                    </Link>
                    <button
                      onClick={() => handleAnalyze(a.portfolio_id)}
                      disabled={analyzingId === a.portfolio_id}
                      className="inline-flex items-center gap-1 text-[#00CC44] hover:text-[#33FF77] transition-colors text-xs disabled:opacity-40 disabled:cursor-not-allowed"
                    >
                      <Sparkles size={11} />
                      {analyzingId === a.portfolio_id ? "Analyzing…" : analyses[a.portfolio_id] ? "Re-analyze" : "Analyze impact"}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* AI event impact analyses */}
      {affected.map(a => {
        const result = analyses[a.portfolio_id];
        const err = analysisErrors[a.portfolio_id];
        if (!result && !err) return null;
        return (
          <div key={a.portfolio_id} className="border border-[#2A2A2A] bg-[#0D0D0D]">
            <SectionHeader
              title="AI Event Impact Analysis"
              sub={`${a.portfolio_name} · GPT-4o mini`}
              action={result ? <CostTag cost={result.llm_usage.total_cost_usd} /> : undefined}
            />
            <div className="px-4 py-4 space-y-3">
              {err ? (
                <p className="text-[#FF4040] text-xs">{err}</p>
              ) : (
                <>
                  <div className="border-l-2 border-[#00CC44]/40 pl-4">
                    <SmartText text={result!.ai_assessment} bulletColor="bg-[#00CC44]" />
                  </div>
                  <RagSources sources={result!.rag_sources} />
                </>
              )}
            </div>
          </div>
        );
      })}

      {event.source_url && (
        <p className="text-[#555] text-xs">
          Source:{" "}
          <a href={event.source_url} target="_blank" rel="noopener noreferrer" className="text-[#F5821F] hover:text-[#FFA040] transition-colors">
            {event.source_url}
          </a>
        </p>
      )}
    </div>
  );
}
