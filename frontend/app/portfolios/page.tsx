"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { getPortfolios, Portfolio } from "@/lib/api";
import LoadingSpinner from "@/components/LoadingSpinner";
import { ArrowRight, BarChart3 } from "lucide-react";
import { manrope, GOLD, WHITE, MUTED, NEAR_BLACK, BORDER, fmt, initials } from "@/lib/theme";

export default function PortfoliosPage() {
  const [portfolios, setPortfolios] = useState<Portfolio[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getPortfolios().then(setPortfolios).finally(() => setLoading(false));
  }, []);

  if (loading) return <LoadingSpinner label="Loading portfolios..." />;

  return (
    <div className={`max-w-6xl mx-auto space-y-6 ${manrope.className}`}>
      <div className="flex items-center gap-3">
        <div className="p-2 rounded-lg" style={{ background: "rgba(250,189,73,0.12)" }}>
          <BarChart3 size={18} style={{ color: GOLD }} />
        </div>
        <div>
          <h1 className="text-[18px] font-bold" style={{ color: WHITE }}>Portfolios</h1>
          <p className="text-[11px] tracking-wide" style={{ color: MUTED }}>{portfolios.length} active</p>
        </div>
      </div>

      <div className="rounded-2xl overflow-hidden" style={{ background: NEAR_BLACK, border: `1px solid ${BORDER}` }}>
        <div className="px-2 pb-2 pt-2">
          {portfolios.map(p => (
            <Link
              key={p.portfolio_id}
              href={`/portfolios/${p.portfolio_id}`}
              className="flex items-center gap-4 px-3 py-3 rounded-xl transition-colors group"
              onMouseEnter={e => (e.currentTarget.style.background = "rgba(250,189,73,0.06)")}
              onMouseLeave={e => (e.currentTarget.style.background = "transparent")}
            >
              <div className="w-9 h-9 rounded-lg flex items-center justify-center text-[11px] font-bold shrink-0" style={{ background: "rgba(250,189,73,0.12)", color: GOLD }}>
                {initials(p.portfolio_name)}
              </div>
              <div className="min-w-0 flex-1">
                <p className="text-[14px] font-semibold truncate transition-colors" style={{ color: WHITE }}>
                  {p.portfolio_name}
                </p>
                <p className="text-[11px] mt-0.5" style={{ color: MUTED }}>
                  ID {p.portfolio_id} · {p.strategy_type || "Unclassified"} · {p.currency}
                </p>
              </div>
              <div className="text-right shrink-0 hidden sm:block">
                <p className="text-[13px] font-bold tabular-nums" style={{ color: WHITE }}>{fmt(Number(p.total_value))}</p>
                <p className="text-[11px] tabular-nums" style={{ color: MUTED }}>{fmt(Number(p.cash_balance))} cash</p>
              </div>
              <ArrowRight size={15} className="shrink-0 transition-colors" style={{ color: MUTED }} />
            </Link>
          ))}
          {portfolios.length === 0 && (
            <p className="text-[12px] px-3 py-8 text-center" style={{ color: MUTED }}>No portfolios found.</p>
          )}
        </div>
      </div>
    </div>
  );
}
