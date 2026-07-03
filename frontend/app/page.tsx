"use client";
import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { getPortfolios, getMarketEvents, Portfolio, MarketEvent } from "@/lib/api";
import { useWebSocket, WsMessage } from "@/hooks/useWebSocket";
import LoadingSpinner from "@/components/LoadingSpinner";
import { ArrowRight, ChevronRight, X } from "lucide-react";

// ── Diverging orange scale (bright → dark) ────────────────────────────────────
const ORANGE_SCALE = ["#FFA040", "#FF8000", "#E05C00", "#CC4400", "#993300", "#7A2500", "#5C1800", "#3D1000"];

function orangeByRank(index: number, total: number): string {
  const i = Math.min(
    Math.round((index / Math.max(total - 1, 1)) * (ORANGE_SCALE.length - 1)),
    ORANGE_SCALE.length - 1
  );
  return ORANGE_SCALE[i];
}

// ── Formatters ────────────────────────────────────────────────────────────────
function fmt(n: number | null | undefined) {
  if (n == null) return "—";
  if (Math.abs(n) >= 1e9) return `$${(n / 1e9).toFixed(2)}B`;
  if (Math.abs(n) >= 1e6) return `$${(n / 1e6).toFixed(2)}M`;
  return `$${n.toLocaleString()}`;
}

function ImpactTag({ level }: { level: string | null }) {
  if (!level) return <span className="text-[#9a9a9a] text-[9px]">—</span>;
  const map: Record<string, string> = {
    high:   "text-[#FF4040] border-[#FF4040]/60",
    medium: "text-[#E05C00] border-[#E05C00]/60",
    low:    "text-[#00CC44] border-[#00CC44]/60",
  };
  return (
    <span className={`text-[9px] font-bold tracking-wider border px-1.5 py-0.5 ${map[level] ?? "text-[#9a9a9a] border-[#9a9a9a]/40"}`}>
      {level.toUpperCase()}
    </span>
  );
}

function PanelHeader({ label, sub, href }: { label: string; sub?: string; href?: string }) {
  return (
    <div
      className="flex items-center justify-between px-3 py-1.5"
      style={{ background: "linear-gradient(to right, #FF8000, #7A2500)" }}
    >
      <div className="flex items-center gap-2">
        <span className="text-white text-[10px] font-bold tracking-[0.18em] uppercase drop-shadow">{label}</span>
        {sub && <span className="text-white/50 text-[9px] tracking-wider">/ {sub}</span>}
      </div>
      {href && (
        <Link href={href} className="flex items-center gap-0.5 text-white/70 text-[9px] hover:text-white tracking-wider transition-colors font-bold">
          ALL <ChevronRight size={9} />
        </Link>
      )}
    </div>
  );
}

// ── Live value cell with flash animation ──────────────────────────────────────
interface LiveValue { value: number; changePct: number; flashKey: number }

function LiveValueCell({ live, base }: { live: LiveValue | undefined; base: number | null }) {
  const display    = live?.value ?? Number(base) ?? 0;
  const changePct  = live?.changePct ?? 0;
  const flashClass = live
    ? changePct >= 0 ? "flash-up" : "flash-down"
    : "";

  return (
    <div className="text-right">
      <span
        key={live?.flashKey}
        className={`text-[#f7f7f2] text-[11px] tabular-nums ${flashClass}`}
      >
        {fmt(display)}
      </span>
      {live && (
        <p className={`text-[9px] tabular-nums mt-0.5 ${changePct >= 0 ? "text-[#00CC44]" : "text-[#FF4040]"}`}>
          {changePct >= 0 ? "▲" : "▼"} {Math.abs(changePct).toFixed(3)}%
        </p>
      )}
    </div>
  );
}

// ── Event alert toast ─────────────────────────────────────────────────────────
interface EventAlert { id: number; title: string; impact: string | null }

function EventAlerts({ alerts, onDismiss }: {
  alerts: EventAlert[];
  onDismiss: (id: number) => void;
}) {
  if (!alerts.length) return null;
  return (
    <div className="space-y-1">
      {alerts.map(a => (
        <div
          key={a.id}
          className="alert-in flex items-center justify-between border border-[#E05C00]/40 bg-[#E05C00]/8 px-3 py-2"
        >
          <div className="flex items-center gap-2">
            <span className="text-[#FFA040] text-[9px] font-bold tracking-wider">NEW EVENT</span>
            <span className="text-[#f7f7f2] text-[10px] truncate max-w-xs">{a.title?.toUpperCase()}</span>
            {a.impact && <ImpactTag level={a.impact} />}
          </div>
          <button onClick={() => onDismiss(a.id)} className="text-[#555] hover:text-[#9a9a9a] ml-3">
            <X size={10} />
          </button>
        </div>
      ))}
    </div>
  );
}

// ── Main dashboard ────────────────────────────────────────────────────────────
export default function Dashboard() {
  const [portfolios, setPortfolios] = useState<Portfolio[]>([]);
  const [events, setEvents]         = useState<MarketEvent[]>([]);
  const [loading, setLoading]       = useState(true);
  const [now, setNow]               = useState(new Date());

  const [liveValues, setLiveValues]   = useState<Record<number, LiveValue>>({});
  const [eventAlerts, setEventAlerts] = useState<EventAlert[]>([]);
  const alertIdRef = useRef(0);

  // Apply gradient background + sidebar glass effect only on the dashboard page
  useEffect(() => {
    document.body.style.background = "transparent";
    const aside = document.querySelector("aside") as HTMLElement | null;
    if (aside) {
      aside.style.background = "rgba(6, 2, 0, 0.80)";
      aside.style.backdropFilter = "blur(18px)";
      aside.style.borderRight = "1px solid rgba(255,120,0,0.22)";
    }
    return () => {
      document.body.style.background = "";
      if (aside) {
        aside.style.background = "";
        aside.style.backdropFilter = "";
        aside.style.borderRight = "";
      }
    };
  }, []);

  const { connected } = useWebSocket((msg: WsMessage) => {
    if (msg.type === "portfolio_update" && msg.portfolio_id != null) {
      setLiveValues(prev => ({
        ...prev,
        [msg.portfolio_id!]: {
          value:      msg.total_value!,
          changePct:  msg.change_pct!,
          flashKey:   Date.now(),
        },
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
    Promise.all([getPortfolios(), getMarketEvents(10)])
      .then(([p, e]) => { setPortfolios(p); setEvents(e); })
      .finally(() => setLoading(false));

    const tick = setInterval(() => setNow(new Date()), 1_000);
    return () => clearInterval(tick);
  }, []);

  const totalAUM = portfolios.reduce((sum, p) => {
    const live = liveValues[p.portfolio_id];
    return sum + (live ? live.value : Number(p.total_value) || 0);
  }, 0);

  // sort strategies by count desc so rank 0 = most popular = brightest orange
  const strategyCounts = portfolios.reduce<Record<string, number>>((acc, p) => {
    if (p.strategy_type) acc[p.strategy_type] = (acc[p.strategy_type] ?? 0) + 1;
    return acc;
  }, {});
  const strategies = Object.entries(strategyCounts)
    .sort((a, b) => b[1] - a[1])
    .map(([s]) => s);

  if (loading) return <LoadingSpinner label="Initialising terminal..." />;

  const dateStr = now.toLocaleDateString("en-US", {
    weekday: "short", year: "numeric", month: "short", day: "numeric",
  }).toUpperCase();
  const timeStr = now.toLocaleTimeString("en-US", { hour12: false });

  return (
    <>
      {/* ── Layer 1: Full-viewport diverging gradient (fixed, behind everything) ── */}
      <div
        className="fixed inset-0"
        style={{
          zIndex: 1,
          background:
            "radial-gradient(ellipse at top left, #FFA040 0%, #FF8000 22%, #CC4400 45%, #7A2500 65%, #3D1000 82%, #050000 100%)",
        }}
      />

      {/* ── Layer 2: Black canvas — sits within main's p-5 gap (that gap = visible orange frame) ── */}
      <div
        className="relative bg-black"
        style={{ zIndex: 2, minHeight: "calc(100vh - 40px)" }}
      >
        <div className="max-w-7xl mx-auto space-y-3 font-mono p-5">

      {/* ── Top terminal bar ─────────────────────────────────────────────── */}
      <div className="flex items-center justify-between border border-[#2e2e2e] bg-[#0d0d0d] px-4 py-2">
        <div className="flex items-center gap-3">
          <span className="text-[11px] font-bold tracking-[0.2em]" style={{ color: "#FF8000" }}>FINSIGHT AI</span>
          <span className="text-[#3A3A3A]">│</span>
          <span className="text-[#9a9a9a] text-[9px] tracking-[0.12em]">PORTFOLIO INTELLIGENCE TERMINAL</span>
          <span className="text-[#3A3A3A]">│</span>
          <span className="text-[#9a9a9a] text-[9px] tracking-wider">v2.0</span>
        </div>
        <div className="flex items-center gap-4">
          <span className="text-[#9a9a9a] text-[10px] tabular-nums tracking-wider">{dateStr}</span>
          <span className="text-[#f7f7f2] text-[10px] tabular-nums font-bold tracking-wider">{timeStr}</span>
          <span className="text-[#3A3A3A]">│</span>
          <div className="flex items-center gap-1.5">
            <span className={`w-1.5 h-1.5 rounded-full ${connected ? "bg-[#00CC44] animate-pulse" : "bg-[#E05C00]"}`} />
            <span className={`text-[9px] font-bold tracking-[0.15em] ${connected ? "text-[#00CC44]" : "text-[#E05C00]"}`}>
              {connected ? "LIVE" : "RECONNECTING"}
            </span>
          </div>
        </div>
      </div>

      {/* ── Event alert toasts ───────────────────────────────────────────── */}
      <EventAlerts
        alerts={eventAlerts}
        onDismiss={id => setEventAlerts(prev => prev.filter(a => a.id !== id))}
      />

      {/* ── KPI strip ────────────────────────────────────────────────────── */}
      <div className="grid grid-cols-4 border border-[#2e2e2e]">
        {[
          { label: "TOTAL AUM",     value: fmt(totalAUM),                          sub: `${portfolios.length} PORTFOLIOS`,                          valueColor: "#00CC44" },
          { label: "STRATEGIES",    value: strategies.length,                       sub: strategies.slice(0, 2).join(" · ").toUpperCase() || "—",   valueColor: "#00CC44" },
          { label: "MARKET EVENTS", value: events.length,                           sub: "LAST 10 ALERTS",                                           valueColor: "#00CC44" },
          { label: "SYSTEM STATUS", value: connected ? "ONLINE" : "PARTIAL",       sub: "API · RAG · GPT-4o",                                       valueColor: connected ? "#00CC44" : "#E05C00" },
        ].map((kpi, i) => (
          <div key={i} className={`p-4 bg-[#0d0d0d] ${i < 3 ? "border-r border-[#2e2e2e]" : ""}`}>
            <p className="text-[9px] font-bold tracking-[0.15em] mb-2" style={{ color: "#FF8000" }}>{kpi.label}</p>
            <p className="text-2xl font-bold tabular-nums" style={{ color: kpi.valueColor }}>{kpi.value}</p>
            <p className="text-[#9a9a9a] text-[10px] mt-1 tracking-wider">{kpi.sub}</p>
          </div>
        ))}
      </div>

      {/* ── Main panels ──────────────────────────────────────────────────── */}
      <div className="grid grid-cols-2 gap-3">

        {/* Portfolios */}
        <div className="border border-[#2e2e2e]">
          <PanelHeader label="PORTFOLIOS" sub={`${portfolios.length} ACTIVE`} href="/portfolios" />
          <div className="grid px-3 py-1.5 bg-[#0d0d0d] border-b border-[#2e2e2e]"
               style={{ gridTemplateColumns: "36px 1fr 110px 50px" }}>
            {["ID", "NAME / STRATEGY", "VALUE", "Δ%"].map(h => (
              <span key={h} className="text-[9px] font-bold tracking-[0.12em] last:text-right" style={{ color: "#FF8000" }}>{h}</span>
            ))}
          </div>

          {portfolios.slice(0, 10).map(p => {
            const live = liveValues[p.portfolio_id];
            return (
              <Link
                key={p.portfolio_id}
                href={`/portfolios/${p.portfolio_id}`}
                className="grid px-3 py-2 border-b border-[#161616] hover:bg-[#1a0a00] transition-colors group"
                style={{ gridTemplateColumns: "36px 1fr 110px 50px" }}
              >
                <span className="text-[#9a9a9a] text-[9px] tabular-nums self-center">
                  {String(p.portfolio_id).padStart(3, "0")}
                </span>
                <div className="min-w-0">
                  <p className="text-[#f7f7f2] text-[11px] transition-colors truncate leading-tight group-hover:text-[#FFA040]">
                    {p.portfolio_name?.toUpperCase()}
                  </p>
                  <p className="text-[#9a9a9a] text-[9px] tracking-wider truncate">
                    {p.strategy_type?.toUpperCase() ?? "—"}
                  </p>
                </div>
                <span
                  key={live?.flashKey}
                  className={`text-[11px] tabular-nums self-center ${
                    live
                      ? live.changePct >= 0 ? "flash-up text-[#00CC44]" : "flash-down text-[#FF4040]"
                      : "text-[#f7f7f2]"
                  }`}
                >
                  {fmt(live?.value ?? Number(p.total_value))}
                </span>
                <span className={`text-[9px] tabular-nums self-center text-right ${
                  live
                    ? live.changePct >= 0 ? "text-[#00CC44]" : "text-[#FF4040]"
                    : "text-[#9a9a9a]"
                }`}>
                  {live
                    ? `${live.changePct >= 0 ? "▲" : "▼"} ${Math.abs(live.changePct).toFixed(2)}%`
                    : "—"}
                </span>
              </Link>
            );
          })}

          <div className="px-3 py-2 bg-[#0d0d0d] border-t border-[#2e2e2e] flex justify-end">
            <Link href="/portfolios" className="text-[9px] tracking-wider flex items-center gap-1 transition-colors opacity-70 hover:opacity-100"
                  style={{ color: "#CC4400" }}
                  onMouseEnter={e => (e.currentTarget.style.color = "#FFA040")}
                  onMouseLeave={e => (e.currentTarget.style.color = "#CC4400")}>
              VIEW ALL {portfolios.length} PORTFOLIOS <ArrowRight size={9} />
            </Link>
          </div>
        </div>

        {/* Market Events */}
        <div className="border border-[#2e2e2e]">
          <PanelHeader label="MARKET EVENTS" sub="RECENT ALERTS" href="/market-events" />
          <div className="grid px-3 py-1.5 bg-[#0d0d0d] border-b border-[#2e2e2e]"
               style={{ gridTemplateColumns: "76px 1fr 60px" }}>
            {["DATE", "EVENT / TYPE", "IMPACT"].map(h => (
              <span key={h} className="text-[9px] font-bold tracking-[0.12em]" style={{ color: "#FF8000" }}>{h}</span>
            ))}
          </div>

          {events.slice(0, 10).map(ev => (
            <Link
              key={ev.event_id}
              href={`/market-events/${ev.event_id}`}
              className="grid px-3 py-2 border-b border-[#161616] hover:bg-[#1a0a00] transition-colors group items-start"
              style={{ gridTemplateColumns: "76px 1fr 60px" }}
            >
              <span className="text-[#9a9a9a] text-[9px] tabular-nums pt-0.5">
                {ev.event_date?.slice(0, 10) ?? "—"}
              </span>
              <div className="min-w-0">
                <p className="text-[#f7f7f2] text-[11px] transition-colors truncate leading-tight group-hover:text-[#FFA040]">
                  {ev.event_title?.toUpperCase() ?? "UNTITLED"}
                </p>
                <p className="text-[#9a9a9a] text-[9px] tracking-wider truncate">
                  {ev.event_type?.toUpperCase() ?? "—"}
                </p>
              </div>
              <div className="pt-0.5">
                <ImpactTag level={ev.impact_level} />
              </div>
            </Link>
          ))}

          <div className="px-3 py-2 bg-[#0d0d0d] border-t border-[#2e2e2e] flex justify-end">
            <Link href="/market-events" className="text-[9px] tracking-wider flex items-center gap-1 transition-colors opacity-70 hover:opacity-100"
                  style={{ color: "#CC4400" }}
                  onMouseEnter={e => (e.currentTarget.style.color = "#FFA040")}
                  onMouseLeave={e => (e.currentTarget.style.color = "#CC4400")}>
              VIEW ALL EVENTS <ArrowRight size={9} />
            </Link>
          </div>
        </div>
      </div>

      {/* ── Strategy distribution ─────────────────────────────────────────── */}
      <div className="border border-[#2e2e2e]">
        <PanelHeader label="STRATEGY DISTRIBUTION" sub={`${strategies.length} ACTIVE`} />
        <div className="flex divide-x divide-[#2e2e2e] bg-[#0d0d0d]">
          {strategies.slice(0, 8).map((s, idx) => {
            const count = strategyCounts[s] ?? 0;
            const pct   = portfolios.length ? ((count / portfolios.length) * 100).toFixed(1) : "0.0";
            const barColor = orangeByRank(idx, Math.min(strategies.length, 8));
            return (
              <div key={s} className="flex-1 px-3 py-2.5 min-w-0">
                <p className="text-[8px] font-bold tracking-wider truncate uppercase" style={{ color: "#FFA040" }}>{s}</p>
                <p className="text-base font-bold tabular-nums mt-0.5" style={{ color: "#00CC44" }}>{count}</p>
                <div className="mt-1.5 h-1 bg-[#1a0a00] rounded-none">
                  <div className="h-full" style={{ width: `${pct}%`, backgroundColor: "#FFA040", opacity: 0.85 }} />
                </div>
                <p className="text-[#9a9a9a] text-[8px] mt-1 tabular-nums">{pct}%</p>
              </div>
            );
          })}
        </div>
      </div>

      {/* ── System status strip ──────────────────────────────────────────── */}
      <div className="flex items-center gap-3 border border-[#2e2e2e] border-t-0 px-3 py-1.5 bg-[#0d0d0d] text-[9px] tracking-wider">
        <span className="font-bold opacity-90" style={{ color: "#FF8000" }}>SYS</span>
        <span className="text-[#3A3A3A]">│</span>
        <span className="text-[#9a9a9a]">API localhost:8000</span>
        <span className="text-[#3A3A3A]">│</span>
        <span className="text-[#9a9a9a]">WS {connected ? "CONNECTED" : "RECONNECTING"}</span>
        <span className="text-[#3A3A3A]">│</span>
        <span className="text-[#9a9a9a]">DB SQL-SERVER</span>
        <span className="text-[#3A3A3A]">│</span>
        <span className="text-[#9a9a9a]">RAG CHROMADB</span>
        <span className="text-[#3A3A3A]">│</span>
        <span className="text-[#9a9a9a]">AI GPT-4o</span>
        <div className="ml-auto flex items-center gap-1.5">
          <span className={`w-1 h-1 rounded-full ${connected ? "bg-[#00CC44] animate-pulse" : "bg-[#E05C00]"}`} />
          <span className={`text-[9px] font-bold tracking-wider ${connected ? "text-[#00CC44]" : "text-[#E05C00]"}`}>
            {connected ? "ALL SYSTEMS OPERATIONAL" : "PARTIAL — WS RECONNECTING"}
          </span>
        </div>
      </div>

        </div>{/* end max-w-7xl */}
      </div>{/* end Layer 2: black canvas */}
    </>
  );
}
