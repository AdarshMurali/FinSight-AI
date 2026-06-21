"use client";
import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { getPortfolios, getMarketEvents, Portfolio, MarketEvent } from "@/lib/api";
import { useWebSocket, WsMessage } from "@/hooks/useWebSocket";
import LoadingSpinner from "@/components/LoadingSpinner";
import { ArrowRight, ChevronRight, X } from "lucide-react";

// ── Formatters ────────────────────────────────────────────────────────────────
function fmt(n: number | null | undefined) {
  if (n == null) return "—";
  if (Math.abs(n) >= 1e9) return `$${(n / 1e9).toFixed(2)}B`;
  if (Math.abs(n) >= 1e6) return `$${(n / 1e6).toFixed(2)}M`;
  return `$${n.toLocaleString()}`;
}

function ImpactTag({ level }: { level: string | null }) {
  if (!level) return <span className="text-[#888] text-[9px]">—</span>;
  const map: Record<string, string> = {
    high:   "text-[#FF4040] border-[#FF4040]/60",
    medium: "text-[#FFB300] border-[#FFB300]/60",
    low:    "text-[#00CC44] border-[#00CC44]/60",
  };
  return (
    <span className={`text-[9px] font-bold tracking-wider border px-1.5 py-0.5 ${map[level] ?? "text-[#AAA] border-[#AAA]/40"}`}>
      {level.toUpperCase()}
    </span>
  );
}

function PanelHeader({ label, sub, href }: { label: string; sub?: string; href?: string }) {
  return (
    <div className="flex items-center justify-between bg-[#F5821F] px-3 py-1.5">
      <div className="flex items-center gap-2">
        <span className="text-black text-[10px] font-bold tracking-[0.18em] uppercase">{label}</span>
        {sub && <span className="text-black/50 text-[9px] tracking-wider">/ {sub}</span>}
      </div>
      {href && (
        <Link href={href} className="flex items-center gap-0.5 text-black/70 text-[9px] hover:text-black tracking-wider transition-colors font-bold">
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
        key={live?.flashKey}        // re-mounts span to restart CSS animation
        className={`text-[#E0E0E0] text-[11px] tabular-nums ${flashClass}`}
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
          className="alert-in flex items-center justify-between border border-[#FFB300]/40 bg-[#FFB300]/8 px-3 py-2"
        >
          <div className="flex items-center gap-2">
            <span className="text-[#FFB300] text-[9px] font-bold tracking-wider">NEW EVENT</span>
            <span className="text-[#E0E0E0] text-[10px] truncate max-w-xs">{a.title?.toUpperCase()}</span>
            {a.impact && <ImpactTag level={a.impact} />}
          </div>
          <button onClick={() => onDismiss(a.id)} className="text-[#555] hover:text-[#AAA] ml-3">
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

  // live data state
  const [liveValues, setLiveValues]   = useState<Record<number, LiveValue>>({});
  const [eventAlerts, setEventAlerts] = useState<EventAlert[]>([]);
  const alertIdRef = useRef(0);

  // WebSocket
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
      // auto-dismiss after 8 s
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

  // Recalculate total AUM using live values where available
  const totalAUM = portfolios.reduce((sum, p) => {
    const live = liveValues[p.portfolio_id];
    return sum + (live ? live.value : Number(p.total_value) || 0);
  }, 0);

  const strategies = [...new Set(portfolios.map(p => p.strategy_type).filter(Boolean))];

  if (loading) return <LoadingSpinner label="Initialising terminal..." />;

  const dateStr = now.toLocaleDateString("en-US", {
    weekday: "short", year: "numeric", month: "short", day: "numeric",
  }).toUpperCase();
  const timeStr = now.toLocaleTimeString("en-US", { hour12: false });

  return (
    <div className="max-w-7xl mx-auto space-y-3 font-mono">

      {/* ── Top terminal bar ─────────────────────────────────────────────── */}
      <div className="flex items-center justify-between border border-[#2A2A2A] bg-[#0D0D0D] px-4 py-2">
        <div className="flex items-center gap-3">
          <span className="text-[#F5821F] text-[11px] font-bold tracking-[0.2em]">FINSIGHT AI</span>
          <span className="text-[#3A3A3A]">│</span>
          <span className="text-[#888] text-[9px] tracking-[0.12em]">PORTFOLIO INTELLIGENCE TERMINAL</span>
          <span className="text-[#3A3A3A]">│</span>
          <span className="text-[#777] text-[9px] tracking-wider">v2.0</span>
        </div>
        <div className="flex items-center gap-4">
          <span className="text-[#AAA] text-[10px] tabular-nums tracking-wider">{dateStr}</span>
          <span className="text-[#E0E0E0] text-[10px] tabular-nums font-bold tracking-wider">{timeStr}</span>
          <span className="text-[#3A3A3A]">│</span>
          {/* WebSocket connection status */}
          <div className="flex items-center gap-1.5">
            <span className={`w-1.5 h-1.5 rounded-full ${connected ? "bg-[#00CC44] animate-pulse" : "bg-[#FFB300]"}`} />
            <span className={`text-[9px] font-bold tracking-[0.15em] ${connected ? "text-[#00CC44]" : "text-[#FFB300]"}`}>
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
      <div className="grid grid-cols-4 border border-[#2A2A2A]">
        {[
          { label: "TOTAL AUM",      value: fmt(totalAUM),       sub: `${portfolios.length} PORTFOLIOS`,  valueColor: "text-[#F5821F]" },
          { label: "STRATEGIES",     value: strategies.length,   sub: strategies.slice(0,2).join(" · ").toUpperCase() || "—", valueColor: "text-[#E0E0E0]" },
          { label: "MARKET EVENTS",  value: events.length,       sub: "LAST 10 ALERTS",                   valueColor: "text-[#FFB300]" },
          { label: "SYSTEM STATUS",  value: connected ? "ONLINE" : "PARTIAL", sub: "API · RAG · GPT-4o", valueColor: connected ? "text-[#00CC44]" : "text-[#FFB300]" },
        ].map((kpi, i) => (
          <div key={i} className={`p-4 bg-[#0D0D0D] ${i < 3 ? "border-r border-[#2A2A2A]" : ""}`}>
            <p className="text-[#F5821F] text-[9px] font-bold tracking-[0.15em] mb-2">{kpi.label}</p>
            <p className={`text-2xl font-bold tabular-nums ${kpi.valueColor}`}>{kpi.value}</p>
            <p className="text-[#888] text-[10px] mt-1 tracking-wider">{kpi.sub}</p>
          </div>
        ))}
      </div>

      {/* ── Main panels ──────────────────────────────────────────────────── */}
      <div className="grid grid-cols-2 gap-3">

        {/* Portfolios */}
        <div className="border border-[#2A2A2A]">
          <PanelHeader label="PORTFOLIOS" sub={`${portfolios.length} ACTIVE`} href="/portfolios" />
          <div className="grid px-3 py-1.5 bg-[#0D0D0D] border-b border-[#2A2A2A]"
               style={{ gridTemplateColumns: "36px 1fr 110px 50px" }}>
            {["ID", "NAME / STRATEGY", "VALUE", "Δ%"].map(h => (
              <span key={h} className="text-[#F5821F] text-[9px] font-bold tracking-[0.12em] last:text-right">{h}</span>
            ))}
          </div>

          {portfolios.slice(0, 10).map(p => {
            const live = liveValues[p.portfolio_id];
            return (
              <Link
                key={p.portfolio_id}
                href={`/portfolios/${p.portfolio_id}`}
                className="grid px-3 py-2 border-b border-[#1A1A1A] hover:bg-[#1A1A1A] transition-colors group"
                style={{ gridTemplateColumns: "36px 1fr 110px 50px" }}
              >
                <span className="text-[#888] text-[9px] tabular-nums self-center">
                  {String(p.portfolio_id).padStart(3, "0")}
                </span>
                <div className="min-w-0">
                  <p className="text-[#E0E0E0] text-[11px] group-hover:text-[#F5821F] transition-colors truncate leading-tight">
                    {p.portfolio_name?.toUpperCase()}
                  </p>
                  <p className="text-[#AAA] text-[9px] tracking-wider truncate">
                    {p.strategy_type?.toUpperCase() ?? "—"}
                  </p>
                </div>
                {/* Live value with flash */}
                <span
                  key={live?.flashKey}
                  className={`text-[11px] tabular-nums self-center ${
                    live
                      ? live.changePct >= 0 ? "flash-up text-[#00CC44]" : "flash-down text-[#FF4040]"
                      : "text-[#E0E0E0]"
                  }`}
                >
                  {fmt(live?.value ?? Number(p.total_value))}
                </span>
                {/* Change % */}
                <span className={`text-[9px] tabular-nums self-center text-right ${
                  live
                    ? live.changePct >= 0 ? "text-[#00CC44]" : "text-[#FF4040]"
                    : "text-[#555]"
                }`}>
                  {live
                    ? `${live.changePct >= 0 ? "▲" : "▼"} ${Math.abs(live.changePct).toFixed(2)}%`
                    : "—"}
                </span>
              </Link>
            );
          })}

          <div className="px-3 py-2 bg-[#0D0D0D] border-t border-[#2A2A2A] flex justify-end">
            <Link href="/portfolios" className="text-[#F5821F] hover:text-[#FFB300] text-[9px] tracking-wider flex items-center gap-1 transition-colors opacity-70 hover:opacity-100">
              VIEW ALL {portfolios.length} PORTFOLIOS <ArrowRight size={9} />
            </Link>
          </div>
        </div>

        {/* Market Events */}
        <div className="border border-[#2A2A2A]">
          <PanelHeader label="MARKET EVENTS" sub="RECENT ALERTS" href="/market-events" />
          <div className="grid px-3 py-1.5 bg-[#0D0D0D] border-b border-[#2A2A2A]"
               style={{ gridTemplateColumns: "76px 1fr 60px" }}>
            {["DATE", "EVENT / TYPE", "IMPACT"].map(h => (
              <span key={h} className="text-[#F5821F] text-[9px] font-bold tracking-[0.12em]">{h}</span>
            ))}
          </div>

          {events.slice(0, 10).map(ev => (
            <Link
              key={ev.event_id}
              href={`/market-events/${ev.event_id}`}
              className="grid px-3 py-2 border-b border-[#1A1A1A] hover:bg-[#1A1A1A] transition-colors group items-start"
              style={{ gridTemplateColumns: "76px 1fr 60px" }}
            >
              <span className="text-[#AAA] text-[9px] tabular-nums pt-0.5">
                {ev.event_date?.slice(0, 10) ?? "—"}
              </span>
              <div className="min-w-0">
                <p className="text-[#E0E0E0] text-[11px] group-hover:text-[#F5821F] transition-colors truncate leading-tight">
                  {ev.event_title?.toUpperCase() ?? "UNTITLED"}
                </p>
                <p className="text-[#AAA] text-[9px] tracking-wider truncate">
                  {ev.event_type?.toUpperCase() ?? "—"}
                </p>
              </div>
              <div className="pt-0.5">
                <ImpactTag level={ev.impact_level} />
              </div>
            </Link>
          ))}

          <div className="px-3 py-2 bg-[#0D0D0D] border-t border-[#2A2A2A] flex justify-end">
            <Link href="/market-events" className="text-[#F5821F] hover:text-[#FFB300] text-[9px] tracking-wider flex items-center gap-1 transition-colors opacity-70 hover:opacity-100">
              VIEW ALL EVENTS <ArrowRight size={9} />
            </Link>
          </div>
        </div>
      </div>

      {/* ── Strategy distribution ─────────────────────────────────────────── */}
      <div className="border border-[#2A2A2A]">
        <PanelHeader label="STRATEGY DISTRIBUTION" sub={`${strategies.length} ACTIVE`} />
        <div className="flex divide-x divide-[#2A2A2A] bg-[#0D0D0D]">
          {strategies.slice(0, 8).map(s => {
            const count = portfolios.filter(p => p.strategy_type === s).length;
            const pct   = portfolios.length ? ((count / portfolios.length) * 100).toFixed(1) : "0.0";
            return (
              <div key={s} className="flex-1 px-3 py-2.5 min-w-0">
                <p className="text-[#F5821F] text-[8px] font-bold tracking-wider truncate uppercase">{s}</p>
                <p className="text-[#E0E0E0] text-base font-bold tabular-nums mt-0.5">{count}</p>
                <div className="mt-1.5 h-px bg-[#2A2A2A]">
                  <div className="h-full bg-[#F5821F]/70" style={{ width: `${pct}%` }} />
                </div>
                <p className="text-[#AAA] text-[8px] mt-1 tabular-nums">{pct}%</p>
              </div>
            );
          })}
        </div>
      </div>

      {/* ── System status strip ──────────────────────────────────────────── */}
      <div className="flex items-center gap-3 border border-[#2A2A2A] border-t-0 px-3 py-1.5 bg-[#0D0D0D] text-[9px] tracking-wider">
        <span className="text-[#F5821F] font-bold opacity-80">SYS</span>
        <span className="text-[#3A3A3A]">│</span>
        <span className="text-[#888]">API localhost:8000</span>
        <span className="text-[#3A3A3A]">│</span>
        <span className="text-[#888]">WS {connected ? `CONNECTED` : "RECONNECTING"}</span>
        <span className="text-[#3A3A3A]">│</span>
        <span className="text-[#888]">DB SQL-SERVER</span>
        <span className="text-[#3A3A3A]">│</span>
        <span className="text-[#888]">RAG CHROMADB</span>
        <span className="text-[#3A3A3A]">│</span>
        <span className="text-[#888]">AI GPT-4o</span>
        <div className="ml-auto flex items-center gap-1.5">
          <span className={`w-1 h-1 rounded-full ${connected ? "bg-[#00CC44] animate-pulse" : "bg-[#FFB300]"}`} />
          <span className={`text-[9px] font-bold tracking-wider ${connected ? "text-[#00CC44]" : "text-[#FFB300]"}`}>
            {connected ? "ALL SYSTEMS OPERATIONAL" : "PARTIAL — WS RECONNECTING"}
          </span>
        </div>
      </div>

    </div>
  );
}
