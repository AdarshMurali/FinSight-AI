"use client";
import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import {
  getPortfolio, getPositions, getPerformance,
  PortfolioDetail, Position, Performance,
} from "@/lib/api";
import { useWebSocket, WsMessage } from "@/hooks/useWebSocket";
import StatCard from "@/components/StatCard";
import SectionHeader from "@/components/SectionHeader";
import LoadingSpinner from "@/components/LoadingSpinner";
import {
  PieChart, Pie, Cell, Tooltip, ResponsiveContainer,
  LineChart, Line, XAxis, YAxis, CartesianGrid,
} from "recharts";
import { Sparkles, Wifi, WifiOff } from "lucide-react";

const COLORS = ["#F5821F","#00CC44","#FFB300","#3b82f6","#FF4040","#a78bfa","#38bdf8","#e879f9"];

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

  const [portfolio, setPortfolio] = useState<PortfolioDetail | null>(null);
  const [positions, setPositions] = useState<Position[]>([]);
  const [performance, setPerf]    = useState<Performance[]>([]);
  const [loading, setLoading]     = useState(true);

  // Live WebSocket state for this specific portfolio
  const [liveValue,     setLiveValue]     = useState<number | null>(null);
  const [liveChangePct, setLiveChangePct] = useState<number | null>(null);
  const [flashKey,      setFlashKey]      = useState(0);

  // Subscribe to WebSocket and filter updates by portfolio_id
  const { connected } = useWebSocket((msg: WsMessage) => {
    if (msg.type === "portfolio_update" && msg.portfolio_id === pid) {
      setLiveValue(msg.total_value ?? null);
      setLiveChangePct(msg.change_pct ?? null);
      setFlashKey(k => k + 1);
    }
  });

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
  if (!portfolio) return <p className="text-[#FF4040] text-sm font-mono">Portfolio not found.</p>;

  // Sector allocation for pie chart
  const sectorMap: Record<string, number> = {};
  positions.forEach(p => {
    const sec = p.security?.sector || "Other";
    sectorMap[sec] = (sectorMap[sec] || 0) + (Number(p.weight) || 0);
  });
  const sectorData = Object.entries(sectorMap)
    .sort((a, b) => b[1] - a[1])
    .map(([name, value]) => ({ name, value: parseFloat(value.toFixed(1)) }));

  const latest       = performance[performance.length - 1];
  const displayValue = liveValue ?? Number(portfolio.total_value);

  // Flash class driven by latest change direction
  const flashClass = liveChangePct != null
    ? liveChangePct >= 0 ? "flash-up" : "flash-down"
    : "";

  return (
    <div className="max-w-7xl mx-auto space-y-6 font-mono">

      {/* ── Header ───────────────────────────────────────────────────────── */}
      <div className="border-b border-[#2A2A2A] pb-4 flex items-start justify-between">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-[#E0E0E0] text-lg font-bold tracking-wider">
              {portfolio.portfolio_name?.toUpperCase()}
            </h1>
            {/* WebSocket connection indicator */}
            <div className="flex items-center gap-1.5">
              {connected
                ? <Wifi size={11} className="text-[#00CC44]" />
                : <WifiOff size={11} className="text-[#FFB300]" />}
              <span className={`text-[9px] font-bold tracking-wider ${connected ? "text-[#00CC44]" : "text-[#FFB300]"}`}>
                {connected ? "LIVE" : "OFFLINE"}
              </span>
            </div>
          </div>
          <p className="text-[#888] text-[10px] mt-0.5 tracking-wider">
            {portfolio.strategy_type?.toUpperCase()} · {portfolio.currency}
            · {portfolio.positions_count} POSITIONS
            {portfolio.customer && ` · ${portfolio.customer.customer_name}`}
          </p>
        </div>
        <Link
          href={`/ai-insights?portfolio=${pid}`}
          className="flex items-center gap-2 px-3 py-2 bg-[#F5821F]/10 border border-[#F5821F]/30 text-[#F5821F] text-[10px] hover:bg-[#F5821F]/20 transition-colors tracking-wider"
        >
          <Sparkles size={12} /> AI INSIGHTS
        </Link>
      </div>

      {/* ── Stat cards ───────────────────────────────────────────────────── */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-0 border border-[#2A2A2A]">

        {/* Total Value — live with flash */}
        <div className="p-4 bg-[#0D0D0D] border-r border-[#2A2A2A]">
          <p className="text-[#F5821F] text-[9px] font-bold tracking-[0.15em] mb-2">TOTAL VALUE</p>
          <p key={flashKey} className={`text-2xl font-bold tabular-nums ${flashClass} text-[#F5821F]`}>
            {fmt(displayValue)}
          </p>
          {liveChangePct != null && (
            <p className={`text-[10px] mt-1 tabular-nums font-bold ${liveChangePct >= 0 ? "text-[#00CC44]" : "text-[#FF4040]"}`}>
              {liveChangePct >= 0 ? "▲" : "▼"} {Math.abs(liveChangePct).toFixed(3)}% LIVE
            </p>
          )}
        </div>

        <div className="p-4 bg-[#0D0D0D] border-r border-[#2A2A2A]">
          <p className="text-[#F5821F] text-[9px] font-bold tracking-[0.15em] mb-2">YTD RETURN</p>
          <p className={`text-2xl font-bold tabular-nums ${(latest?.ytd_return ?? 0) > 0 ? "text-[#00CC44]" : (latest?.ytd_return ?? 0) < 0 ? "text-[#FF4040]" : "text-[#E0E0E0]"}`}>
            {pct(latest?.ytd_return)}
          </p>
        </div>

        <div className="p-4 bg-[#0D0D0D] border-r border-[#2A2A2A]">
          <p className="text-[#F5821F] text-[9px] font-bold tracking-[0.15em] mb-2">SHARPE RATIO</p>
          <p className="text-2xl font-bold tabular-nums text-[#E0E0E0]">
            {latest?.sharpe_ratio != null ? Number(latest.sharpe_ratio).toFixed(2) : "—"}
          </p>
        </div>

        <div className="p-4 bg-[#0D0D0D]">
          <p className="text-[#F5821F] text-[9px] font-bold tracking-[0.15em] mb-2">VOLATILITY</p>
          <p className="text-2xl font-bold tabular-nums text-[#FFB300]">
            {latest?.volatility != null ? `${Number(latest.volatility).toFixed(1)}%` : "—"}
          </p>
        </div>
      </div>

      {/* ── Charts row ───────────────────────────────────────────────────── */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">

        {/* Sector allocation */}
        <div className="bg-[#0D0D0D] border border-[#2A2A2A] p-4">
          <div className="bg-[#F5821F] px-3 py-1.5 -mx-4 -mt-4 mb-4">
            <span className="text-black text-[10px] font-bold tracking-[0.15em]">SECTOR ALLOCATION</span>
          </div>
          <ResponsiveContainer width="100%" height={160}>
            <PieChart>
              <Pie data={sectorData} cx="50%" cy="50%" innerRadius={45} outerRadius={72}
                dataKey="value" paddingAngle={2}>
                {sectorData.map((_, i) => (
                  <Cell key={i} fill={COLORS[i % COLORS.length]} />
                ))}
              </Pie>
              <Tooltip
                contentStyle={{ background: "#0D0D0D", border: "1px solid #2A2A2A", fontSize: 10, fontFamily: "monospace" }}
                formatter={(v: unknown) => [`${v}%`, ""]}
              />
            </PieChart>
          </ResponsiveContainer>
          <div className="space-y-1 mt-2">
            {sectorData.slice(0, 6).map((s, i) => (
              <div key={s.name} className="flex items-center justify-between text-[10px]">
                <div className="flex items-center gap-2">
                  <span className="w-2 h-2 shrink-0" style={{ background: COLORS[i % COLORS.length] }} />
                  <span className="text-[#AAA] truncate max-w-[110px]">{s.name.toUpperCase()}</span>
                </div>
                <span className="text-[#E0E0E0] tabular-nums">{s.value}%</span>
              </div>
            ))}
          </div>
        </div>

        {/* Performance chart */}
        <div className="lg:col-span-2 bg-[#0D0D0D] border border-[#2A2A2A] p-4">
          <div className="bg-[#F5821F] px-3 py-1.5 -mx-4 -mt-4 mb-4">
            <span className="text-black text-[10px] font-bold tracking-[0.15em]">
              30-DAY PERFORMANCE · TOTAL VALUE
            </span>
          </div>
          <ResponsiveContainer width="100%" height={200}>
            <LineChart data={performance} margin={{ top: 4, right: 8, bottom: 0, left: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1A1A1A" />
              <XAxis dataKey="as_of_date" tick={{ fill: "#888", fontSize: 9, fontFamily: "monospace" }}
                tickFormatter={v => v?.slice(5)} interval="preserveStartEnd" />
              <YAxis tick={{ fill: "#888", fontSize: 9, fontFamily: "monospace" }}
                tickFormatter={v => `$${(v/1e6).toFixed(0)}M`} width={52} />
              <Tooltip
                contentStyle={{ background: "#0D0D0D", border: "1px solid #2A2A2A", fontSize: 10, fontFamily: "monospace" }}
                formatter={(v: unknown) => [fmt(v as number), "Value"]}
                labelFormatter={l => l?.slice(0, 10)}
              />
              <Line type="monotone" dataKey="total_value" stroke="#F5821F" strokeWidth={1.5} dot={false} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* ── Positions table ───────────────────────────────────────────────── */}
      <div className="border border-[#2A2A2A]">
        <div className="bg-[#F5821F] px-3 py-1.5">
          <span className="text-black text-[10px] font-bold tracking-[0.15em]">
            POSITIONS · {positions.length} HOLDINGS
          </span>
        </div>
        <div className="overflow-x-auto">
          <table>
            <thead>
              <tr>
                <th>TICKER</th>
                <th>NAME</th>
                <th>SECTOR</th>
                <th>TYPE</th>
                <th className="text-right">QTY</th>
                <th className="text-right">AVG COST</th>
                <th className="text-right">PRICE</th>
                <th className="text-right">MKT VALUE</th>
                <th className="text-right">WEIGHT</th>
              </tr>
            </thead>
            <tbody>
              {positions.map(p => {
                const gain = Number(p.current_price) - Number(p.avg_cost_basis);
                return (
                  <tr key={p.position_id}>
                    <td className="font-bold text-[#F5821F] tracking-wider">
                      {p.security?.ticker_symbol || "—"}
                    </td>
                    <td className="text-[#AAA] max-w-[160px] truncate">
                      {p.security?.security_name || "—"}
                    </td>
                    <td className="text-[#888]">{p.security?.sector || "—"}</td>
                    <td>
                      <span className={`badge ${p.position_type === "long" ? "badge-blue" : "badge-high"}`}>
                        {p.position_type?.toUpperCase()}
                      </span>
                    </td>
                    <td className="text-right text-[#E0E0E0] tabular-nums">
                      {Number(p.quantity).toLocaleString()}
                    </td>
                    <td className="text-right text-[#888] tabular-nums">
                      ${Number(p.avg_cost_basis).toFixed(2)}
                    </td>
                    <td className={`text-right font-bold tabular-nums ${gain >= 0 ? "text-[#00CC44]" : "text-[#FF4040]"}`}>
                      ${Number(p.current_price).toFixed(2)}
                    </td>
                    <td className="text-right text-[#E0E0E0] tabular-nums">
                      {fmt(Number(p.market_value))}
                    </td>
                    <td className="text-right text-[#E0E0E0] tabular-nums">
                      {Number(p.weight).toFixed(1)}%
                    </td>
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
