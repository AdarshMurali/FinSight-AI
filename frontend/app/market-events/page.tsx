"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { getMarketEvents, MarketEvent } from "@/lib/api";
import LoadingSpinner from "@/components/LoadingSpinner";
import { Radio, ArrowRight } from "lucide-react";
import { manrope, GOLD, WHITE, MUTED, NEAR_BLACK, BORDER } from "@/lib/theme";

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
    <div className={`max-w-6xl mx-auto space-y-6 ${manrope.className}`}>
      <div className="flex items-center gap-3">
        <div className="p-2 rounded-lg" style={{ background: "rgba(250,189,73,0.12)" }}>
          <Radio size={18} style={{ color: GOLD }} />
        </div>
        <div>
          <h1 className="text-[18px] font-bold" style={{ color: WHITE }}>Market Events</h1>
          <p className="text-[11px] tracking-wide" style={{ color: MUTED }}>{events.length} total events</p>
        </div>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-3">
        <div className="flex items-center flex-wrap gap-2">
          <span className="text-[11px] uppercase tracking-wide" style={{ color: MUTED }}>Type:</span>
          {EVENT_TYPES.map(t => (
            <button
              key={t}
              onClick={() => setFilter(t)}
              className="px-3 py-1 text-[11px] rounded-full transition-colors border"
              style={filter === t
                ? { background: "rgba(250,189,73,0.14)", color: GOLD, borderColor: "rgba(250,189,73,0.4)" }
                : { color: MUTED, borderColor: BORDER }}
            >
              {t}
            </button>
          ))}
        </div>
        <div className="flex items-center flex-wrap gap-2">
          <span className="text-[11px] uppercase tracking-wide" style={{ color: MUTED }}>Impact:</span>
          {["All", "high", "medium", "low"].map(t => (
            <button
              key={t}
              onClick={() => setImpact(t)}
              className="px-3 py-1 text-[11px] rounded-full transition-colors border"
              style={impact === t
                ? { background: "rgba(255,204,29,0.14)", color: "#FFCC1D", borderColor: "rgba(255,204,29,0.4)" }
                : { color: MUTED, borderColor: BORDER }}
            >
              {t}
            </button>
          ))}
        </div>
      </div>

      <div className="rounded-2xl overflow-hidden" style={{ background: NEAR_BLACK, border: `1px solid ${BORDER}` }}>
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
                  <td className="whitespace-nowrap" style={{ color: MUTED }}>{ev.event_date?.slice(0, 10)}</td>
                  <td>
                    <Link href={`/market-events/${ev.event_id}`} className="transition-colors font-medium text-xs" style={{ color: WHITE }}>
                      {ev.event_title}
                    </Link>
                    {ev.event_description && (
                      <p className="text-[10px] mt-0.5 line-clamp-1" style={{ color: MUTED }}>{ev.event_description}</p>
                    )}
                  </td>
                  <td><span className="badge badge-blue">{ev.event_type}</span></td>
                  <td>{impactBadge(ev.impact_level)}</td>
                  <td className="text-[10px] max-w-[160px] truncate" style={{ color: MUTED }}>
                    {sectors.slice(0, 3).join(", ") || "—"}
                  </td>
                  <td className="text-right">
                    <Link href={`/market-events/${ev.event_id}`} className="inline-flex transition-colors" style={{ color: MUTED }}>
                      <ArrowRight size={14} />
                    </Link>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
        {filtered.length === 0 && (
          <p className="text-xs text-center py-8" style={{ color: MUTED }}>No events match the selected filters.</p>
        )}
      </div>
    </div>
  );
}
