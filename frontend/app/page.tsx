"use client";
import { useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";
import { Manrope } from "next/font/google";
import {
  PieChart, Pie, Cell, Tooltip, ResponsiveContainer,
} from "recharts";
import {
  getPortfolios, getAlerts, markAlertRead, getSecuritiesCount,
  Portfolio, AlertItem,
} from "@/lib/api";
import { useWebSocket, WsMessage } from "@/hooks/useWebSocket";
import {
  ArrowUpRight, ArrowDownRight, ArrowRight, X, Sparkles, Wallet,
  LayoutGrid, Layers, TrendingUp,
} from "lucide-react";

// ── FinSight AI dashboard — Bloomberg Professional–inspired visual language.
// Re-themed around Bloomberg's own black→amber→gold gradient (sampled from
// professional.bloomberg.com's CSS: #010101 → #c47c10 → #fabd49) and a
// licensed-substitute font (Manrope, standing in for their proprietary
// Avenir Next Pro for Bloomberg). A preview of this design also lives at
// /home-bloomberg for reference.
const manrope = Manrope({ subsets: ["latin"], weight: ["400", "500", "600", "700", "800"] });

const NEAR_BLACK = "#0a0a0a";
const GOLD    = "#fabd49";
const WHITE   = "#FFFFFF";
const MUTED   = "#9C9CA5";
const GREEN   = "#00C853";
const RED     = "#e51e3c";
const WARNING = "#FFCC1D";
const BORDER  = "rgba(250,189,73,0.14)";

// On-brand gold ramp (bright → dark) instead of a rainbow categorical set —
// an ordinal/sequential scale reads cleaner here and stays colorblind-safe
// by construction (differentiated by lightness, not hue). Ranked by strategy
// popularity, so the most common strategy gets the brightest gold.
const GOLD_SCALE = ["#FFE7A8", "#FCCB6B", "#FABD49", "#E0A030", "#C47C10", "#9C6410", "#7A4E0E", "#5C3B0C"];
const OTHER_GRAY     = "#5a5b63";
const CHART_SURFACE = "#1a1a19";

function goldByRank(index: number, total: number): string {
  const i = Math.min(
    Math.round((index / Math.max(total - 1, 1)) * (GOLD_SCALE.length - 1)),
    GOLD_SCALE.length - 1
  );
  return GOLD_SCALE[i];
}

const CARD_SHADOW       = "0 1rem 2.8rem rgba(0,0,0,0.5)";
const CARD_SHADOW_HOVER = "0 1.6rem 4rem rgba(196,124,16,0.28)";

function fmt(n: number | null | undefined) {
  if (n == null) return "—";
  if (Math.abs(n) >= 1e9) return `$${(n / 1e9).toFixed(2)}B`;
  if (Math.abs(n) >= 1e6) return `$${(n / 1e6).toFixed(2)}M`;
  return `$${n.toLocaleString()}`;
}

function initials(name: string | null | undefined) {
  if (!name) return "?";
  const parts = name.trim().split(/\s+/);
  return ((parts[0]?.[0] ?? "") + (parts[1]?.[0] ?? "")).toUpperCase() || "?";
}

function ImpactTag({ level }: { level: string | null }) {
  if (!level) return <span className="text-[11px]" style={{ color: MUTED }}>—</span>;
  const map: Record<string, string> = { high: RED, medium: WARNING, low: GREEN };
  const c = map[level] ?? MUTED;
  return (
    <span className="text-[10px] font-bold tracking-wide px-2 py-0.5 rounded-full" style={{ color: c, background: `${c}1a` }}>
      {level.toUpperCase()}
    </span>
  );
}

// Circular outlined arrow button — Bloomberg's own CTA motif ("Need customer
// support? →") rather than a filled pill.
function ViewAllCircle({ href }: { href: string }) {
  const [hover, setHover] = useState(false);
  return (
    <Link
      href={href}
      className="flex items-center justify-center w-8 h-8 rounded-full shrink-0 transition-all duration-200"
      style={{ border: `1.5px solid ${hover ? GOLD : "rgba(255,255,255,0.35)"}`, background: hover ? "rgba(250,189,73,0.12)" : "transparent" }}
      onMouseEnter={() => setHover(true)}
      onMouseLeave={() => setHover(false)}
      title="View all"
    >
      <ArrowRight size={14} style={{ color: hover ? GOLD : WHITE }} />
    </Link>
  );
}

function Card({ title, sub, href, children, className = "" }: {
  title: string; sub?: string; href?: string; children: React.ReactNode; className?: string;
}) {
  const [hover, setHover] = useState(false);
  return (
    <div
      className={`rounded-2xl overflow-hidden transition-all duration-300 ${className}`}
      style={{
        background: NEAR_BLACK,
        border: `1px solid ${BORDER}`,
        boxShadow: hover ? CARD_SHADOW_HOVER : CARD_SHADOW,
        transform: hover ? "translateY(-3px)" : "none",
      }}
      onMouseEnter={() => setHover(true)}
      onMouseLeave={() => setHover(false)}
    >
      <div className="flex items-center justify-between px-5 pt-4 pb-3">
        <div>
          <h2 className="text-[13px] font-bold tracking-wide text-white">{title}</h2>
          {sub && <p className="text-[11px] mt-0.5" style={{ color: MUTED }}>{sub}</p>}
        </div>
        {href && <ViewAllCircle href={href} />}
      </div>
      {children}
    </div>
  );
}

interface LiveValue { value: number; changePct: number; flashKey: number }
interface EventAlert { id: number; title: string; impact: string | null }

function EventAlerts({ alerts, onDismiss }: { alerts: EventAlert[]; onDismiss: (id: number) => void }) {
  if (!alerts.length) return null;
  return (
    <div className="space-y-1.5">
      {alerts.map(a => (
        <div key={a.id} className="alert-in flex items-center justify-between px-4 py-2.5 rounded-xl" style={{ background: NEAR_BLACK, border: `1px solid ${BORDER}`, boxShadow: CARD_SHADOW }}>
          <div className="flex items-center gap-2.5">
            <span className="text-[10px] font-bold tracking-wide px-2 py-0.5 rounded-full text-black" style={{ background: GOLD }}>
              NEW EVENT
            </span>
            <span className="text-[12px] truncate max-w-md text-white">{a.title}</span>
            {a.impact && <ImpactTag level={a.impact} />}
          </div>
          <button onClick={() => onDismiss(a.id)} className="ml-3" style={{ color: MUTED }}>
            <X size={13} />
          </button>
        </div>
      ))}
    </div>
  );
}

function AiAlertTicker({ alerts, onDismiss }: { alerts: AlertItem[]; onDismiss: (id: number) => void }) {
  if (!alerts.length) return null;
  const totalChars = alerts.reduce((sum, a) => sum + a.title.length + a.message.length, 0);
  const duration = Math.max(totalChars / 9, 45);

  return (
    <div className="ticker-wrap flex items-stretch overflow-hidden rounded-full" style={{ background: NEAR_BLACK, border: `1px solid ${BORDER}` }}>
      <div className="flex items-center gap-2 pl-5 pr-4 shrink-0">
        <Sparkles size={13} style={{ color: GOLD }} />
        <span className="text-[10px] font-bold tracking-[0.12em] whitespace-nowrap" style={{ color: GOLD }}>AI INSIGHTS</span>
      </div>
      <div className="relative flex-1 overflow-hidden">
        <div className="ticker-track flex items-center gap-10 py-2.5 px-4" style={{ animationDuration: `${duration}s` }}>
          {[...alerts, ...alerts].map((a, i) => (
            <div key={`${a.alert_id}-${i}`} className="flex items-center gap-2 shrink-0">
              <span style={{ color: GREEN }}>●</span>
              {a.portfolio_id != null ? (
                <Link href={`/portfolios/${a.portfolio_id}`} onClick={() => onDismiss(a.alert_id)} className="text-[12px] whitespace-nowrap text-white">
                  {a.portfolio_name && <span style={{ color: GOLD }}>[{a.portfolio_name}] </span>}
                  <span className="font-semibold">{a.title}</span>
                  <span style={{ color: MUTED }}> — {a.message}</span>
                </Link>
              ) : (
                <span className="text-[12px] whitespace-nowrap text-white">
                  <span className="font-semibold">{a.title}</span>
                  <span style={{ color: MUTED }}> — {a.message}</span>
                </span>
              )}
              <button onClick={() => onDismiss(a.alert_id)} className="shrink-0" style={{ color: MUTED }} title="Mark as read">
                <X size={12} />
              </button>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function ChartTooltip({ active, payload }: { active?: boolean; payload?: { name: string; value: number; payload: { pct: string } }[] }) {
  if (!active || !payload?.length) return null;
  const p = payload[0];
  return (
    <div className="rounded-lg px-3 py-2 text-[11px]" style={{ background: CHART_SURFACE, border: `1px solid ${BORDER}`, color: WHITE, boxShadow: CARD_SHADOW_HOVER }}>
      <p className="font-semibold">{p.name}</p>
      <p style={{ color: MUTED }}>{p.value} portfolio{p.value === 1 ? "" : "s"} · {p.payload.pct}%</p>
    </div>
  );
}

export default function Dashboard() {
  const [portfolios, setPortfolios] = useState<Portfolio[]>([]);
  const [loading, setLoading]       = useState(true);
  const [now, setNow]               = useState(new Date());
  const [securitiesCount, setSecuritiesCount] = useState(0);

  const [liveValues, setLiveValues]   = useState<Record<number, LiveValue>>({});
  const [eventAlerts, setEventAlerts] = useState<EventAlert[]>([]);
  const [aiAlerts, setAiAlerts]       = useState<AlertItem[]>([]);
  const alertIdRef = useRef(0);

  const handleDismissAiAlert = (alertId: number) => {
    setAiAlerts(prev => prev.filter(a => a.alert_id !== alertId));
    markAlertRead(alertId).catch(() => {});
  };

  const { connected } = useWebSocket((msg: WsMessage) => {
    if (msg.type === "portfolio_update" && msg.portfolio_id != null) {
      setLiveValues(prev => ({
        ...prev,
        [msg.portfolio_id!]: { value: msg.total_value!, changePct: msg.change_pct!, flashKey: Date.now() },
      }));
    }
    if (msg.type === "market_event" && msg.data) {
      const d = msg.data as Record<string, unknown>;
      const title  = (d.headline ?? d.title ?? d.summary ?? "New market event") as string;
      const impact = (d.impact_level ?? null) as string | null;
      const id = ++alertIdRef.current;
      setEventAlerts(prev => [...prev.slice(-4), { id, title, impact }]);
      setTimeout(() => setEventAlerts(prev => prev.filter(a => a.id !== id)), 8_000);
    }
  });

  useEffect(() => {
    getPortfolios()
      .then(setPortfolios)
      .finally(() => setLoading(false));
    const tick = setInterval(() => setNow(new Date()), 1_000);
    return () => clearInterval(tick);
  }, []);

  useEffect(() => {
    const fetchAiAlerts = () => {
      getAlerts({ unread_only: true, limit: 50 })
        .then(all => setAiAlerts(all.filter(a => a.alert_type === "ai")))
        .catch(() => {});
    };
    fetchAiAlerts();
    const id = setInterval(fetchAiAlerts, 60_000);
    return () => clearInterval(id);
  }, []);

  useEffect(() => {
    const fetchSecuritiesCount = () => {
      getSecuritiesCount()
        .then(r => setSecuritiesCount(r.distinct_securities))
        .catch(() => {});
    };
    fetchSecuritiesCount();
    const id = setInterval(fetchSecuritiesCount, 60_000);
    return () => clearInterval(id);
  }, []);

  const baseAUM = portfolios.reduce((sum, p) => sum + (Number(p.total_value) || 0), 0);
  const totalAUM = portfolios.reduce((sum, p) => {
    const live = liveValues[p.portfolio_id];
    return sum + (live ? live.value : Number(p.total_value) || 0);
  }, 0);
  const sessionChangePct = baseAUM ? ((totalAUM - baseAUM) / baseAUM) * 100 : 0;

  const strategyCounts = portfolios.reduce<Record<string, number>>((acc, p) => {
    if (p.strategy_type) acc[p.strategy_type] = (acc[p.strategy_type] ?? 0) + 1;
    return acc;
  }, {});
  const strategies = Object.entries(strategyCounts).sort((a, b) => b[1] - a[1]).map(([s]) => s);

  const pieData = useMemo(() => {
    const TOP_N = 8;
    const top = strategies.slice(0, TOP_N).map((s, i) => ({
      name: s,
      value: strategyCounts[s] ?? 0,
      pct: portfolios.length ? (((strategyCounts[s] ?? 0) / portfolios.length) * 100).toFixed(1) : "0.0",
      color: goldByRank(i, Math.min(strategies.length, TOP_N)),
    }));
    const otherCount = strategies.slice(TOP_N).reduce((s, name) => s + (strategyCounts[name] ?? 0), 0);
    if (otherCount > 0) {
      top.push({ name: "OTHER", value: otherCount, pct: ((otherCount / portfolios.length) * 100).toFixed(1), color: OTHER_GRAY });
    }
    return top;
  }, [strategies, strategyCounts, portfolios.length]);

  if (loading) {
    return (
      <div className={`min-h-screen flex items-center justify-center ${manrope.className}`}>
        <div className="flex items-center gap-3 text-[12px] tracking-wide text-white">
          <span className="w-3.5 h-3.5 rounded-full border-2 animate-spin" style={{ borderColor: "rgba(250,189,73,0.25)", borderTopColor: GOLD }} />
          Loading your portfolios…
        </div>
      </div>
    );
  }

  const dateStr = now.toLocaleDateString("en-US", { weekday: "long", month: "long", day: "numeric" });
  const timeStr = now.toLocaleTimeString("en-US", { hour: "2-digit", minute: "2-digit", second: "2-digit" });

  return (
    <div className={manrope.className}>
      <div className="relative max-w-7xl mx-auto space-y-4">

        {/* ── Header ────────────────────────────────────────────────────────── */}
        <div className="flex items-start justify-between flex-wrap gap-4">
          <div className="max-w-xl">
            <h1 className="text-[26px] sm:text-[28px] font-extrabold leading-tight tracking-tight">
              <span className="text-white">Real-Time Portfolio </span>
              <span style={{ color: GOLD }}>Intelligence</span>
            </h1>
            <p className="text-[16px] mt-2 leading-relaxed" style={{ color: MUTED }}>
              Monitor risk, track performance, and act on AI-driven insights — all in real time,
              built for professional fund managers.
            </p>
          </div>
          <div className="flex flex-col items-end gap-2">
            <div className="flex items-center gap-2 px-3 py-1.5 rounded-full" style={{ background: NEAR_BLACK, border: `1px solid ${BORDER}` }}>
              <span className="w-1.5 h-1.5 rounded-full" style={{ background: connected ? GREEN : WARNING }} />
              <span className="text-[11px] font-semibold" style={{ color: connected ? GREEN : WARNING }}>
                {connected ? "Live" : "Reconnecting"}
              </span>
            </div>
            <p className="text-[11px]" style={{ color: MUTED }}>{dateStr} · {timeStr}</p>
          </div>
        </div>

        {/* ── AI insights ticker ───────────────────────────────────────────── */}
        <AiAlertTicker alerts={aiAlerts} onDismiss={handleDismissAiAlert} />

        {/* ── Event alert toasts ───────────────────────────────────────────── */}
        <EventAlerts alerts={eventAlerts} onDismiss={id => setEventAlerts(prev => prev.filter(a => a.id !== id))} />

        {/* ── KPI row ──────────────────────────────────────────────────────── */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          {[
            { label: "Total AUM", icon: Wallet, value: fmt(totalAUM), delta: `${sessionChangePct >= 0 ? "+" : ""}${sessionChangePct.toFixed(2)}% today`, deltaGood: sessionChangePct >= 0 },
            { label: "Active Portfolios", icon: LayoutGrid, value: String(portfolios.length), delta: `${strategies.length} strategies`, neutral: true },
            { label: "Securities Held", icon: Layers, value: String(securitiesCount), delta: `across ${portfolios.length} portfolios`, neutral: true },
          ].map((kpi, i) => (
            <KpiTile key={i} {...kpi} />
          ))}
        </div>

        {/* ── Main grid ────────────────────────────────────────────────────── */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
          <div className="lg:col-span-2">
            <Card title="Top Portfolios" sub={`${portfolios.length} active`} href="/portfolios">
              <div className="px-2 pb-2">
                {portfolios.slice(0, 8).map(p => {
                  const live = liveValues[p.portfolio_id];
                  const value = live?.value ?? (Number(p.total_value) || 0);
                  const changePct = live?.changePct ?? 0;
                  const flashClass = live ? (changePct >= 0 ? "flash-up" : "flash-down") : "";
                  return (
                    <PortfolioRow key={p.portfolio_id} p={p} value={value} changePct={changePct} live={!!live} flashClass={flashClass} flashKey={live?.flashKey} />
                  );
                })}
              </div>
            </Card>
          </div>

          <Card title="Allocation" sub="by strategy">
            <div className="px-5 pb-5">
              <div className="relative h-[180px]">
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie
                      data={pieData} dataKey="value" nameKey="name"
                      innerRadius={55} outerRadius={78}
                      paddingAngle={pieData.length > 1 ? 2 : 0}
                      stroke={NEAR_BLACK} strokeWidth={2}
                    >
                      {pieData.map((d, i) => <Cell key={i} fill={d.color} />)}
                    </Pie>
                    <Tooltip content={<ChartTooltip />} />
                  </PieChart>
                </ResponsiveContainer>
                <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
                  <p className="text-[22px] font-extrabold text-white">{portfolios.length}</p>
                  <p className="text-[10px] tracking-wide" style={{ color: MUTED }}>PORTFOLIOS</p>
                </div>
              </div>
              <div className="mt-4 space-y-1.5">
                {pieData.slice(0, 6).map(d => (
                  <div key={d.name} className="flex items-center gap-2 text-[11px]">
                    <span className="w-2 h-2 rounded-full shrink-0" style={{ background: d.color }} />
                    <span className="truncate flex-1 text-white">{d.name}</span>
                    <span className="tabular-nums" style={{ color: MUTED }}>{d.pct}%</span>
                  </div>
                ))}
              </div>
            </div>
          </Card>
        </div>

        {/* ── Footer status ────────────────────────────────────────────────── */}
        <div className="flex items-center gap-4 flex-wrap px-1 py-3 text-[11px]" style={{ color: MUTED }}>
          <span className="flex items-center">
            <TrendingUp size={12} style={{ color: GOLD }} />
          </span>
          <span>·</span>
          <span>API {(process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000").replace(/^https?:\/\//, "")}</span>
          <span>·</span>
          <span>ChromaDB RAG</span>
          <span>·</span>
          <span>GPT-4o</span>
          <span className="ml-auto flex items-center gap-1.5">
            <span className="w-1.5 h-1.5 rounded-full" style={{ background: connected ? GREEN : WARNING }} />
            {connected ? "All systems operational" : "Reconnecting to live feed"}
          </span>
        </div>

      </div>
    </div>
  );
}

// ── KPI tile — near-black card, gold icon chip, amber glow intensifying on hover ──
function KpiTile({ label, icon: Icon, value, delta, deltaGood, neutral }: {
  label: string; icon: React.ComponentType<{ size?: number; style?: React.CSSProperties }>;
  value: string; delta: string; deltaGood?: boolean; neutral?: boolean;
}) {
  const [hover, setHover] = useState(false);
  return (
    <div
      className="p-5 rounded-2xl transition-all duration-300"
      style={{
        background: NEAR_BLACK, border: `1px solid ${BORDER}`,
        boxShadow: hover ? CARD_SHADOW_HOVER : CARD_SHADOW,
        transform: hover ? "translateY(-4px)" : "none",
      }}
      onMouseEnter={() => setHover(true)}
      onMouseLeave={() => setHover(false)}
    >
      <div className="flex items-center justify-between mb-3">
        <span className="text-[11px] font-semibold tracking-wide" style={{ color: MUTED }}>{label}</span>
        <div className="p-1.5 rounded-lg" style={{ background: "rgba(250,189,73,0.12)" }}>
          <Icon size={13} style={{ color: GOLD }} />
        </div>
      </div>
      <p className="text-[26px] font-extrabold tabular-nums leading-none text-white">{value}</p>
      <p className="text-[11px] mt-2 flex items-center gap-1" style={{ color: neutral ? MUTED : deltaGood ? GREEN : RED }}>
        {!neutral && (deltaGood ? <ArrowUpRight size={11} /> : <ArrowDownRight size={11} />)}
        {delta}
      </p>
    </div>
  );
}

// ── Portfolio row — gold-tinted hover wash + gold hover text ("hover = selection") ──
function PortfolioRow({ p, value, changePct, live, flashClass, flashKey }: {
  p: Portfolio; value: number; changePct: number; live: boolean; flashClass: string; flashKey?: number;
}) {
  const [hover, setHover] = useState(false);
  return (
    <Link
      href={`/portfolios/${p.portfolio_id}`}
      className="flex items-center gap-3 px-3 py-2.5 rounded-xl transition-colors"
      style={{ background: hover ? "rgba(250,189,73,0.07)" : "transparent" }}
      onMouseEnter={() => setHover(true)}
      onMouseLeave={() => setHover(false)}
    >
      <div className="w-8 h-8 rounded-lg flex items-center justify-center text-[10px] font-bold shrink-0" style={{ background: "rgba(250,189,73,0.12)", color: GOLD }}>
        {initials(p.portfolio_name)}
      </div>
      <div className="min-w-0 flex-1">
        <p className="text-[13px] font-semibold truncate transition-colors" style={{ color: hover ? GOLD : WHITE }}>
          {p.portfolio_name}
        </p>
        <p className="text-[11px] truncate" style={{ color: MUTED }}>{p.strategy_type ?? "Unclassified"}</p>
      </div>
      <div className="text-right shrink-0">
        <p key={flashKey} className={`text-[13px] font-bold tabular-nums text-white ${flashClass}`}>
          {fmt(value)}
        </p>
        <p className="text-[11px] tabular-nums flex items-center justify-end gap-0.5" style={{ color: live ? (changePct >= 0 ? GREEN : RED) : MUTED }}>
          {live ? (<>{changePct >= 0 ? <ArrowUpRight size={10} /> : <ArrowDownRight size={10} />}{Math.abs(changePct).toFixed(2)}%</>) : "—"}
        </p>
      </div>
    </Link>
  );
}
