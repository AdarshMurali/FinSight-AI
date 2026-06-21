"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { getPortfolios, getMarketEvents, Portfolio, MarketEvent } from "@/lib/api";
import StatCard from "@/components/StatCard";
import SectionHeader from "@/components/SectionHeader";
import LoadingSpinner from "@/components/LoadingSpinner";
import { ArrowRight } from "lucide-react";

function fmt(n: number | null | undefined) {
  if (n == null) return "—";
  if (Math.abs(n) >= 1e9) return `$${(n / 1e9).toFixed(2)}B`;
  if (Math.abs(n) >= 1e6) return `$${(n / 1e6).toFixed(2)}M`;
  return `$${n.toLocaleString()}`;
}

function impactBadge(level: string | null) {
  if (!level) return null;
  const cls = level === "high" ? "badge-high" : level === "medium" ? "badge-medium" : "badge-low";
  return <span className={`badge ${cls}`}>{level.toUpperCase()}</span>;
}

export default function Dashboard() {
  const [portfolios, setPortfolios] = useState<Portfolio[]>([]);
  const [events, setEvents] = useState<MarketEvent[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([getPortfolios(), getMarketEvents(10)])
      .then(([p, e]) => { setPortfolios(p); setEvents(e); })
      .finally(() => setLoading(false));
  }, []);

  const totalAUM = portfolios.reduce((s, p) => s + (Number(p.total_value) || 0), 0);
  const strategies = [...new Set(portfolios.map(p => p.strategy_type).filter(Boolean))];

  if (loading) return <LoadingSpinner label="Loading dashboard..." />;

  return (
    <div className="max-w-7xl mx-auto space-y-8">
      <div className="border-b border-[#2a2a3a] pb-4">
        <h1 className="text-[#e8e8f0] text-lg font-semibold tracking-wide">Dashboard</h1>
        <p className="text-[#5a5a70] text-xs mt-0.5">
          {new Date().toLocaleDateString("en-US", { weekday: "long", year: "numeric", month: "long", day: "numeric" })}
        </p>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatCard label="Total AUM" value={fmt(totalAUM)} accent="blue" />
        <StatCard label="Portfolios" value={portfolios.length} accent="blue" />
        <StatCard label="Strategies" value={strategies.length} sub={strategies.slice(0, 2).join(", ") || "—"} />
        <StatCard label="Recent Events" value={events.length} sub="last 10 events" accent="yellow" />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Portfolios */}
        <div className="bg-[#111118] border border-[#2a2a3a] rounded-lg p-5">
          <SectionHeader
            title="Portfolios"
            sub={`${portfolios.length} active`}
            action={
              <Link href="/portfolios" className="text-[#1e90ff] text-xs hover:underline flex items-center gap-1">
                View all <ArrowRight size={12} />
              </Link>
            }
          />
          <div className="space-y-2">
            {portfolios.slice(0, 8).map(p => (
              <Link
                key={p.portfolio_id}
                href={`/portfolios/${p.portfolio_id}`}
                className="flex items-center justify-between px-3 py-2.5 rounded bg-[#1a1a24] hover:bg-[#222230] transition-colors group"
              >
                <div>
                  <p className="text-[#e8e8f0] text-xs font-medium group-hover:text-[#1e90ff] transition-colors">
                    {p.portfolio_name}
                  </p>
                  <p className="text-[#5a5a70] text-[10px] mt-0.5">{p.strategy_type || "—"} · {p.currency}</p>
                </div>
                <div className="text-right flex items-center gap-2">
                  <p className="text-[#e8e8f0] text-xs">{fmt(Number(p.total_value))}</p>
                  <ArrowRight size={12} className="text-[#5a5a70] group-hover:text-[#1e90ff] transition-colors" />
                </div>
              </Link>
            ))}
          </div>
        </div>

        {/* Market Events */}
        <div className="bg-[#111118] border border-[#2a2a3a] rounded-lg p-5">
          <SectionHeader
            title="Recent Market Events"
            sub="latest alerts"
            action={
              <Link href="/market-events" className="text-[#1e90ff] text-xs hover:underline flex items-center gap-1">
                View all <ArrowRight size={12} />
              </Link>
            }
          />
          <div className="space-y-2">
            {events.slice(0, 8).map(ev => (
              <Link
                key={ev.event_id}
                href={`/market-events/${ev.event_id}`}
                className="block px-3 py-2.5 rounded bg-[#1a1a24] hover:bg-[#222230] transition-colors"
              >
                <div className="flex items-center justify-between gap-2">
                  <p className="text-[#e8e8f0] text-xs truncate flex-1">{ev.event_title}</p>
                  {impactBadge(ev.impact_level)}
                </div>
                <div className="flex gap-3 mt-1">
                  <span className="text-[#5a5a70] text-[10px]">{ev.event_type}</span>
                  <span className="text-[#5a5a70] text-[10px]">{ev.event_date?.slice(0, 10)}</span>
                </div>
              </Link>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
