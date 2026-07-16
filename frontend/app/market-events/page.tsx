"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { getMarketEvents, MarketEvent } from "@/lib/api";
import LoadingSpinner from "@/components/LoadingSpinner";
import { Radio, ArrowRight } from "lucide-react";

function impactBadge(level: string | null) {
  if (!level) return null;
  const cls = level === "high" ? "badge-high" : level === "medium" ? "badge-medium" : "badge-low";
  return <span className={`badge ${cls}`}>{level.toUpperCase()}</span>;
}

// Matches the Market_Events.event_type CHECK constraint exactly (database_migration.md).
const EVENT_TYPES = ["All", "earnings", "sectoral", "economic", "policy", "geopolitical", "regulatory", "natural_disaster"];

export default function MarketEventsPage() {
  const [events, setEvents]       = useState<MarketEvent[]>([]);
  const [filter, setFilter]       = useState("All");
  const [impact, setImpact]       = useState("All");
  const [loading, setLoading]     = useState(true);

  useEffect(() => {
    getMarketEvents(100).then(setEvents).finally(() => setLoading(false));
  }, []);

  const filtered = events.filter(e => {
    if (filter !== "All" && e.event_type !== filter) return false;
    if (impact !== "All" && e.impact_level !== impact) return false;
    return true;
  });

  if (loading) return <LoadingSpinner label="Loading market events..." />;

  return (
    <div className="max-w-6xl mx-auto space-y-6 font-mono">
      <div className="border-b border-[#2A2A2A] pb-4 flex items-center gap-3">
        <Radio size={18} className="text-[#FFB300]" />
        <div>
          <h1 className="text-[#E0E0E0] text-lg font-bold tracking-wider">MARKET EVENTS</h1>
          <p className="text-[#888] text-[10px] tracking-wider">{events.length} TOTAL EVENTS</p>
        </div>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-3">
        <div className="flex items-center gap-2">
          <span className="text-[#555] text-[10px] uppercase tracking-wider">Type:</span>
          {EVENT_TYPES.map(t => (
            <button
              key={t}
              onClick={() => setFilter(t)}
              className={`px-3 py-1 text-[11px] uppercase tracking-wide transition-colors border ${
                filter === t
                  ? "bg-[#F5821F]/15 text-[#F5821F] border-[#F5821F]/40"
                  : "text-[#888] border-[#2A2A2A] hover:text-[#E0E0E0] hover:border-[#F5821F]/40"
              }`}
            >
              {t}
            </button>
          ))}
        </div>
        <div className="flex items-center gap-2">
          <span className="text-[#555] text-[10px] uppercase tracking-wider">Impact:</span>
          {["All", "high", "medium", "low"].map(t => (
            <button
              key={t}
              onClick={() => setImpact(t)}
              className={`px-3 py-1 text-[11px] uppercase tracking-wide transition-colors border ${
                impact === t
                  ? "bg-[#FFB300]/15 text-[#FFB300] border-[#FFB300]/40"
                  : "text-[#888] border-[#2A2A2A] hover:text-[#E0E0E0] hover:border-[#FFB300]/40"
              }`}
            >
              {t}
            </button>
          ))}
        </div>
      </div>

      <div className="border border-[#2A2A2A] bg-black">
        <table>
          <thead>
            <tr>
              <th>Date</th>
              <th>Event</th>
              <th>Type</th>
              <th>Impact</th>
              <th>Sectors</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {filtered.map(ev => {
              let sectors: string[] = [];
              try { sectors = JSON.parse(ev.affected_sectors || "[]"); } catch {}
              return (
                <tr key={ev.event_id}>
                  <td className="text-[#888] whitespace-nowrap">{ev.event_date?.slice(0, 10)}</td>
                  <td>
                    <Link href={`/market-events/${ev.event_id}`} className="text-[#E0E0E0] hover:text-[#F5821F] transition-colors font-medium text-xs">
                      {ev.event_title}
                    </Link>
                    {ev.event_description && (
                      <p className="text-[#555] text-[10px] mt-0.5 line-clamp-1">{ev.event_description}</p>
                    )}
                  </td>
                  <td><span className="badge badge-blue">{ev.event_type}</span></td>
                  <td>{impactBadge(ev.impact_level)}</td>
                  <td className="text-[#888] text-[10px] max-w-[160px] truncate">
                    {sectors.slice(0, 3).join(", ") || "—"}
                  </td>
                  <td className="text-right">
                    <Link href={`/market-events/${ev.event_id}`} className="text-[#555] hover:text-[#F5821F] transition-colors inline-flex">
                      <ArrowRight size={14} />
                    </Link>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
        {filtered.length === 0 && (
          <p className="text-[#555] text-xs text-center py-8">No events match the selected filters.</p>
        )}
      </div>
    </div>
  );
}
