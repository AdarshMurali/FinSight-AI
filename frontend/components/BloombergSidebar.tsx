"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { Manrope } from "next/font/google";
import { LayoutDashboard, BarChart3, Sparkles, Radio, TrendingUp, MessageSquare, Bell, X, Check, CheckCheck, LogOut } from "lucide-react";
import { getAlerts, getUnreadCount, markAlertRead, markAllAlertsRead, AlertItem } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";

// ── Bloomberg Professional–inspired variant (see app/home-bloomberg/page.tsx).
// Font sizes match HdfcSidebar.tsx (the current /home-hdfc, not the v1 snapshot)
// per request; nav is pushed down from the logo block for more breathing room.
const manrope = Manrope({ subsets: ["latin"], weight: ["400", "500", "600", "700", "800"] });

const GOLD    = "#fabd49";
const AMBER   = "#c47c10";
const GREEN   = "#00C853";
const RED     = "#e51e3c";
const WARNING = "#FFCC1D";
const WHITE   = "#FFFFFF";
const MUTED   = "#9C9CA5";
const GLASS       = "rgba(250,189,73,0.10)";
const GLASS_HOVER = "rgba(250,189,73,0.16)";
// alert panel floats as a near-black card with a gold hairline, matching the variant
const PANEL_BG     = "#0a0a0a";
const PANEL_BORDER = "rgba(250,189,73,0.18)";
const CARD_MUTED   = "#9C9CA5";
const CARD_SHADOW  = "0 1.2rem 3.2rem rgba(0,0,0,0.55)";

const nav = [
  { href: "/",              label: "Dashboard",   icon: LayoutDashboard },
  { href: "/portfolios",    label: "Portfolios",  icon: BarChart3 },
  { href: "/ai-insights",   label: "AI Insights", icon: Sparkles },
  { href: "/chat",          label: "AI Chat",     icon: MessageSquare },
  { href: "/market-events", label: "Mkt Events",  icon: Radio },
];

const SEVERITY_STYLE: Record<string, { dot: string; label: string }> = {
  critical: { dot: RED,     label: "CRITICAL" },
  warning:  { dot: WARNING, label: "WARNING"  },
  info:     { dot: GREEN,   label: "INFO"     },
};

function initials(name: string | null | undefined) {
  if (!name) return "?";
  const parts = name.trim().split(/\s+/);
  return ((parts[0]?.[0] ?? "") + (parts[1]?.[0] ?? "")).toUpperCase() || "?";
}

function timeAgo(iso: string) {
  const diff = Date.now() - new Date(iso).getTime();
  const m = Math.floor(diff / 60000);
  if (m < 60)   return `${m}m ago`;
  const h = Math.floor(m / 60);
  if (h < 24)   return `${h}h ago`;
  return `${Math.floor(h / 24)}d ago`;
}

export default function BloombergSidebar() {
  const path = usePathname();
  const { user, logout } = useAuth();
  const [panelOpen,   setPanelOpen]   = useState(false);
  const [alerts,      setAlerts]      = useState<AlertItem[]>([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const panelRef = useRef<HTMLDivElement>(null);

  const fetchAlerts = async () => {
    try {
      const [data, uc] = await Promise.all([getAlerts({ limit: 30, unread_only: true }), getUnreadCount()]);
      setAlerts(data);
      setUnreadCount(uc.count);
    } catch { /* silent */ }
  };

  useEffect(() => {
    fetchAlerts();
    const id = setInterval(fetchAlerts, 60_000);
    return () => clearInterval(id);
  }, []);

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (panelRef.current && !panelRef.current.contains(e.target as Node)) {
        setPanelOpen(false);
      }
    };
    if (panelOpen) document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, [panelOpen]);

  const handleMarkRead = async (id: number) => {
    await markAlertRead(id);
    setAlerts(prev => prev.filter(a => a.alert_id !== id));
    setUnreadCount(c => Math.max(0, c - 1));
  };

  const handleMarkAll = async () => {
    await markAllAlertsRead();
    setAlerts([]);
    setUnreadCount(0);
  };

  return (
    <>
      <aside className={`fixed top-0 left-0 h-screen w-64 flex flex-col z-50 ${manrope.className}`}>
        {/* Logo */}
        <div className="px-5 pt-5 pb-4" style={{ borderBottom: "1px solid rgba(250,189,73,0.15)" }}>
          <div className="flex items-center gap-2">
            <div className="w-9 h-9 rounded-lg flex items-center justify-center shrink-0" style={{ background: GOLD }}>
              <TrendingUp size={18} className="text-black" />
            </div>
            <span className="font-extrabold text-[24px] tracking-tight whitespace-nowrap">
              <span className="text-white">FinSight</span> <span style={{ color: GOLD }}>AI</span>
            </span>
          </div>
          <p className="text-[12px] tracking-wide mt-1.5 pl-11" style={{ color: MUTED }}>
            Portfolio Intelligence
          </p>
        </div>

        {/* Navigation — pushed down from the logo block for more breathing room */}
        <nav className="flex-1 pt-16 pb-3 px-2.5 space-y-1">
          {nav.map(({ href, label, icon: Icon }) => {
            const active = path === href || (href !== "/" && path.startsWith(href));
            return (
              <Link
                key={href}
                href={href}
                className="flex items-center gap-3 px-3.5 py-3 rounded-lg text-[15px] font-medium transition-colors duration-150 relative"
                style={{ color: WHITE, background: active ? GLASS : "transparent" }}
                onMouseEnter={e => { if (!active) e.currentTarget.style.background = GLASS; }}
                onMouseLeave={e => { if (!active) e.currentTarget.style.background = "transparent"; }}
              >
                {active && (
                  <span className="absolute left-0 top-1/2 -translate-y-1/2 w-[3px] h-4 rounded-full" style={{ background: GOLD }} />
                )}
                <Icon size={17} style={{ color: active ? GOLD : WHITE, opacity: active ? 1 : 0.85 }} />
                {label}
              </Link>
            );
          })}
        </nav>

        {/* Alerts bell */}
        <div className="px-2.5 pb-2">
          <button
            onClick={() => { setPanelOpen(o => !o); if (!panelOpen) fetchAlerts(); }}
            className="relative flex items-center gap-3 w-full text-left px-3.5 py-3 rounded-lg transition-colors duration-150"
            style={{ background: panelOpen ? GLASS : "transparent", color: WHITE }}
            onMouseEnter={e => (e.currentTarget.style.background = GLASS_HOVER)}
            onMouseLeave={e => (e.currentTarget.style.background = panelOpen ? GLASS : "transparent")}
          >
            <div className="relative shrink-0">
              <Bell size={17} style={{ color: unreadCount > 0 ? WARNING : MUTED }} />
              {unreadCount > 0 && (
                <span
                  className="absolute -top-1.5 -right-1.5 flex items-center justify-center rounded-full text-[9px] font-bold"
                  style={{ background: RED, color: "#fff", minWidth: 15, height: 15, padding: "0 3px" }}
                >
                  {unreadCount > 99 ? "99+" : unreadCount}
                </span>
              )}
            </div>
            <span className="text-[15px] font-medium">
              Alerts{unreadCount > 0 ? ` (${unreadCount})` : ""}
            </span>
          </button>
        </div>

        {/* System status */}
        <div className="px-5 py-3.5 space-y-2.5" style={{ borderTop: "1px solid rgba(250,189,73,0.15)" }}>
          <div className="flex items-center gap-2">
            <span className="w-1.5 h-1.5 rounded-full shrink-0" style={{ background: GREEN }} />
            <span className="text-[12.5px] font-semibold tracking-wide" style={{ color: GREEN }}>LIVE</span>
            <span className="text-[12px] ml-auto truncate" style={{ color: MUTED }}>
              {(process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000").replace(/^https?:\/\//, "")}
            </span>
          </div>
          <div className="flex justify-between">
            <span className="text-[12.5px]" style={{ color: MUTED }}>RAG</span>
            <span className="text-[12.5px] text-white">ChromaDB</span>
          </div>
          <div className="flex justify-between">
            <span className="text-[12.5px]" style={{ color: MUTED }}>AI</span>
            <span className="text-[12.5px] text-white">GPT-4o</span>
          </div>
        </div>

        {/* Logged-in user + logout */}
        {user && (
          <div className="px-4 py-4 flex items-center justify-between gap-2" style={{ borderTop: "1px solid rgba(250,189,73,0.15)" }}>
            <div className="flex items-center gap-2.5 min-w-0">
              <div className="w-8 h-8 rounded-full flex items-center justify-center text-[11px] font-bold shrink-0 text-black" style={{ background: GOLD }}>
                {initials(user.full_name)}
              </div>
              <div className="min-w-0">
                <p className="text-[14px] font-semibold truncate text-white">{user.full_name}</p>
                <p className="text-[11.5px] tracking-wide" style={{ color: MUTED }}>
                  {user.role === "admin" ? "Admin" : "Fund Manager"}
                </p>
              </div>
            </div>
            <button
              onClick={logout}
              title="Log out"
              className="shrink-0 p-1.5 rounded-lg transition-colors"
              style={{ color: MUTED }}
              onMouseEnter={e => { e.currentTarget.style.color = "#fff"; e.currentTarget.style.background = "rgba(229,30,60,0.35)"; }}
              onMouseLeave={e => { e.currentTarget.style.color = MUTED; e.currentTarget.style.background = "transparent"; }}
            >
              <LogOut size={14} />
            </button>
          </div>
        )}
      </aside>

      {/* Alert slide-out panel — near-black card with a gold hairline, matching the variant */}
      {panelOpen && (
        <div
          ref={panelRef}
          className={`fixed top-0 left-64 h-screen w-80 z-40 flex flex-col overflow-hidden ${manrope.className}`}
          style={{ background: PANEL_BG, borderRight: `1px solid ${PANEL_BORDER}`, boxShadow: CARD_SHADOW }}
        >
          <div className="flex items-center justify-between px-4 py-3.5 shrink-0" style={{ borderBottom: `1px solid ${PANEL_BORDER}` }}>
            <div className="flex items-center gap-2">
              <Bell size={13} style={{ color: GOLD }} />
              <span className="text-[13px] font-bold text-white">Alerts</span>
              {unreadCount > 0 && (
                <span className="text-[10px] font-bold px-1.5 py-0.5 rounded-full text-white" style={{ background: RED }}>
                  {unreadCount}
                </span>
              )}
            </div>
            <div className="flex items-center gap-3">
              {unreadCount > 0 && (
                <button onClick={handleMarkAll} title="Mark all read" style={{ color: CARD_MUTED }}>
                  <CheckCheck size={14} />
                </button>
              )}
              <button onClick={() => setPanelOpen(false)} style={{ color: CARD_MUTED }}>
                <X size={14} />
              </button>
            </div>
          </div>

          <div className="flex-1 overflow-y-auto">
            {alerts.length === 0 ? (
              <div className="flex flex-col items-center justify-center h-full gap-2">
                <Bell size={22} style={{ color: CARD_MUTED, opacity: 0.4 }} />
                <p className="text-[12px]" style={{ color: CARD_MUTED }}>No unread alerts</p>
              </div>
            ) : (
              <div>
                {alerts.map(a => {
                  const s = SEVERITY_STYLE[a.severity] ?? SEVERITY_STYLE.info;
                  return (
                    <div
                      key={a.alert_id}
                      className="px-4 py-3.5 transition-colors"
                      style={{
                        borderBottom: `1px solid ${PANEL_BORDER}`,
                        borderLeft: `3px solid ${a.is_read ? "transparent" : s.dot}`,
                        background: a.is_read ? "transparent" : "rgba(250,189,73,0.04)",
                      }}
                    >
                      <div className="flex items-start justify-between gap-2">
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-1.5 mb-1.5 flex-wrap">
                            <span className="w-1.5 h-1.5 rounded-full shrink-0" style={{ background: s.dot }} />
                            <span className="text-[9px] font-bold tracking-wide" style={{ color: s.dot }}>{s.label}</span>
                            {a.alert_type === "ai" && (
                              <span
                                className="flex items-center gap-0.5 text-[9px] font-bold tracking-wide px-1.5 py-0.5 rounded-full shrink-0"
                                style={{ color: GOLD, background: "rgba(250,189,73,0.12)" }}
                                title="Generated by GPT-4o"
                              >
                                <Sparkles size={8} /> AI
                              </span>
                            )}
                            <span className="text-[9px] ml-auto" style={{ color: CARD_MUTED }}>{timeAgo(a.triggered_at)}</span>
                          </div>
                          {a.portfolio_name && (
                            <p className="text-[9px] font-semibold tracking-wide truncate mb-0.5" style={{ color: CARD_MUTED }}>
                              {a.portfolio_name.toUpperCase()}
                            </p>
                          )}
                          <p className="text-[12px] font-medium mb-0.5 truncate text-white">{a.title}</p>
                          <p className="text-[11px] leading-relaxed" style={{ color: CARD_MUTED }}>{a.message}</p>
                        </div>
                        {!a.is_read && (
                          <button
                            onClick={() => handleMarkRead(a.alert_id)}
                            className="shrink-0 mt-0.5 p-1.5 rounded-lg transition-colors"
                            style={{ color: GREEN, background: "rgba(0,200,83,0.10)" }}
                            title="Mark this alert as read"
                          >
                            <Check size={12} />
                          </button>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>
      )}
    </>
  );
}
