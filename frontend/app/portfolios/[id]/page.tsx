"use client";
import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import {
  getPortfolio, getPositions, getPerformance,
  PortfolioDetail, Position, Performance
} from "@/lib/api";
import StatCard from "@/components/StatCard";
import SectionHeader from "@/components/SectionHeader";
import LoadingSpinner from "@/components/LoadingSpinner";
import {
  PieChart, Pie, Cell, Tooltip, ResponsiveContainer,
  LineChart, Line, XAxis, YAxis, CartesianGrid
} from "recharts";
import { Sparkles } from "lucide-react";

const COLORS = ["#1e90ff","#00d084","#a78bfa","#f5c518","#ff4d4d","#38bdf8","#fb923c","#e879f9"];

function fmt(n: number | null | undefined) {
  if (n == null) return "—";
  if (Math.abs(n) >= 1e9) return `$${(n / 1e9).toFixed(2)}B`;
  if (Math.abs(n) >= 1e6) return `$${(n / 1e6).toFixed(2)}M`;
  return `$${Number(n).toLocaleString()}`;
}

function pct(n: number | null | undefined) {
  if (n == null) return "—";
  const v = Number(n);
  return `${v >= 0 ? "+" : ""}${v.toFixed(2)}%`;
}

export default function PortfolioPage() {
  const { id } = useParams<{ id: string }>();
  const pid = Number(id);

  const [portfolio, setPortfolio]   = useState<PortfolioDetail | null>(null);
  const [positions, setPositions]   = useState<Position[]>([]);
  const [performance, setPerf]      = useState<Performance[]>([]);
  const [loading, setLoading]       = useState(true);

  useEffect(() => {
    Promise.all([getPortfolio(pid), getPositions(pid), getPerformance(pid, 30)])
      .then(([port, pos, perf]) => {
        setPortfolio(port);
        setPositions(pos.sort((a, b) => (Number(b.weight) || 0) - (Number(a.weight) || 0)));
        setPerf([...perf].reverse());
      })
      .finally(() => setLoading(false));
  }, [pid]);

  if (loading) return <LoadingSpinner label="Loading portfolio..." />;
  if (!portfolio) return <p className="text-[#ff4d4d] text-sm">Portfolio not found.</p>;

  // Sector allocation for pie chart
  const sectorMap: Record<string, number> = {};
  positions.forEach(p => {
    const sec = p.security?.sector || "Other";
    sectorMap[sec] = (sectorMap[sec] || 0) + (Number(p.weight) || 0);
  });
  const sectorData = Object.entries(sectorMap)
    .sort((a, b) => b[1] - a[1])
    .map(([name, value]) => ({ name, value: parseFloat(value.toFixed(1)) }));

  const latest = performance[performance.length - 1];

  return (
    <div className="max-w-7xl mx-auto space-y-6">
      {/* Header */}
      <div className="border-b border-[#2a2a3a] pb-4 flex items-start justify-between">
        <div>
          <h1 className="text-[#e8e8f0] text-lg font-semibold">{portfolio.portfolio_name}</h1>
          <p className="text-[#5a5a70] text-xs mt-0.5">
            {portfolio.strategy_type} · {portfolio.currency} · {portfolio.positions_count} positions
            {portfolio.customer && ` · ${portfolio.customer.customer_name}`}
          </p>
        </div>
        <Link
          href={`/ai-insights?portfolio=${pid}`}
          className="flex items-center gap-2 px-3 py-2 bg-[#a78bfa]/10 border border-[#a78bfa]/20 rounded text-[#a78bfa] text-xs hover:bg-[#a78bfa]/20 transition-colors"
        >
          <Sparkles size={13} /> AI Insights
        </Link>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatCard label="Total Value" value={fmt(Number(portfolio.total_value))} accent="blue" />
        <StatCard label="YTD Return" value={pct(latest?.ytd_return)}
          positive={(latest?.ytd_return ?? 0) > 0} negative={(latest?.ytd_return ?? 0) < 0} />
        <StatCard label="Sharpe Ratio" value={latest?.sharpe_ratio != null ? Number(latest.sharpe_ratio).toFixed(2) : "—"} />
        <StatCard label="Volatility" value={latest?.volatility != null ? `${Number(latest.volatility).toFixed(1)}%` : "—"} accent="yellow" />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Sector Allocation */}
        <div className="bg-[#111118] border border-[#2a2a3a] rounded-lg p-5">
          <SectionHeader title="Sector Allocation" />
          <ResponsiveContainer width="100%" height={180}>
            <PieChart>
              <Pie data={sectorData} cx="50%" cy="50%" innerRadius={50} outerRadius={80}
                dataKey="value" paddingAngle={2}>
                {sectorData.map((_, i) => (
                  <Cell key={i} fill={COLORS[i % COLORS.length]} />
                ))}
              </Pie>
              <Tooltip
                contentStyle={{ background: "#1a1a24", border: "1px solid #2a2a3a", borderRadius: 6, fontSize: 11 }}
                formatter={(v: unknown) => [`${v}%`, ""]}
              />
            </PieChart>
          </ResponsiveContainer>
          <div className="space-y-1.5 mt-2">
            {sectorData.slice(0, 6).map((s, i) => (
              <div key={s.name} className="flex items-center justify-between text-[11px]">
                <div className="flex items-center gap-2">
                  <span className="w-2 h-2 rounded-full" style={{ background: COLORS[i % COLORS.length] }} />
                  <span className="text-[#9898b0] truncate max-w-[120px]">{s.name}</span>
                </div>
                <span className="text-[#e8e8f0]">{s.value}%</span>
              </div>
            ))}
          </div>
        </div>

        {/* Performance chart */}
        <div className="lg:col-span-2 bg-[#111118] border border-[#2a2a3a] rounded-lg p-5">
          <SectionHeader title="30-Day Performance" sub="Portfolio total value" />
          <ResponsiveContainer width="100%" height={220}>
            <LineChart data={performance} margin={{ top: 4, right: 8, bottom: 0, left: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#2a2a3a" />
              <XAxis dataKey="as_of_date" tick={{ fill: "#5a5a70", fontSize: 10 }}
                tickFormatter={v => v?.slice(5)} interval="preserveStartEnd" />
              <YAxis tick={{ fill: "#5a5a70", fontSize: 10 }}
                tickFormatter={v => `$${(v/1e6).toFixed(1)}M`} width={60} />
              <Tooltip
                contentStyle={{ background: "#1a1a24", border: "1px solid #2a2a3a", borderRadius: 6, fontSize: 11 }}
                formatter={(v: unknown) => [fmt(v as number), "Value"]}
                labelFormatter={l => l?.slice(0, 10)}
              />
              <Line type="monotone" dataKey="total_value" stroke="#1e90ff" strokeWidth={2} dot={false} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Positions table */}
      <div className="bg-[#111118] border border-[#2a2a3a] rounded-lg">
        <div className="p-5 border-b border-[#2a2a3a]">
          <SectionHeader title="Positions" sub={`${positions.length} holdings`} />
        </div>
        <div className="overflow-x-auto">
          <table>
            <thead>
              <tr>
                <th>Ticker</th>
                <th>Name</th>
                <th>Sector</th>
                <th>Type</th>
                <th className="text-right">Qty</th>
                <th className="text-right">Avg Cost</th>
                <th className="text-right">Current Price</th>
                <th className="text-right">Market Value</th>
                <th className="text-right">Weight</th>
              </tr>
            </thead>
            <tbody>
              {positions.map(p => {
                const gain = p.current_price - p.avg_cost_basis;
                return (
                  <tr key={p.position_id}>
                    <td className="font-semibold text-[#1e90ff]">{p.security?.ticker_symbol || "—"}</td>
                    <td className="text-[#9898b0] max-w-[160px] truncate">{p.security?.security_name || "—"}</td>
                    <td className="text-[#9898b0]">{p.security?.sector || "—"}</td>
                    <td>
                      <span className={`badge ${p.position_type === "long" ? "badge-blue" : "badge-high"}`}>
                        {p.position_type}
                      </span>
                    </td>
                    <td className="text-right text-[#e8e8f0]">{Number(p.quantity).toLocaleString()}</td>
                    <td className="text-right text-[#9898b0]">${Number(p.avg_cost_basis).toFixed(2)}</td>
                    <td className={`text-right font-medium ${gain >= 0 ? "positive" : "negative"}`}>
                      ${Number(p.current_price).toFixed(2)}
                    </td>
                    <td className="text-right text-[#e8e8f0]">{fmt(Number(p.market_value))}</td>
                    <td className="text-right text-[#e8e8f0]">{Number(p.weight).toFixed(1)}%</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
