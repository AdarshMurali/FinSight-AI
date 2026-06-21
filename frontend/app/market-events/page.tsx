"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { getMarketEvents, MarketEvent } from "@/lib/api";
import SectionHeader from "@/components/SectionHeader";
import LoadingSpinner from "@/components/LoadingSpinner";
import { Radio, ArrowRight } from "lucide-react";

function impactBadge(level: string | null) {
  if (!level) return null;
  const cls = level === "high" ? "badge-high" : level === "medium" ? "badge-medium" : "badge-low";
  return <span className={`badge ${cls}`}>{level.toUpperCase()}</span>;
}

const EVENT_TYPES = ["All", "policy", "geopolitical", "sectoral", "economic"];

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
    <div className="max-w-6xl mx-auto space-y-6">
      <div className="border-b border-[#2a2a3a] pb-4 flex items-center gap-3">
        <Radio size={18} className="text-[#f5c518]" />
        <div>
          <h1 className="text-[#e8e8f0] text-lg font-semibold">Market Events</h1>
          <p className="text-[#5a5a70] text-xs">{events.length} total events</p>
        </div>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-3">
        <div className="flex items-center gap-2">
          <span className="text-[#5a5a70] text-[10px] uppercase tracking-wider">Type:</span>
          {EVENT_TYPES.map(t => (
            <button
              key={t}
              onClick={() => setFilter(t)}
              className={`px-3 py-1 rounded text-[11px] transition-colors ${
                filter === t
                  ? "bg-[#1e90ff]/20 text-[#1e90ff] border border-[#1e90ff]/30"
                  : "text-[#9898b0] hover:text-[#e8e8f0] bg-[#1a1a24]"
              }`}
            >
              {t}
            </button>
          ))}
        </div>
        <div className="flex items-center gap-2">
          <span className="text-[#5a5a70] text-[10px] uppercase tracking-wider">Impact:</span>
          {["All", "high", "medium", "low"].map(t => (
            <button
              key={t}
              onClick={() => setImpact(t)}
              className={`px-3 py-1 rounded text-[11px] transition-colors ${
                impact === t
                  ? "bg-[#f5c518]/20 text-[#f5c518] border border-[#f5c518]/30"
                  : "text-[#9898b0] hover:text-[#e8e8f0] bg-[#1a1a24]"
              }`}
            >
              {t}
            </button>
          ))}
        </div>
      </div>

      <div className="bg-[#111118] border border-[#2a2a3a] rounded-lg overflow-hidden">
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
                  <td className="text-[#9898b0] whitespace-nowrap">{ev.event_date?.slice(0, 10)}</td>
                  <td>
                    <Link href={`/market-events/${ev.event_id}`} className="text-[#e8e8f0] hover:text-[#1e90ff] transition-colors font-medium text-xs">
                      {ev.event_title}
                    </Link>
                    {ev.event_description && (
                      <p className="text-[#5a5a70] text-[10px] mt-0.5 line-clamp-1">{ev.event_description}</p>
                    )}
                  </td>
                  <td><span className="badge badge-blue">{ev.event_type}</span></td>
                  <td>{impactBadge(ev.impact_level)}</td>
                  <td className="text-[#9898b0] text-[10px] max-w-[160px] truncate">
                    {sectors.slice(0, 3).join(", ") || "—"}
                  </td>
                  <td className="text-right">
                    <Link href={`/market-events/${ev.event_id}`} className="text-[#5a5a70] hover:text-[#1e90ff] transition-colors inline-flex">
                      <ArrowRight size={14} />
                    </Link>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
        {filtered.length === 0 && (
          <p className="text-[#5a5a70] text-xs text-center py-8">No events match the selected filters.</p>
        )}
      </div>
    </div>
  );
}
