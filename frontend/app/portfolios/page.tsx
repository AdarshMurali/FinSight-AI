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
    <div className="max-w-6xl mx-auto space-y-6">
      <div className="border-b border-[#2a2a3a] pb-4 flex items-center gap-3">
        <BarChart3 size={18} className="text-[#1e90ff]" />
        <div>
          <h1 className="text-[#e8e8f0] text-lg font-semibold">Portfolios</h1>
          <p className="text-[#5a5a70] text-xs">{portfolios.length} portfolios</p>
        </div>
      </div>

      <div className="bg-[#111118] border border-[#2a2a3a] rounded-lg overflow-hidden">
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
                  <Link href={`/portfolios/${p.portfolio_id}`} className="text-[#1e90ff] hover:underline font-medium">
                    {p.portfolio_name}
                  </Link>
                  <p className="text-[#5a5a70] text-[10px] mt-0.5">ID: {p.portfolio_id}</p>
                </td>
                <td className="text-[#9898b0]">{p.strategy_type || "—"}</td>
                <td className="text-[#9898b0]">{p.currency}</td>
                <td className="text-right text-[#e8e8f0] font-medium">{fmt(Number(p.total_value))}</td>
                <td className="text-right text-[#9898b0]">{fmt(Number(p.cash_balance))}</td>
                <td className="text-right">
                  <Link href={`/portfolios/${p.portfolio_id}`} className="text-[#5a5a70] hover:text-[#1e90ff] transition-colors inline-flex">
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
