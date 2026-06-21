"use client";
import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { getMarketEvent, getAffectedPortfolios, MarketEvent, AffectedPortfolio } from "@/lib/api";
import LoadingSpinner from "@/components/LoadingSpinner";
import SectionHeader from "@/components/SectionHeader";
import { Radio } from "lucide-react";
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

  useEffect(() => {
    const eid = Number(id);
    Promise.all([getMarketEvent(eid), getAffectedPortfolios(eid)])
      .then(([ev, aff]) => { setEvent(ev); setAffected(aff); })
      .finally(() => setLoading(false));
  }, [id]);

  if (loading) return <LoadingSpinner label="Loading event..." />;
  if (!event) return <p className="text-[#ff4d4d] text-sm">Event not found.</p>;

  let sectors: string[] = [];
  let regions: string[] = [];
  try { sectors = JSON.parse(event.affected_sectors || "[]"); } catch {}
  try { regions = JSON.parse(event.affected_regions || "[]"); } catch {}

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      {/* Header */}
      <div className="border-b border-[#2a2a3a] pb-4">
        <div className="flex items-center gap-2 mb-2">
          <Radio size={16} className="text-[#f5c518]" />
          <span className="badge badge-blue">{event.event_type}</span>
          {impactBadge(event.impact_level)}
        </div>
        <h1 className="text-[#e8e8f0] text-lg font-semibold">{event.event_title}</h1>
        <p className="text-[#5a5a70] text-xs mt-1">{event.event_date?.slice(0, 10)}</p>
      </div>

      {/* Description */}
      {event.event_description && (
        <div className="bg-[#111118] border border-[#2a2a3a] rounded-lg p-5">
          <SectionHeader title="Event Summary" />
          <p className="text-[#9898b0] text-sm leading-6">{event.event_description}</p>
        </div>
      )}

      {/* Metadata */}
      <div className="grid grid-cols-2 gap-4">
        <div className="bg-[#111118] border border-[#2a2a3a] rounded-lg p-5">
          <SectionHeader title="Affected Sectors" />
          {sectors.length ? (
            <div className="flex flex-wrap gap-2">
              {sectors.map(s => <span key={s} className="badge badge-yellow">{s}</span>)}
            </div>
          ) : <p className="text-[#5a5a70] text-xs">None specified</p>}
        </div>
        <div className="bg-[#111118] border border-[#2a2a3a] rounded-lg p-5">
          <SectionHeader title="Affected Regions" />
          {regions.length ? (
            <div className="flex flex-wrap gap-2">
              {regions.map(r => <span key={r} className="badge badge-blue">{r}</span>)}
            </div>
          ) : <p className="text-[#5a5a70] text-xs">None specified</p>}
        </div>
      </div>

      {/* Affected portfolios */}
      <div className="bg-[#111118] border border-[#2a2a3a] rounded-lg">
        <div className="p-5 border-b border-[#2a2a3a]">
          <SectionHeader title="Affected Portfolios" sub={`${affected.length} portfolios with related position changes`} />
        </div>
        {affected.length === 0 ? (
          <p className="text-[#5a5a70] text-xs p-5">No portfolios with linked position changes.</p>
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
                  <td className="text-[#e8e8f0] font-medium text-xs">{a.portfolio_name}</td>
                  <td className="text-right text-[#9898b0]">{a.changes_count}</td>
                  <td className={`text-right font-medium ${a.total_weight_change >= 0 ? "positive" : "negative"}`}>
                    {a.total_weight_change >= 0 ? "+" : ""}{a.total_weight_change.toFixed(2)}%
                  </td>
                  <td className="text-right">
                    <Link href={`/portfolios/${a.portfolio_id}`} className="text-[#1e90ff] text-xs hover:underline">
                      View portfolio
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {event.source_url && (
        <p className="text-[#5a5a70] text-xs">
          Source:{" "}
          <a href={event.source_url} target="_blank" rel="noopener noreferrer" className="text-[#1e90ff] hover:underline">
            {event.source_url}
          </a>
        </p>
      )}
    </div>
  );
}
