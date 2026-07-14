"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { LayoutDashboard, BarChart3, Sparkles, Radio, TrendingUp, MessageSquare, Bell, X, CheckCheck, LogOut } from "lucide-react";
import { getAlerts, getUnreadCount, markAlertRead, markAllAlertsRead, AlertItem } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";

const nav = [
  { href: "/",              label: "DASHBOARD",   icon: LayoutDashboard },
  { href: "/portfolios",    label: "PORTFOLIOS",  icon: BarChart3 },
  { href: "/ai-insights",   label: "AI INSIGHTS", icon: Sparkles },
  { href: "/chat",          label: "AI CHAT",     icon: MessageSquare },
  { href: "/market-events", label: "MKT EVENTS",  icon: Radio },
];

const SEVERITY_STYLE: Record<string, { dot: string; border: string; label: string }> = {
  critical: { dot: "#FF4040", border: "rgba(255,64,64,0.25)",  label: "CRITICAL" },
  warning:  { dot: "#FFB300", border: "rgba(255,179,0,0.25)",  label: "WARNING"  },
  info:     { dot: "#00CC44", border: "rgba(0,204,68,0.25)",   label: "INFO"     },
};

function timeAgo(iso: string) {
  const diff = Date.now() - new Date(iso).getTime();
  const m = Math.floor(diff / 60000);
  if (m < 60)   return `${m}m ago`;
  const h = Math.floor(m / 60);
  if (h < 24)   return `${h}h ago`;
  return `${Math.floor(h / 24)}d ago`;
}

export default function Sidebar() {
  const path = usePathname();
  const { user, logout } = useAuth();
  const [panelOpen,   setPanelOpen]   = useState(false);
  const [alerts,      setAlerts]      = useState<AlertItem[]>([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const panelRef = useRef<HTMLDivElement>(null);

  const fetchAlerts = async () => {
    try {
      const [data, uc] = await Promise.all([getAlerts({ limit: 30 }), getUnreadCount()]);
      setAlerts(data);
      setUnreadCount(uc.count);
    } catch { /* silent */ }
  };

  useEffect(() => {
    fetchAlerts();
    const id = setInterval(fetchAlerts, 60_000);
    return () => clearInterval(id);
  }, []);

  // close panel on outside click
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
    setAlerts(prev => prev.map(a => a.alert_id === id ? { ...a, is_read: true } : a));
    setUnreadCount(c => Math.max(0, c - 1));
  };

  const handleMarkAll = async () => {
    await markAllAlertsRead();
    setAlerts(prev => prev.map(a => ({ ...a, is_read: true })));
    setUnreadCount(0);
  };

  return (
    <>
      <aside
        className="fixed top-0 left-0 h-screen w-52 bg-[#0D0D0D] flex flex-col z-50"
        style={{ borderRight: "1px solid rgba(255,120,0,0.18)" }}
      >
        {/* Orange accent top bar */}
        <div style={{ height: "3px", background: "linear-gradient(to right, #FF8000, #7A2500)" }} />

        {/* Logo */}
        <div className="px-4 pt-4 pb-3.5" style={{ borderBottom: "1px solid rgba(255,120,0,0.15)" }}>
          <div className="flex items-center gap-2 mb-1">
            <TrendingUp size={14} className="text-[#FF8000]" />
            <span className="text-[#FF8000] font-bold text-sm tracking-[0.22em]">FINSIGHT</span>
          </div>
          <p className="text-[9px] tracking-[0.18em] uppercase pl-5" style={{ color: "#8A6040" }}>
            Portfolio Terminal
          </p>
        </div>

        {/* Navigation */}
        <nav className="flex-1 py-2">
          {nav.map(({ href, label, icon: Icon }) => {
            const active = path === href || (href !== "/" && path.startsWith(href));
            return (
              <Link
                key={href}
                href={href}
                className="flex items-center gap-3 px-4 py-2.5 text-[10px] tracking-[0.15em] transition-all duration-150 border-l-2"
                style={active ? {
                  borderLeftColor: "#FF8000",
                  color: "#FFF0E6",
                  background: "rgba(255,128,0,0.10)",
                } : {
                  borderLeftColor: "transparent",
                  color: "#A87860",
                }}
                onMouseEnter={e => {
                  if (!active) {
                    (e.currentTarget as HTMLElement).style.color = "#F0C090";
                    (e.currentTarget as HTMLElement).style.background = "rgba(255,128,0,0.06)";
                    (e.currentTarget as HTMLElement).style.borderLeftColor = "rgba(255,128,0,0.40)";
                  }
                }}
                onMouseLeave={e => {
                  if (!active) {
                    (e.currentTarget as HTMLElement).style.color = "#A87860";
                    (e.currentTarget as HTMLElement).style.background = "";
                    (e.currentTarget as HTMLElement).style.borderLeftColor = "transparent";
                  }
                }}
              >
                <Icon size={12} style={{ opacity: active ? 1 : 0.65 }} />
                {label}
              </Link>
            );
          })}
        </nav>

        {/* Divider */}
        <div style={{ height: "1px", background: "rgba(255,120,0,0.15)" }} />

        {/* Bell icon */}
        <div className="px-4 py-3" style={{ borderBottom: "1px solid rgba(255,120,0,0.10)" }}>
          <button
            onClick={() => { setPanelOpen(o => !o); if (!panelOpen) fetchAlerts(); }}
            className="relative flex items-center gap-2 w-full text-left"
          >
            <div className="relative">
              <Bell size={14} style={{ color: unreadCount > 0 ? "#FFB300" : "#6A4828" }} />
              {unreadCount > 0 && (
                <span
                  className="absolute -top-1.5 -right-1.5 flex items-center justify-center rounded-full text-[8px] font-bold"
                  style={{ background: "#FF4040", color: "#fff", minWidth: 14, height: 14, padding: "0 3px" }}
                >
                  {unreadCount > 99 ? "99+" : unreadCount}
                </span>
              )}
            </div>
            <span className="text-[9px] tracking-[0.12em] uppercase" style={{ color: unreadCount > 0 ? "#FFB300" : "#6A4828" }}>
              ALERTS{unreadCount > 0 ? ` (${unreadCount})` : ""}
            </span>
          </button>
        </div>

        {/* System status */}
        <div className="px-4 py-3 space-y-2">
          <div className="flex items-center gap-2">
            <span className="w-1.5 h-1.5 rounded-full bg-[#00CC44] animate-pulse shrink-0" />
            <span className="text-[#00CC44] text-[9px] font-bold tracking-[0.15em]">LIVE</span>
            <span className="text-[9px] ml-auto" style={{ color: "#6A4828" }}>
              {(process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000").replace(/^https?:\/\//, "")}
            </span>
          </div>
          <div className="flex justify-between">
            <span className="text-[9px] tracking-wider" style={{ color: "#6A4828" }}>RAG</span>
            <span className="text-[9px]" style={{ color: "#9A6B46" }}>CHROMADB</span>
          </div>
          <div className="flex justify-between">
            <span className="text-[9px] tracking-wider" style={{ color: "#6A4828" }}>AI</span>
            <span className="text-[9px]" style={{ color: "#9A6B46" }}>GPT-4o</span>
          </div>
        </div>

        {/* Logged-in user + logout */}
        {user && (
          <div
            className="px-4 py-3 flex items-center justify-between gap-2"
            style={{ borderTop: "1px solid rgba(255,120,0,0.10)" }}
          >
            <div className="min-w-0">
              <p className="text-[10px] font-semibold truncate" style={{ color: "#E8C090" }}>
                {user.full_name}
              </p>
              <p className="text-[8px] tracking-[0.1em] uppercase" style={{ color: "#6A4828" }}>
                {user.role === "admin" ? "Admin" : "Fund Manager"}
              </p>
            </div>
            <button
              onClick={logout}
              title="Log out"
              className="shrink-0 p-1.5 rounded transition-colors"
              style={{ color: "#6A4828" }}
              onMouseEnter={e => ((e.currentTarget as HTMLElement).style.color = "#FF8000")}
              onMouseLeave={e => ((e.currentTarget as HTMLElement).style.color = "#6A4828")}
            >
              <LogOut size={13} />
            </button>
          </div>
        )}

        {/* Bottom accent bar */}
        <div style={{ height: "2px", background: "linear-gradient(to right, #7A2500, #FF8000)" }} />
      </aside>

      {/* Alert slide-out panel */}
      {panelOpen && (
        <div
          ref={panelRef}
          className="fixed top-0 left-52 h-screen w-80 z-40 flex flex-col overflow-hidden"
          style={{
            background: "#0F0F0F",
            borderRight: "1px solid rgba(255,120,0,0.20)",
            boxShadow: "4px 0 24px rgba(0,0,0,0.6)",
          }}
        >
          {/* Panel header */}
          <div
            className="flex items-center justify-between px-4 py-3 shrink-0"
            style={{
              background: "linear-gradient(to right, #FF8000, #7A2500)",
              borderBottom: "1px solid rgba(255,120,0,0.30)",
            }}
          >
            <div className="flex items-center gap-2">
              <Bell size={12} className="text-white" />
              <span className="text-white text-[10px] font-bold tracking-[0.18em] uppercase">Alerts</span>
              {unreadCount > 0 && (
                <span className="text-[8px] font-bold px-1.5 py-0.5 rounded-full" style={{ background: "#FF4040", color: "#fff" }}>
                  {unreadCount}
                </span>
              )}
            </div>
            <div className="flex items-center gap-2">
              {unreadCount > 0 && (
                <button onClick={handleMarkAll} title="Mark all read">
                  <CheckCheck size={12} className="text-white/70 hover:text-white transition-colors" />
                </button>
              )}
              <button onClick={() => setPanelOpen(false)}>
                <X size={12} className="text-white/70 hover:text-white transition-colors" />
              </button>
            </div>
          </div>

          {/* Alert list */}
          <div className="flex-1 overflow-y-auto">
            {alerts.length === 0 ? (
              <div className="flex flex-col items-center justify-center h-full gap-2">
                <Bell size={20} style={{ color: "#3A2010" }} />
                <p className="text-[10px] tracking-wider" style={{ color: "#5A3820" }}>No alerts</p>
              </div>
            ) : (
              <div className="divide-y" style={{ borderColor: "rgba(255,120,0,0.08)" }}>
                {alerts.map(a => {
                  const s = SEVERITY_STYLE[a.severity] ?? SEVERITY_STYLE.info;
                  return (
                    <div
                      key={a.alert_id}
                      className="px-4 py-3 transition-colors"
                      style={{
                        background: a.is_read ? "transparent" : "rgba(255,128,0,0.04)",
                        borderLeft: `3px solid ${a.is_read ? "transparent" : s.dot}`,
                      }}
                    >
                      <div className="flex items-start justify-between gap-2">
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-1.5 mb-1">
                            <span
                              className="w-1.5 h-1.5 rounded-full shrink-0"
                              style={{ background: s.dot }}
                            />
                            <span
                              className="text-[8px] font-bold tracking-wider px-1 py-0.5 border"
                              style={{ color: s.dot, borderColor: s.border }}
                            >
                              {s.label}
                            </span>
                            {a.alert_type === "ai" && (
                              <span
                                className="flex items-center gap-0.5 text-[8px] font-bold tracking-wider px-1 py-0.5 border shrink-0"
                                style={{ color: "#F5821F", borderColor: "rgba(245,130,31,0.4)", background: "rgba(245,130,31,0.08)" }}
                                title="Generated by GPT-4o"
                              >
                                <Sparkles size={8} /> AI
                              </span>
                            )}
                            <span className="text-[8px] ml-auto" style={{ color: "#5A3820" }}>
                              {timeAgo(a.triggered_at)}
                            </span>
                          </div>
                          <p className="text-[10px] font-semibold mb-0.5 truncate" style={{ color: "#E8C090" }}>
                            {a.title}
                          </p>
                          <p className="text-[9px] leading-relaxed" style={{ color: "#7A5030" }}>
                            {a.message}
                          </p>
                        </div>
                        {!a.is_read && (
                          <button
                            onClick={() => handleMarkRead(a.alert_id)}
                            className="shrink-0 mt-0.5 p-0.5"
                            title="Mark this alert as read"
                          >
                            <X size={10} style={{ color: "#A87860" }} className="hover:text-[#FF8000] transition-colors" />
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
