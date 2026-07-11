"use client";
import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import {
  getPortfolio, getPositions, getPerformance, getRiskMetrics, refreshRiskMetrics,
  getRiskHistory, getAlerts, markAlertRead, markAllAlertsRead, downloadPortfolioReport,
  PortfolioDetail, Position, Performance, RiskMetrics, RiskHistoryPoint, AlertItem,
} from "@/lib/api";
import { useWebSocket, WsMessage } from "@/hooks/useWebSocket";
import StatCard from "@/components/StatCard";
import SectionHeader from "@/components/SectionHeader";
import LoadingSpinner from "@/components/LoadingSpinner";
import {
  PieChart, Pie, Cell, Tooltip, ResponsiveContainer,
  LineChart, Line, XAxis, YAxis, CartesianGrid, ReferenceLine, Legend,
  BarChart, Bar,
} from "recharts";
import { Sparkles, Wifi, WifiOff, RefreshCw, Bell, CheckCheck, X, FileDown } from "lucide-react";

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

function varColor(v: number) {
  return v < -2 ? "text-[#FF4040]" : v < -1 ? "text-[#FFB300]" : "text-[#00CC44]";
}

type Tab = "overview" | "positions" | "risk";

export default function PortfolioPage() {
  const { id } = useParams<{ id: string }>();
  const pid = Number(id);

  const [portfolio, setPortfolio] = useState<PortfolioDetail | null>(null);
  const [positions, setPositions] = useState<Position[]>([]);
  const [performance, setPerf]    = useState<Performance[]>([]);
  const [loading, setLoading]     = useState(true);
  const [activeTab, setActiveTab] = useState<Tab>("overview");

  const [riskData,       setRiskData]       = useState<RiskMetrics | null>(null);
  const [riskLoading,    setRiskLoading]    = useState(false);
  const [riskRefreshing, setRiskRefreshing] = useState(false);
  const [riskAlerts,     setRiskAlerts]     = useState<AlertItem[]>([]);
  const [riskHistory,    setRiskHistory]    = useState<RiskHistoryPoint[]>([]);

  const [liveValue,     setLiveValue]     = useState<number | null>(null);
  const [liveChangePct, setLiveChangePct] = useState<number | null>(null);
  const [flashKey,      setFlashKey]      = useState(0);
  const [reportDownloading, setReportDownloading] = useState(false);

  const handleDownloadReport = async () => {
    setReportDownloading(true);
    try {
      await downloadPortfolioReport(pid);
    } catch {
      alert("Report generation failed — please try again.");
    } finally {
      setReportDownloading(false);
    }
  };

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

  const loadRisk = async () => {
    setRiskLoading(true);
    try {
      const [data, alerts, history] = await Promise.all([
        getRiskMetrics(pid),
        getAlerts({ portfolio_id: pid, limit: 20 }),
        getRiskHistory(pid, 30),
      ]);
      setRiskData(data);
      setRiskAlerts(alerts);
      setRiskHistory(history);
    } catch {
      setRiskData({ status: "not_computed" });
    } finally {
      setRiskLoading(false);
    }
  };

  const handleDismissRiskAlert = async (alert_id: number) => {
    await markAlertRead(alert_id);
    setRiskAlerts(prev => prev.filter(a => a.alert_id !== alert_id));
  };

  const handleDismissAllRiskAlerts = async () => {
    await markAllAlertsRead(pid);
    setRiskAlerts(prev => prev.map(a => ({ ...a, is_read: true })));
  };

  useEffect(() => {
    if (activeTab === "risk" && !riskData) loadRisk();
  }, [activeTab]);

  const triggerRefresh = async () => {
    setRiskRefreshing(true);
    try {
      await refreshRiskMetrics(pid);
      let tries = 0;
      const poll = setInterval(async () => {
        tries++;
        const data = await getRiskMetrics(pid);
        if (data.status === "ok") {
          setRiskData(data);
          setRiskRefreshing(false);
          clearInterval(poll);
        }
        if (tries >= 7) { clearInterval(poll); setRiskRefreshing(false); loadRisk(); }
      }, 5000);
    } catch {
      setRiskRefreshing(false);
    }
  };

  if (loading) return <LoadingSpinner label="Loading portfolio..." />;
  if (!portfolio) return <p className="text-[#FF4040] text-sm font-mono">Portfolio not found.</p>;

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
  const flashClass   = liveChangePct != null
    ? liveChangePct >= 0 ? "flash-up" : "flash-down"
    : "";

  const TAB_STYLE = (t: Tab) =>
    `px-4 py-2 text-[10px] font-bold tracking-[0.15em] border-b-2 transition-colors cursor-pointer ${
      activeTab === t
        ? "border-[#F5821F] text-[#F5821F]"
        : "border-transparent text-[#888] hover:text-[#CCC]"
    }`;

  return (
    <div className="max-w-7xl mx-auto space-y-6 font-mono">

      {/* ── Header ───────────────────────────────────────────────────────── */}
      <div className="border-b border-[#2A2A2A] pb-4 flex items-start justify-between">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-[#E0E0E0] text-lg font-bold tracking-wider">
              {portfolio.portfolio_name?.toUpperCase()}
            </h1>
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
        <div className="flex items-center gap-2">
          <button
            onClick={handleDownloadReport}
            disabled={reportDownloading}
            className="flex items-center gap-2 px-3 py-2 bg-[#F5821F]/10 border border-[#F5821F]/30 text-[#F5821F] text-[10px] hover:bg-[#F5821F]/20 transition-colors tracking-wider disabled:opacity-50"
          >
            <FileDown size={12} /> {reportDownloading ? "GENERATING…" : "EXPORT REPORT"}
          </button>
          <Link
            href={`/ai-insights?portfolio=${pid}`}
            className="flex items-center gap-2 px-3 py-2 bg-[#F5821F]/10 border border-[#F5821F]/30 text-[#F5821F] text-[10px] hover:bg-[#F5821F]/20 transition-colors tracking-wider"
          >
            <Sparkles size={12} /> AI INSIGHTS
          </Link>
        </div>
      </div>

      {/* ── Stat cards ───────────────────────────────────────────────────── */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-0 border border-[#2A2A2A]">
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

      {/* ── Tab bar ──────────────────────────────────────────────────────── */}
      <div className="border-b border-[#2A2A2A] flex gap-0">
        <button className={TAB_STYLE("overview")}  onClick={() => setActiveTab("overview")}>OVERVIEW</button>
        <button className={TAB_STYLE("positions")} onClick={() => setActiveTab("positions")}>POSITIONS</button>
        <button className={TAB_STYLE("risk")}      onClick={() => setActiveTab("risk")}>RISK ANALYTICS</button>
      </div>

      {/* ── OVERVIEW TAB ─────────────────────────────────────────────────── */}
      {activeTab === "overview" && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
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
      )}

      {/* ── POSITIONS TAB ────────────────────────────────────────────────── */}
      {activeTab === "positions" && (
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
      )}

      {/* ── RISK ANALYTICS TAB ───────────────────────────────────────────── */}
      {activeTab === "risk" && (
        <div className="space-y-6">

          {/* Inline Alerts Panel */}
          {riskAlerts.length > 0 && (
            <div className="border border-[#2A2A2A] overflow-hidden">
              <div
                className="flex items-center justify-between px-3 py-1.5"
                style={{ background: "linear-gradient(to right, #FF8000, #7A2500)" }}
              >
                <div className="flex items-center gap-2">
                  <Bell size={11} className="text-white" />
                  <span className="text-white text-[10px] font-bold tracking-[0.18em] uppercase">Risk Alerts</span>
                  <span className="text-[8px] font-bold px-1.5 py-0.5 rounded-full" style={{ background: "rgba(0,0,0,0.30)", color: "#fff" }}>
                    {riskAlerts.filter(a => !a.is_read).length} unread
                  </span>
                </div>
                <button onClick={handleDismissAllRiskAlerts} className="flex items-center gap-1 text-white/70 hover:text-white text-[9px] tracking-wider transition-colors">
                  <CheckCheck size={10} /> MARK ALL READ
                </button>
              </div>
              <div className="divide-y" style={{ borderColor: "rgba(255,120,0,0.08)" }}>
                {riskAlerts.map(a => {
                  const colorMap: Record<string, string> = { critical: "#FF4040", warning: "#FFB300", info: "#00CC44" };
                  const color = colorMap[a.severity] ?? "#888";
                  return (
                    <div
                      key={a.alert_id}
                      className="flex items-start gap-3 px-4 py-3 bg-[#0D0D0D] transition-colors"
                      style={{ borderLeft: `3px solid ${a.is_read ? "transparent" : color}`, opacity: a.is_read ? 0.5 : 1 }}
                    >
                      <span className="w-1.5 h-1.5 rounded-full mt-1.5 shrink-0" style={{ background: color }} />
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-0.5">
                          <span className="text-[8px] font-bold tracking-wider px-1 border" style={{ color, borderColor: `${color}40` }}>
                            {a.severity.toUpperCase()}
                          </span>
                          <span className="text-[9px] font-semibold" style={{ color: "#E8C090" }}>{a.title}</span>
                        </div>
                        <p className="text-[9px] leading-relaxed" style={{ color: "#7A5030" }}>{a.message}</p>
                      </div>
                      {!a.is_read && (
                        <button onClick={() => handleDismissRiskAlert(a.alert_id)} className="shrink-0 mt-0.5" title="Dismiss">
                          <X size={11} style={{ color: "#5A3820" }} className="hover:text-[#FF8000] transition-colors" />
                        </button>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* Toolbar */}
          <div className="flex items-center justify-between">
            <div>
              <p className="text-[#888] text-[10px]">
                {riskData?.computed_at
                  ? `Last computed: ${new Date(riskData.computed_at).toLocaleString()} · Price date: ${riskData.price_date ?? "—"}`
                  : "Risk metrics have not been computed yet."}
              </p>
              <p className="text-[#555] text-[9px] mt-0.5">Pre-computed daily at 17:30 ET · Weights based on real-time prices × synthetic quantities</p>
            </div>
            <button
              onClick={triggerRefresh}
              disabled={riskRefreshing}
              className="flex items-center gap-2 px-3 py-2 border border-[#F5821F]/50 text-[#F5821F] text-[10px] hover:bg-[#F5821F]/10 transition-colors tracking-wider disabled:opacity-50"
            >
              <RefreshCw size={11} className={riskRefreshing ? "animate-spin" : ""} />
              {riskRefreshing ? "COMPUTING…" : "REFRESH"}
            </button>
          </div>

          {riskLoading && <LoadingSpinner label="Loading risk metrics..." />}

          {!riskLoading && riskData?.status === "not_computed" && (
            <div className="border border-[#2A2A2A] p-8 text-center">
              <p className="text-[#888] text-[11px] tracking-wider">No risk metrics computed yet.</p>
              <p className="text-[#555] text-[10px] mt-1">Click REFRESH to compute now, or wait for the 17:30 ET daily job.</p>
            </div>
          )}

          {!riskLoading && riskData?.status === "ok" && riskData.var && !riskData.var.error && (
            <>
              {/* VaR Grid */}
              <div>
                <div className="bg-[#F5821F] px-3 py-1.5 mb-0">
                  <span className="text-black text-[10px] font-bold tracking-[0.15em]">VALUE AT RISK (VaR) · HISTORICAL SIMULATION</span>
                </div>
                <div className="grid grid-cols-2 md:grid-cols-4 border border-[#2A2A2A] border-t-0">
                  {[
                    { label: "95% 1-DAY",  val: riskData.var.historical?.var_95_1d_pct },
                    { label: "99% 1-DAY",  val: riskData.var.historical?.var_99_1d_pct },
                    { label: "95% 10-DAY", val: riskData.var.historical?.var_95_10d_pct },
                    { label: "99% 10-DAY", val: riskData.var.historical?.var_99_10d_pct },
                  ].map(({ label, val }, i) => (
                    <div key={label} className={`p-4 bg-[#0D0D0D] ${i < 3 ? "border-r border-[#2A2A2A]" : ""}`}>
                      <p className="text-[#888] text-[9px] font-bold tracking-[0.12em] mb-2">{label}</p>
                      <p className={`text-2xl font-bold tabular-nums ${varColor(val ?? 0)}`}>
                        {val != null ? `${val.toFixed(2)}%` : "—"}
                      </p>
                      <p className="text-[#555] text-[9px] mt-1">max expected loss</p>
                    </div>
                  ))}
                </div>
                {riskData.var.distribution && (
                  <div className="border border-[#2A2A2A] border-t-0 bg-[#0D0D0D] px-4 py-2 flex gap-8 flex-wrap">
                    <span className="text-[#888] text-[9px]">
                      DAILY VOL <span className="text-[#E0E0E0] ml-1">{riskData.var.distribution.daily_vol_pct.toFixed(3)}%</span>
                    </span>
                    <span className="text-[#888] text-[9px]">
                      ANN. VOL <span className="text-[#E0E0E0] ml-1">{riskData.var.distribution.annualized_vol_pct.toFixed(2)}%</span>
                    </span>
                    <span className="text-[#888] text-[9px]">
                      SKEWNESS <span className="text-[#E0E0E0] ml-1">{riskData.var.distribution.skewness.toFixed(3)}</span>
                    </span>
                    <span className="text-[#888] text-[9px]">
                      EX. KURTOSIS <span className="text-[#E0E0E0] ml-1">{riskData.var.distribution.excess_kurtosis.toFixed(3)}</span>
                    </span>
                    <span className="text-[#888] text-[9px]">
                      OBS <span className="text-[#E0E0E0] ml-1">{riskData.var.observations}</span>
                    </span>
                  </div>
                )}
              </div>

              {/* Stress Tests */}
              {riskData.stress_tests && riskData.stress_tests.length > 0 && (
                <div>
                  <div className="bg-[#F5821F] px-3 py-1.5">
                    <span className="text-black text-[10px] font-bold tracking-[0.15em]">HISTORICAL STRESS TESTS</span>
                  </div>
                  <div className="border border-[#2A2A2A] border-t-0 overflow-x-auto">
                    <table>
                      <thead>
                        <tr>
                          <th>SCENARIO</th>
                          <th>PERIOD</th>
                          <th className="text-right">PORTFOLIO IMPACT</th>
                          <th className="text-right">WORST POSITION</th>
                          <th className="text-right">WORST RETURN</th>
                          <th className="text-right">COVERAGE</th>
                        </tr>
                      </thead>
                      <tbody>
                        {riskData.stress_tests.map(st => (
                          <tr key={st.name}>
                            <td className="font-bold text-[#E0E0E0]">{st.name}</td>
                            <td className="text-[#888]">{st.label}</td>
                            <td className={`text-right font-bold tabular-nums text-lg ${st.portfolio_impact_pct < 0 ? "text-[#FF4040]" : "text-[#00CC44]"}`}>
                              {st.portfolio_impact_pct >= 0 ? "+" : ""}{st.portfolio_impact_pct.toFixed(2)}%
                            </td>
                            <td className="text-right text-[#F5821F] tabular-nums font-bold">{st.worst_position}</td>
                            <td className={`text-right tabular-nums ${st.worst_position_pct < 0 ? "text-[#FF4040]" : "text-[#00CC44]"}`}>
                              {st.worst_position_pct >= 0 ? "+" : ""}{st.worst_position_pct.toFixed(2)}%
                            </td>
                            <td className="text-right text-[#888] text-[10px]">
                              {st.tickers_with_data}/{st.tickers_total} tickers
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}

              {/* Factor Exposure */}
              {riskData.factor_exposure && !riskData.factor_exposure.error && riskData.factor_exposure.factors && (
                <div>
                  <div className="bg-[#F5821F] px-3 py-1.5">
                    <span className="text-black text-[10px] font-bold tracking-[0.15em]">FACTOR EXPOSURE · OLS REGRESSION (2Y)</span>
                  </div>
                  <div className="border border-[#2A2A2A] border-t-0 bg-[#0D0D0D] p-4">
                    {riskData.factor_exposure.market_interp && (
                      <p className="text-[#FFB300] text-[10px] mb-4 tracking-wider">{riskData.factor_exposure.market_interp}</p>
                    )}
                    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                      <div>
                        <p className="text-[#888] text-[9px] mb-3 tracking-wider">BETA TO FACTOR</p>
                        <ResponsiveContainer width="100%" height={180}>
                          <BarChart
                            data={Object.entries(riskData.factor_exposure.factors).map(([name, f]) => ({
                              name, beta: f.beta,
                            }))}
                            margin={{ left: -10, right: 10 }}
                          >
                            <CartesianGrid strokeDasharray="3 3" stroke="#1A1A1A" />
                            <XAxis dataKey="name" tick={{ fill: "#888", fontSize: 9, fontFamily: "monospace" }} />
                            <YAxis tick={{ fill: "#888", fontSize: 9, fontFamily: "monospace" }} />
                            <Tooltip
                              contentStyle={{ background: "#0D0D0D", border: "1px solid #2A2A2A", fontSize: 10, fontFamily: "monospace" }}
                              formatter={(v: unknown) => [Number(v).toFixed(3), "Beta"]}
                            />
                            <Bar dataKey="beta" fill="#F5821F" />
                          </BarChart>
                        </ResponsiveContainer>
                      </div>
                      <div>
                        <p className="text-[#888] text-[9px] mb-3 tracking-wider">FACTOR DETAIL</p>
                        <table>
                          <thead>
                            <tr>
                              <th>FACTOR</th>
                              <th>PROXY</th>
                              <th className="text-right">BETA</th>
                              <th className="text-right">R²</th>
                            </tr>
                          </thead>
                          <tbody>
                            {Object.entries(riskData.factor_exposure.factors).map(([fname, f]) => (
                              <tr key={fname}>
                                <td className="text-[#E0E0E0]">{fname}</td>
                                <td className="text-[#F5821F] font-bold">{f.ticker}</td>
                                <td className={`text-right tabular-nums font-bold ${f.beta > 1.2 ? "text-[#FF4040]" : f.beta < 0.5 ? "text-[#00CC44]" : "text-[#E0E0E0]"}`}>
                                  {f.beta.toFixed(3)}
                                </td>
                                <td className="text-right text-[#888] tabular-nums">{(f.r_squared * 100).toFixed(1)}%</td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {/* VaR Trend Chart */}
              <div>
                <div className="bg-[#F5821F] px-3 py-1.5">
                  <span className="text-black text-[10px] font-bold tracking-[0.15em]">VAR TREND · 30-DAY HISTORY</span>
                </div>
                {riskHistory.length < 2 ? (
                  <div className="border border-[#2A2A2A] border-t-0 bg-[#0D0D0D] p-6 text-center">
                    <p className="text-[#888] text-[10px] tracking-wider">No trend data yet.</p>
                    <p className="text-[#555] text-[9px] mt-1">Run the risk job daily to build history. At least 2 data points needed.</p>
                  </div>
                ) : (
                  <div className="border border-[#2A2A2A] border-t-0 bg-[#0D0D0D] p-4">
                    <p className="text-[#555] text-[9px] mb-3 tracking-wider">
                      LOSS % (ABSOLUTE VALUE) · DASHED LINES = ALERT THRESHOLDS (WARNING 2% / CRITICAL 3.5%)
                    </p>
                    <ResponsiveContainer width="100%" height={200}>
                      <LineChart
                        data={riskHistory.map(r => ({
                          date:   r.price_date?.slice(5) ?? r.computed_at.slice(5, 10),
                          var_95: r.var_95_1d_pct != null ? Math.abs(r.var_95_1d_pct) : null,
                          var_99: r.var_99_1d_pct != null ? Math.abs(r.var_99_1d_pct) : null,
                        }))}
                        margin={{ top: 4, right: 16, bottom: 0, left: 0 }}
                      >
                        <CartesianGrid strokeDasharray="3 3" stroke="#1A1A1A" />
                        <XAxis
                          dataKey="date"
                          tick={{ fill: "#888", fontSize: 9, fontFamily: "monospace" }}
                          interval="preserveStartEnd"
                        />
                        <YAxis
                          tick={{ fill: "#888", fontSize: 9, fontFamily: "monospace" }}
                          tickFormatter={v => `${v.toFixed(1)}%`}
                          width={44}
                        />
                        <Tooltip
                          contentStyle={{ background: "#0D0D0D", border: "1px solid #2A2A2A", fontSize: 10, fontFamily: "monospace" }}
                          formatter={(v: unknown) => [`${Number(v).toFixed(3)}%`, ""]}
                        />
                        <Legend
                          wrapperStyle={{ fontSize: 9, fontFamily: "monospace", color: "#888", paddingTop: 8 }}
                          formatter={(value) => value === "var_95" ? "95% VaR (1-day)" : "99% VaR (1-day)"}
                        />
                        <ReferenceLine y={2}   stroke="#FFB300" strokeDasharray="4 2" strokeWidth={1} label={{ value: "WARN", fill: "#FFB300", fontSize: 8, fontFamily: "monospace" }} />
                        <ReferenceLine y={3.5} stroke="#FF4040" strokeDasharray="4 2" strokeWidth={1} label={{ value: "CRIT", fill: "#FF4040", fontSize: 8, fontFamily: "monospace" }} />
                        <Line type="monotone" dataKey="var_95" stroke="#FFB300" strokeWidth={1.5} dot={false} connectNulls />
                        <Line type="monotone" dataKey="var_99" stroke="#FF4040" strokeWidth={1.5} dot={false} connectNulls />
                      </LineChart>
                    </ResponsiveContainer>
                  </div>
                )}
              </div>
            </>
          )}
        </div>
      )}
    </div>
  );
}
