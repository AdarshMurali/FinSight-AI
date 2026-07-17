"use client";
import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { getMarketEvent, getAffectedPortfolios, getPortfolios, aiAnalyzeEvent, MarketEvent, AffectedPortfolio, AIEventAnalysis, Portfolio } from "@/lib/api";
import LoadingSpinner from "@/components/LoadingSpinner";
import SectionHeader from "@/components/SectionHeader";
import { SmartText, RagSources, CostTag } from "@/components/AiTextRenderer";
import { Radio, Sparkles } from "lucide-react";
import Link from "next/link";
import { manrope, GOLD, WHITE, MUTED, GREEN, RED, NEAR_BLACK, BORDER } from "@/lib/theme";

function impactBadge(level: string | null) {
  if (!level) return null;
  const cls = level === "high" ? "badge-high" : level === "medium" ? "badge-medium" : "badge-low";
  return <span className={`badge ${cls}`}>{level.toUpperCase()}</span>;
}

export default function MarketEventDetail() {
  const { id } = useParams<{ id: string }>();
  const [event, setEvent]         = useState<MarketEvent | null>(null);
  const [affected, setAffected]   = useState<AffectedPortfolio[]>([]);
  const [portfolios, setPortfolios] = useState<Portfolio[]>([]);
  const [selectedPortfolioId, setSelectedPortfolioId] = useState(0);
  const [loading, setLoading]     = useState(true);

  const [analyzingId, setAnalyzingId] = useState<number | null>(null);
  const [analyses, setAnalyses]       = useState<Record<number, AIEventAnalysis>>({});
  const [analysisErrors, setAnalysisErrors] = useState<Record<number, string>>({});

  useEffect(() => {
    const eid = Number(id);
    Promise.all([getMarketEvent(eid), getAffectedPortfolios(eid), getPortfolios()])
      .then(([ev, aff, pf]) => {
        setEvent(ev);
        setAffected(aff);
        setPortfolios(pf);
        if (pf.length) setSelectedPortfolioId(pf[0].portfolio_id);
      })
      .finally(() => setLoading(false));
  }, [id]);

  // Portfolio names for any portfolio we've run an analysis on, whether or
  // not the system auto-detected it as "affected" (exposure detection relies
  // on the event having tagged sectors/regions, which many events lack).
  const portfolioNameById = new Map<number, string>();
  affected.forEach(a => portfolioNameById.set(a.portfolio_id, a.portfolio_name));
  portfolios.forEach(p => { if (!portfolioNameById.has(p.portfolio_id)) portfolioNameById.set(p.portfolio_id, p.portfolio_name); });

  const analyzedPortfolioIds = Array.from(
    new Set([...Object.keys(analyses), ...Object.keys(analysisErrors)].map(Number))
  );

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
  if (!event) return <p className={`text-sm ${manrope.className}`} style={{ color: RED }}>Event not found.</p>;

  let sectors: string[] = [];
  let regions: string[] = [];
  try { sectors = JSON.parse(event.affected_sectors || "[]"); } catch {}
  try { regions = JSON.parse(event.affected_regions || "[]"); } catch {}

  return (
    <div className={`max-w-4xl mx-auto space-y-4 ${manrope.className}`}>
      {/* Header */}
      <div className="pb-4" style={{ borderBottom: `1px solid ${BORDER}` }}>
        <div className="flex items-center gap-2 mb-2">
          <Radio size={16} style={{ color: GOLD }} />
          <span className="badge badge-blue">{event.event_type}</span>
          {impactBadge(event.impact_level)}
        </div>
        <h1 className="text-[19px] font-bold" style={{ color: WHITE }}>{event.event_title}</h1>
        <p className="text-[11px] mt-1 tracking-wide" style={{ color: MUTED }}>{event.event_date?.slice(0, 10)}</p>
      </div>

      {/* Description */}
      {event.event_description && (
        <div className="rounded-2xl overflow-hidden" style={{ background: NEAR_BLACK, border: `1px solid ${BORDER}` }}>
          <SectionHeader title="Event Summary" />
          <div className="px-4 py-4">
            <p className="text-sm leading-6" style={{ color: MUTED }}>{event.event_description}</p>
          </div>
        </div>
      )}

      {/* Metadata */}
      <div className="grid grid-cols-2 gap-4">
        <div className="rounded-2xl overflow-hidden" style={{ background: NEAR_BLACK, border: `1px solid ${BORDER}` }}>
          <SectionHeader title="Affected Sectors" />
          <div className="px-4 py-4">
            {sectors.length ? (
              <div className="flex flex-wrap gap-2">
                {sectors.map(s => <span key={s} className="badge badge-yellow">{s}</span>)}
              </div>
            ) : <p className="text-xs" style={{ color: MUTED }}>None specified</p>}
          </div>
        </div>
        <div className="rounded-2xl overflow-hidden" style={{ background: NEAR_BLACK, border: `1px solid ${BORDER}` }}>
          <SectionHeader title="Affected Regions" />
          <div className="px-4 py-4">
            {regions.length ? (
              <div className="flex flex-wrap gap-2">
                {regions.map(r => <span key={r} className="badge badge-blue">{r}</span>)}
              </div>
            ) : <p className="text-xs" style={{ color: MUTED }}>None specified</p>}
          </div>
        </div>
      </div>

      {/* Affected portfolios */}
      <div className="rounded-2xl overflow-hidden" style={{ background: NEAR_BLACK, border: `1px solid ${BORDER}` }}>
        <SectionHeader title="Affected Portfolios" sub={`${affected.length} portfolios with related position changes`} />
        {affected.length === 0 ? (
          <p className="text-xs p-4" style={{ color: MUTED }}>No portfolios with linked position changes.</p>
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
                  <td className="font-medium text-xs" style={{ color: WHITE }}>{a.portfolio_name}</td>
                  <td className="text-right" style={{ color: MUTED }}>{a.changes_count}</td>
                  <td className="text-right font-medium" style={{ color: a.total_weight_change >= 0 ? GREEN : RED }}>
                    {a.total_weight_change >= 0 ? "+" : ""}{(a.total_weight_change * 100).toFixed(2)}%
                  </td>
                  <td className="text-right whitespace-nowrap">
                    <Link href={`/portfolios/${a.portfolio_id}`} className="transition-colors text-xs mr-3" style={{ color: GOLD }}>
                      View portfolio
                    </Link>
                    <button
                      onClick={() => handleAnalyze(a.portfolio_id)}
                      disabled={analyzingId === a.portfolio_id}
                      className="inline-flex items-center gap-1 transition-colors text-xs disabled:opacity-40 disabled:cursor-not-allowed"
                      style={{ color: GOLD }}
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

      {/* Analyze any portfolio's exposure — independent of auto-detected "affected" list,
          since exposure detection requires the event to have tagged sectors/regions,
          which many events (like this one) don't have. */}
      <div className="rounded-2xl overflow-hidden" style={{ background: NEAR_BLACK, border: `1px solid ${BORDER}` }}>
        <SectionHeader title="AI Event Impact Analysis" sub="analyze any portfolio's exposure to this event" />
        <div className="p-4 flex items-end gap-4">
          <div className="flex-1">
            <label className="text-[10px] uppercase tracking-wide block mb-2" style={{ color: MUTED }}>Portfolio</label>
            <select
              value={selectedPortfolioId}
              onChange={e => setSelectedPortfolioId(Number(e.target.value))}
              className="w-full text-xs px-3 py-2.5 rounded-lg focus:outline-none transition-colors"
              style={{ background: "#000", border: `1px solid ${BORDER}`, color: WHITE }}
            >
              {portfolios.map(p => (
                <option key={p.portfolio_id} value={p.portfolio_id}>
                  #{p.portfolio_id} — {p.portfolio_name}
                </option>
              ))}
            </select>
          </div>
          <button
            onClick={() => handleAnalyze(selectedPortfolioId)}
            disabled={analyzingId === selectedPortfolioId || !selectedPortfolioId}
            className="flex items-center gap-2 px-5 py-2.5 rounded-full text-black text-xs font-bold tracking-wide uppercase transition-colors disabled:opacity-40 disabled:cursor-not-allowed whitespace-nowrap"
            style={{ background: GOLD }}
          >
            <Sparkles size={13} />
            {analyzingId === selectedPortfolioId ? "Analyzing…" : "Analyze impact"}
          </button>
        </div>
      </div>

      {/* AI event impact analysis results */}
      {analyzedPortfolioIds.map(pid => {
        const result = analyses[pid];
        const err = analysisErrors[pid];
        return (
          <div key={pid} className="rounded-2xl overflow-hidden" style={{ background: NEAR_BLACK, border: `1px solid ${BORDER}` }}>
            <SectionHeader
              title="AI Event Impact Analysis"
              sub={`${portfolioNameById.get(pid) ?? `Portfolio #${pid}`} · GPT-4o mini`}
              action={result ? <CostTag cost={result.llm_usage.total_cost_usd} /> : undefined}
            />
            <div className="px-4 py-4 space-y-3">
              {err ? (
                <p className="text-xs" style={{ color: RED }}>{err}</p>
              ) : (
                <>
                  <div className="pl-4" style={{ borderLeft: `2px solid ${GOLD}4d` }}>
                    <SmartText text={result!.ai_assessment} bulletColor="bg-[#fabd49]" />
                  </div>
                  <RagSources sources={result!.rag_sources} />
                </>
              )}
            </div>
          </div>
        );
      })}

      {event.source_url && (
        <p className="text-xs" style={{ color: MUTED }}>
          Source:{" "}
          <a href={event.source_url} target="_blank" rel="noopener noreferrer" className="transition-colors" style={{ color: GOLD }}>
            {event.source_url}
          </a>
        </p>
      )}
    </div>
  );
}
