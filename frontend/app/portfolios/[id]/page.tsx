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
import LoadingSpinner from "@/components/LoadingSpinner";
import {
  PieChart, Pie, Cell, Tooltip, ResponsiveContainer,
  LineChart, Line, XAxis, YAxis, CartesianGrid, ReferenceLine, Legend,
  BarChart, Bar,
} from "recharts";
import { Sparkles, Wifi, WifiOff, RefreshCw, Bell, CheckCheck, X, FileDown } from "lucide-react";
import {
  manrope, GOLD, AMBER_DARK, WHITE, MUTED, GREEN, RED, WARNING,
  NEAR_BLACK, CHART_SURFACE, BORDER, GOLD_SCALE, fmt, pct,
} from "@/lib/theme";

function varColor(v: number) {
  return v < -2 ? RED : v < -1 ? WARNING : GREEN;
}

const chartTick = { fill: MUTED, fontSize: 9 };
const chartTooltipStyle = { background: CHART_SURFACE, border: `1px solid ${BORDER}`, fontSize: 10, borderRadius: 8 };

// ── Gold gradient card header bar (matches the rest of the site) ────────────
function CardHeader({ title }: { title: string }) {
  return (
    <div className="px-4 py-2.5" style={{ background: `linear-gradient(to right, ${GOLD}, ${AMBER_DARK})` }}>
      <span className="text-black text-[11px] font-bold tracking-wide uppercase">{title}</span>
    </div>
  );
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
        getAlerts({ portfolio_id: pid, limit: 20, unread_only: true }),
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
    setRiskAlerts([]);
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
  if (!portfolio) return <p className={`text-sm ${manrope.className}`} style={{ color: RED }}>Portfolio not found.</p>;

  const sectorMap: Record<string, number> = {};
  positions.forEach(p => {
    const sec = p.security?.sector || "Other";
    sectorMap[sec] = (sectorMap[sec] || 0) + (Number(p.weight) || 0);
  });
  // Position.weight is a fraction (0.558 = 55.8%) — same *100 fix as pct()/volatility
  // above. Pie slice proportions are scale-invariant either way; this only affects
  // the displayed legend/tooltip numbers.
  const sectorData = Object.entries(sectorMap)
    .sort((a, b) => b[1] - a[1])
    .map(([name, value]) => ({ name, value: parseFloat((value * 100).toFixed(1)) }));

  const latest       = performance[performance.length - 1];
  const displayValue = liveValue ?? Number(portfolio.total_value);
  const flashClass   = liveChangePct != null
    ? liveChangePct >= 0 ? "flash-up" : "flash-down"
    : "";

  const tabStyle = (t: Tab) => ({
    color: activeTab === t ? GOLD : MUTED,
    borderBottomColor: activeTab === t ? GOLD : "transparent",
  });

  return (
    <div className={`max-w-7xl mx-auto space-y-6 ${manrope.className}`}>

      {/* ── Header ───────────────────────────────────────────────────────── */}
      <div className="pb-4 flex items-start justify-between" style={{ borderBottom: `1px solid ${BORDER}` }}>
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-[19px] font-bold" style={{ color: WHITE }}>
              {portfolio.portfolio_name}
            </h1>
            <div className="flex items-center gap-1.5">
              {connected
                ? <Wifi size={12} style={{ color: GREEN }} />
                : <WifiOff size={12} style={{ color: WARNING }} />}
              <span className="text-[10px] font-bold tracking-wide" style={{ color: connected ? GREEN : WARNING }}>
                {connected ? "LIVE" : "OFFLINE"}
              </span>
            </div>
          </div>
          <p className="text-[11px] mt-0.5 tracking-wide" style={{ color: MUTED }}>
            {portfolio.strategy_type} · {portfolio.currency}
            · {portfolio.positions_count} positions
            {portfolio.customer && ` · ${portfolio.customer.customer_name}`}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={handleDownloadReport}
            disabled={reportDownloading}
            className="flex items-center gap-2 px-3.5 py-2 rounded-full text-[11px] tracking-wide transition-colors disabled:opacity-50"
            style={{ background: "rgba(250,189,73,0.10)", border: `1px solid ${BORDER}`, color: GOLD }}
          >
            <FileDown size={12} /> {reportDownloading ? "Generating…" : "Export report"}
          </button>
          <Link
            href={`/ai-insights?portfolio=${pid}`}
            className="flex items-center gap-2 px-3.5 py-2 rounded-full text-[11px] tracking-wide transition-colors"
            style={{ background: "rgba(250,189,73,0.10)", border: `1px solid ${BORDER}`, color: GOLD }}
          >
            <Sparkles size={12} /> AI Insights
          </Link>
        </div>
      </div>

      {/* ── Stat cards ───────────────────────────────────────────────────── */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <div className="p-4 rounded-2xl" style={{ background: NEAR_BLACK, border: `1px solid ${BORDER}` }}>
          <p className="text-[10px] font-bold tracking-wide mb-2" style={{ color: GOLD }}>TOTAL VALUE</p>
          <p key={flashKey} className={`text-2xl font-extrabold tabular-nums ${flashClass}`} style={{ color: WHITE }}>
            {fmt(displayValue)}
          </p>
          {liveChangePct != null && (
            <p className="text-[10px] mt-1 tabular-nums font-bold" style={{ color: liveChangePct >= 0 ? GREEN : RED }}>
              {liveChangePct >= 0 ? "▲" : "▼"} {Math.abs(liveChangePct).toFixed(3)}% live
            </p>
          )}
        </div>
        <div className="p-4 rounded-2xl" style={{ background: NEAR_BLACK, border: `1px solid ${BORDER}` }}>
          <p className="text-[10px] font-bold tracking-wide mb-2" style={{ color: GOLD }}>YTD RETURN</p>
          <p className="text-2xl font-extrabold tabular-nums" style={{ color: (latest?.ytd_return ?? 0) > 0 ? GREEN : (latest?.ytd_return ?? 0) < 0 ? RED : WHITE }}>
            {pct(latest?.ytd_return)}
          </p>
        </div>
        <div className="p-4 rounded-2xl" style={{ background: NEAR_BLACK, border: `1px solid ${BORDER}` }}>
          <p className="text-[10px] font-bold tracking-wide mb-2" style={{ color: GOLD }}>SHARPE RATIO</p>
          <p className="text-2xl font-extrabold tabular-nums" style={{ color: WHITE }}>
            {latest?.sharpe_ratio != null ? Number(latest.sharpe_ratio).toFixed(2) : "—"}
          </p>
        </div>
        <div className="p-4 rounded-2xl" style={{ background: NEAR_BLACK, border: `1px solid ${BORDER}` }}>
          <p className="text-[10px] font-bold tracking-wide mb-2" style={{ color: GOLD }}>VOLATILITY</p>
          <p className="text-2xl font-extrabold tabular-nums" style={{ color: WARNING }}>
            {latest?.volatility != null ? `${(Number(latest.volatility) * 100).toFixed(1)}%` : "—"}
          </p>
        </div>
      </div>

      {/* ── Tab bar ──────────────────────────────────────────────────────── */}
      <div className="flex gap-0" style={{ borderBottom: `1px solid ${BORDER}` }}>
        {(["overview", "positions", "risk"] as Tab[]).map(t => (
          <button
            key={t}
            className="px-4 py-2.5 text-[11px] font-bold tracking-wide border-b-2 transition-colors cursor-pointer capitalize"
            style={tabStyle(t)}
            onClick={() => setActiveTab(t)}
          >
            {t === "risk" ? "Risk Analytics" : t}
          </button>
        ))}
      </div>

      {/* ── OVERVIEW TAB ─────────────────────────────────────────────────── */}
      {activeTab === "overview" && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          <div className="rounded-2xl overflow-hidden" style={{ background: NEAR_BLACK, border: `1px solid ${BORDER}` }}>
            <CardHeader title="Sector Allocation" />
            <div className="p-4">
              <ResponsiveContainer width="100%" height={160}>
                <PieChart>
                  <Pie data={sectorData} cx="50%" cy="50%" innerRadius={45} outerRadius={72}
                    dataKey="value" paddingAngle={2} stroke={NEAR_BLACK} strokeWidth={2}>
                    {sectorData.map((_, i) => (
                      <Cell key={i} fill={GOLD_SCALE[i % GOLD_SCALE.length]} />
                    ))}
                  </Pie>
                  <Tooltip contentStyle={chartTooltipStyle} formatter={(v: unknown) => [`${v}%`, ""]} />
                </PieChart>
              </ResponsiveContainer>
              <div className="space-y-1.5 mt-2">
                {sectorData.slice(0, 6).map((s, i) => (
                  <div key={s.name} className="flex items-center justify-between text-[11px]">
                    <div className="flex items-center gap-2">
                      <span className="w-2 h-2 rounded-full shrink-0" style={{ background: GOLD_SCALE[i % GOLD_SCALE.length] }} />
                      <span className="truncate max-w-[110px]" style={{ color: WHITE }}>{s.name}</span>
                    </div>
                    <span className="tabular-nums" style={{ color: MUTED }}>{s.value}%</span>
                  </div>
                ))}
              </div>
            </div>
          </div>

          <div className="lg:col-span-2 rounded-2xl overflow-hidden" style={{ background: NEAR_BLACK, border: `1px solid ${BORDER}` }}>
            <CardHeader title="30-Day Performance · Total Value" />
            <div className="p-4">
              <ResponsiveContainer width="100%" height={200}>
                <LineChart data={performance} margin={{ top: 4, right: 8, bottom: 0, left: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke={BORDER} />
                  <XAxis dataKey="as_of_date" tick={chartTick}
                    tickFormatter={v => v?.slice(5)} interval="preserveStartEnd" />
                  <YAxis tick={chartTick}
                    tickFormatter={v => `$${(v/1e6).toFixed(0)}M`} width={52} />
                  <Tooltip
                    contentStyle={chartTooltipStyle}
                    formatter={(v: unknown) => [fmt(v as number), "Value"]}
                    labelFormatter={l => l?.slice(0, 10)}
                  />
                  <Line type="monotone" dataKey="total_value" stroke={GOLD} strokeWidth={1.5} dot={false} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>
      )}

      {/* ── POSITIONS TAB ────────────────────────────────────────────────── */}
      {activeTab === "positions" && (
        <div className="rounded-2xl overflow-hidden" style={{ background: NEAR_BLACK, border: `1px solid ${BORDER}` }}>
          <CardHeader title={`Positions · ${positions.length} holdings`} />
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
                      <td className="font-bold tracking-wide" style={{ color: GOLD }}>
                        {p.security?.ticker_symbol || "—"}
                      </td>
                      <td className="max-w-[160px] truncate" style={{ color: MUTED }}>
                        {p.security?.security_name || "—"}
                      </td>
                      <td style={{ color: MUTED }}>{p.security?.sector || "—"}</td>
                      <td>
                        <span className={`badge ${p.position_type === "long" ? "badge-blue" : "badge-high"}`}>
                          {p.position_type?.toUpperCase()}
                        </span>
                      </td>
                      <td className="text-right tabular-nums" style={{ color: WHITE }}>
                        {Number(p.quantity).toLocaleString()}
                      </td>
                      <td className="text-right tabular-nums" style={{ color: MUTED }}>
                        ${Number(p.avg_cost_basis).toFixed(2)}
                      </td>
                      <td className="text-right font-bold tabular-nums" style={{ color: gain >= 0 ? GREEN : RED }}>
                        ${Number(p.current_price).toFixed(2)}
                      </td>
                      <td className="text-right tabular-nums" style={{ color: WHITE }}>
                        {fmt(Number(p.market_value))}
                      </td>
                      <td className="text-right tabular-nums" style={{ color: WHITE }}>
                        {(Number(p.weight) * 100).toFixed(1)}%
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
            <div className="rounded-2xl overflow-hidden" style={{ border: `1px solid ${BORDER}` }}>
              <div
                className="flex items-center justify-between px-4 py-2.5"
                style={{ background: `linear-gradient(to right, ${GOLD}, ${AMBER_DARK})` }}
              >
                <div className="flex items-center gap-2">
                  <Bell size={12} className="text-black" />
                  <span className="text-black text-[11px] font-bold tracking-wide uppercase">Risk Alerts</span>
                  <span className="text-[9px] font-bold px-1.5 py-0.5 rounded-full" style={{ background: "rgba(0,0,0,0.25)", color: "#fff" }}>
                    {riskAlerts.length} unread
                  </span>
                </div>
                <button onClick={handleDismissAllRiskAlerts} className="flex items-center gap-1 text-black/60 hover:text-black text-[10px] tracking-wide transition-colors">
                  <CheckCheck size={11} /> Mark all read
                </button>
              </div>
              <div style={{ background: NEAR_BLACK }}>
                {riskAlerts.map(a => {
                  const colorMap: Record<string, string> = { critical: RED, warning: WARNING, info: GREEN };
                  const color = colorMap[a.severity] ?? MUTED;
                  return (
                    <div
                      key={a.alert_id}
                      className="flex items-start gap-3 px-4 py-3 transition-colors"
                      style={{ borderLeft: `3px solid ${color}`, borderTop: `1px solid ${BORDER}` }}
                    >
                      <span className="w-1.5 h-1.5 rounded-full mt-1.5 shrink-0" style={{ background: color }} />
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-0.5">
                          <span className="text-[9px] font-bold tracking-wide px-1.5 py-0.5 rounded-full" style={{ color, border: `1px solid ${color}40` }}>
                            {a.severity.toUpperCase()}
                          </span>
                          {a.alert_type === "ai" && (
                            <span
                              className="flex items-center gap-0.5 text-[9px] font-bold tracking-wide px-1.5 py-0.5 rounded-full shrink-0"
                              style={{ color: GOLD, border: `1px solid ${BORDER}`, background: "rgba(250,189,73,0.08)" }}
                              title="Generated by GPT-4o"
                            >
                              <Sparkles size={8} /> AI
                            </span>
                          )}
                          <span className="text-[10px] font-semibold" style={{ color: WHITE }}>{a.title}</span>
                        </div>
                        <p className="text-[10px] leading-relaxed" style={{ color: MUTED }}>{a.message}</p>
                      </div>
                      <button onClick={() => handleDismissRiskAlert(a.alert_id)} className="shrink-0 mt-0.5 p-0.5" title="Mark this alert as read">
                        <X size={11} style={{ color: MUTED }} className="hover:opacity-70 transition-opacity" />
                      </button>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* Toolbar */}
          <div className="flex items-center justify-between">
            <div>
              <p className="text-[11px]" style={{ color: MUTED }}>
                {riskData?.computed_at
                  ? `Last computed: ${new Date(riskData.computed_at).toLocaleString()} · Price date: ${riskData.price_date ?? "—"}`
                  : "Risk metrics have not been computed yet."}
              </p>
              <p className="text-[10px] mt-0.5" style={{ color: MUTED }}>Pre-computed daily at 17:30 ET · Weights based on real-time prices × synthetic quantities</p>
            </div>
            <button
              onClick={triggerRefresh}
              disabled={riskRefreshing}
              className="flex items-center gap-2 px-3.5 py-2 rounded-full text-[11px] tracking-wide transition-colors disabled:opacity-50"
              style={{ border: `1px solid ${BORDER}`, color: GOLD }}
            >
              <RefreshCw size={12} className={riskRefreshing ? "animate-spin" : ""} />
              {riskRefreshing ? "Computing…" : "Refresh"}
            </button>
          </div>

          {riskLoading && <LoadingSpinner label="Loading risk metrics..." />}

          {!riskLoading && riskData?.status === "not_computed" && (
            <div className="rounded-2xl p-8 text-center" style={{ border: `1px solid ${BORDER}` }}>
              <p className="text-[11px] tracking-wide" style={{ color: MUTED }}>No risk metrics computed yet.</p>
              <p className="text-[10px] mt-1" style={{ color: MUTED }}>Click Refresh to compute now, or wait for the 17:30 ET daily job.</p>
            </div>
          )}

          {!riskLoading && riskData?.status === "ok" && riskData.var && !riskData.var.error && (
            <>
              {/* VaR Grid */}
              <div className="rounded-2xl overflow-hidden" style={{ border: `1px solid ${BORDER}` }}>
                <CardHeader title="Value at Risk (VaR) · Historical Simulation" />
                <div className="grid grid-cols-2 md:grid-cols-4 gap-3 p-3" style={{ background: NEAR_BLACK }}>
                  {[
                    { label: "95% 1-DAY",  val: riskData.var.historical?.var_95_1d_pct },
                    { label: "99% 1-DAY",  val: riskData.var.historical?.var_99_1d_pct },
                    { label: "95% 10-DAY", val: riskData.var.historical?.var_95_10d_pct },
                    { label: "99% 10-DAY", val: riskData.var.historical?.var_99_10d_pct },
                  ].map(({ label, val }) => (
                    <div key={label} className="p-3 rounded-xl" style={{ background: "rgba(255,255,255,0.02)", border: `1px solid ${BORDER}` }}>
                      <p className="text-[9px] font-bold tracking-wide mb-2" style={{ color: MUTED }}>{label}</p>
                      <p className="text-2xl font-extrabold tabular-nums" style={{ color: varColor(val ?? 0) }}>
                        {val != null ? `${val.toFixed(2)}%` : "—"}
                      </p>
                      <p className="text-[9px] mt-1" style={{ color: MUTED }}>max expected loss</p>
                    </div>
                  ))}
                </div>
                {riskData.var.distribution && (
                  <div className="px-4 py-3 flex gap-8 flex-wrap" style={{ background: NEAR_BLACK, borderTop: `1px solid ${BORDER}` }}>
                    <span className="text-[10px]" style={{ color: MUTED }}>
                      DAILY VOL <span className="ml-1" style={{ color: WHITE }}>{riskData.var.distribution.daily_vol_pct.toFixed(3)}%</span>
                    </span>
                    <span className="text-[10px]" style={{ color: MUTED }}>
                      ANN. VOL <span className="ml-1" style={{ color: WHITE }}>{riskData.var.distribution.annualized_vol_pct.toFixed(2)}%</span>
                    </span>
                    <span className="text-[10px]" style={{ color: MUTED }}>
                      SKEWNESS <span className="ml-1" style={{ color: WHITE }}>{riskData.var.distribution.skewness.toFixed(3)}</span>
                    </span>
                    <span className="text-[10px]" style={{ color: MUTED }}>
                      EX. KURTOSIS <span className="ml-1" style={{ color: WHITE }}>{riskData.var.distribution.excess_kurtosis.toFixed(3)}</span>
                    </span>
                    <span className="text-[10px]" style={{ color: MUTED }}>
                      OBS <span className="ml-1" style={{ color: WHITE }}>{riskData.var.observations}</span>
                    </span>
                  </div>
                )}
              </div>

              {/* Stress Tests */}
              {riskData.stress_tests && riskData.stress_tests.length > 0 && (
                <div className="rounded-2xl overflow-hidden" style={{ border: `1px solid ${BORDER}` }}>
                  <CardHeader title="Historical Stress Tests" />
                  <div className="overflow-x-auto" style={{ background: NEAR_BLACK }}>
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
                            <td className="font-bold" style={{ color: WHITE }}>{st.name}</td>
                            <td style={{ color: MUTED }}>{st.label}</td>
                            <td className="text-right font-bold tabular-nums text-lg" style={{ color: st.portfolio_impact_pct < 0 ? RED : GREEN }}>
                              {st.portfolio_impact_pct >= 0 ? "+" : ""}{st.portfolio_impact_pct.toFixed(2)}%
                            </td>
                            <td className="text-right tabular-nums font-bold" style={{ color: GOLD }}>{st.worst_position}</td>
                            <td className="text-right tabular-nums" style={{ color: st.worst_position_pct < 0 ? RED : GREEN }}>
                              {st.worst_position_pct >= 0 ? "+" : ""}{st.worst_position_pct.toFixed(2)}%
                            </td>
                            <td className="text-right text-[10px]" style={{ color: MUTED }}>
                              {st.tickers_with_data}/{st.tickers_total} tickers
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}

              {/* Parametric Shock Scenarios */}
              {riskData.parametric_shocks && riskData.parametric_shocks.length > 0 && (
                <div className="rounded-2xl overflow-hidden" style={{ border: `1px solid ${BORDER}` }}>
                  <CardHeader title="Parametric Shock Scenarios" />
                  <div className="px-4 py-3" style={{ background: NEAR_BLACK, borderBottom: `1px solid ${BORDER}` }}>
                    <p className="text-[10px]" style={{ color: MUTED }}>
                      Sensitivity-based — applied via computed factor beta / rate-duration proxy to today&apos;s book, not historical replay.
                    </p>
                  </div>
                  <div className="overflow-x-auto" style={{ background: NEAR_BLACK }}>
                    <table>
                      <thead>
                        <tr>
                          <th>SCENARIO</th>
                          <th className="text-right">PORTFOLIO IMPACT</th>
                          <th className="text-right">BASIS</th>
                        </tr>
                      </thead>
                      <tbody>
                        {riskData.parametric_shocks.map(ps => (
                          <tr key={ps.name}>
                            <td className="font-bold" style={{ color: WHITE }}>{ps.name}</td>
                            <td className="text-right font-bold tabular-nums text-lg" style={{
                              color: ps.portfolio_impact_pct == null ? MUTED : ps.portfolio_impact_pct < 0 ? RED : GREEN
                            }}>
                              {ps.portfolio_impact_pct == null ? "—" :
                                `${ps.portfolio_impact_pct >= 0 ? "+" : ""}${ps.portfolio_impact_pct.toFixed(2)}%`}
                            </td>
                            <td className="text-right text-[10px]" style={{ color: MUTED }}>
                              {ps.methodology === "duration_proxy" &&
                                `${ps.fixed_income_weight_pct?.toFixed(1)}% FI @ ${ps.duration_proxy_years}yr duration`}
                              {ps.methodology === "market_beta" &&
                                (ps.market_beta != null ? `market beta ${ps.market_beta.toFixed(2)}` : ps.note)}
                              {ps.methodology === "baseline" && "reference"}
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
                <div className="rounded-2xl overflow-hidden" style={{ border: `1px solid ${BORDER}` }}>
                  <CardHeader title="Factor Exposure · OLS Regression (2Y)" />
                  <div className="p-4" style={{ background: NEAR_BLACK }}>
                    {riskData.factor_exposure.market_interp && (
                      <p className="text-[11px] mb-4 tracking-wide" style={{ color: WARNING }}>{riskData.factor_exposure.market_interp}</p>
                    )}
                    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                      <div>
                        <p className="text-[10px] mb-3 tracking-wide" style={{ color: MUTED }}>BETA TO FACTOR</p>
                        <ResponsiveContainer width="100%" height={180}>
                          <BarChart
                            data={Object.entries(riskData.factor_exposure.factors).map(([name, f]) => ({
                              name, beta: f.beta,
                            }))}
                            margin={{ left: -10, right: 10 }}
                          >
                            <CartesianGrid strokeDasharray="3 3" stroke={BORDER} />
                            <XAxis dataKey="name" tick={chartTick} />
                            <YAxis tick={chartTick} />
                            <Tooltip contentStyle={chartTooltipStyle} formatter={(v: unknown) => [Number(v).toFixed(3), "Beta"]} />
                            <Bar dataKey="beta" fill={GOLD} radius={[4, 4, 0, 0]} />
                          </BarChart>
                        </ResponsiveContainer>
                      </div>
                      <div>
                        <p className="text-[10px] mb-3 tracking-wide" style={{ color: MUTED }}>FACTOR DETAIL</p>
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
                                <td style={{ color: WHITE }}>{fname}</td>
                                <td className="font-bold" style={{ color: GOLD }}>{f.ticker}</td>
                                <td className="text-right tabular-nums font-bold" style={{ color: f.beta > 1.2 ? RED : f.beta < 0.5 ? GREEN : WHITE }}>
                                  {f.beta.toFixed(3)}
                                </td>
                                <td className="text-right tabular-nums" style={{ color: MUTED }}>{(f.r_squared * 100).toFixed(1)}%</td>
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
              <div className="rounded-2xl overflow-hidden" style={{ border: `1px solid ${BORDER}` }}>
                <CardHeader title="VaR Trend · 30-Day History" />
                {riskHistory.length < 2 ? (
                  <div className="p-6 text-center" style={{ background: NEAR_BLACK }}>
                    <p className="text-[11px] tracking-wide" style={{ color: MUTED }}>No trend data yet.</p>
                    <p className="text-[10px] mt-1" style={{ color: MUTED }}>Run the risk job daily to build history. At least 2 data points needed.</p>
                  </div>
                ) : (
                  <div className="p-4" style={{ background: NEAR_BLACK }}>
                    <p className="text-[10px] mb-3 tracking-wide" style={{ color: MUTED }}>
                      Loss % (absolute value) · dashed lines = alert thresholds (warning 2% / critical 3.5%)
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
                        <CartesianGrid strokeDasharray="3 3" stroke={BORDER} />
                        <XAxis dataKey="date" tick={chartTick} interval="preserveStartEnd" />
                        <YAxis tick={chartTick} tickFormatter={v => `${v.toFixed(1)}%`} width={44} />
                        <Tooltip contentStyle={chartTooltipStyle} formatter={(v: unknown) => [`${Number(v).toFixed(3)}%`, ""]} />
                        <Legend
                          wrapperStyle={{ fontSize: 9, color: MUTED, paddingTop: 8 }}
                          formatter={(value) => value === "var_95" ? "95% VaR (1-day)" : "99% VaR (1-day)"}
                        />
                        <ReferenceLine y={2}   stroke={WARNING} strokeDasharray="4 2" strokeWidth={1} label={{ value: "WARN", fill: WARNING, fontSize: 8 }} />
                        <ReferenceLine y={3.5} stroke={RED} strokeDasharray="4 2" strokeWidth={1} label={{ value: "CRIT", fill: RED, fontSize: 8 }} />
                        <Line type="monotone" dataKey="var_95" stroke={WARNING} strokeWidth={1.5} dot={false} connectNulls />
                        <Line type="monotone" dataKey="var_99" stroke={RED} strokeWidth={1.5} dot={false} connectNulls />
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
