"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { getPortfolios, Portfolio } from "@/lib/api";
import LoadingSpinner from "@/components/LoadingSpinner";
import { ArrowRight, BarChart3 } from "lucide-react";

function fmt(n: number | null | undefined) {
  if (n == null) return "—";
  if (Math.abs(n) >= 1e9) return `$${(n / 1e9).toFixed(2)}B`;
  if (Math.abs(n) >= 1e6) return `$${(n / 1e6).toFixed(2)}M`;
  return `$${Number(n).toLocaleString()}`;
}

export default function PortfoliosPage() {
  const [portfolios, setPortfolios] = useState<Portfolio[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getPortfolios().then(setPortfolios).finally(() => setLoading(false));
  }, []);

  if (loading) return <LoadingSpinner label="Loading portfolios..." />;

  return (
    <div className="max-w-6xl mx-auto space-y-6 font-mono">
      <div className="border-b border-[#2A2A2A] pb-4 flex items-center gap-3">
        <BarChart3 size={18} className="text-[#F5821F]" />
        <div>
          <h1 className="text-[#E0E0E0] text-lg font-bold tracking-wider">PORTFOLIOS</h1>
          <p className="text-[#888] text-[10px] tracking-wider">{portfolios.length} PORTFOLIOS</p>
        </div>
      </div>

      <div className="border border-[#2A2A2A] bg-black">
        <table>
          <thead>
            <tr>
              <th>Portfolio</th>
              <th>Strategy</th>
              <th>Currency</th>
              <th className="text-right">Total Value</th>
              <th className="text-right">Cash</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {portfolios.map(p => (
              <tr key={p.portfolio_id} className="cursor-pointer">
                <td>
                  <Link href={`/portfolios/${p.portfolio_id}`} className="text-[#F5821F] hover:text-[#FFA040] transition-colors font-bold tracking-wide text-xs">
                    {p.portfolio_name?.toUpperCase()}
                  </Link>
                  <p className="text-[#555] text-[10px] mt-0.5">ID: {p.portfolio_id}</p>
                </td>
                <td className="text-[#888]">{p.strategy_type || "—"}</td>
                <td className="text-[#888]">{p.currency}</td>
                <td className="text-right text-[#E0E0E0] font-bold tabular-nums">{fmt(Number(p.total_value))}</td>
                <td className="text-right text-[#888] tabular-nums">{fmt(Number(p.cash_balance))}</td>
                <td className="text-right">
                  <Link href={`/portfolios/${p.portfolio_id}`} className="text-[#555] hover:text-[#F5821F] transition-colors inline-flex">
                    <ArrowRight size={14} />
                  </Link>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
