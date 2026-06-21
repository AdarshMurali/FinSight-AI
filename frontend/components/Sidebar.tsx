"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { LayoutDashboard, BarChart3, Sparkles, Radio, TrendingUp, MessageSquare } from "lucide-react";

const nav = [
  { href: "/",              label: "DASHBOARD",   icon: LayoutDashboard },
  { href: "/portfolios",    label: "PORTFOLIOS",  icon: BarChart3 },
  { href: "/ai-insights",   label: "AI INSIGHTS", icon: Sparkles },
  { href: "/chat",          label: "AI CHAT",     icon: MessageSquare },
  { href: "/market-events", label: "MKT EVENTS",  icon: Radio },
];

export default function Sidebar() {
  const path = usePathname();

  return (
    <aside className="fixed top-0 left-0 h-screen w-52 bg-black border-r border-[#2A2A2A] flex flex-col z-50">

      {/* Logo */}
      <div className="px-4 py-4 border-b border-[#2A2A2A] bg-[#0D0D0D]">
        <div className="flex items-center gap-2 mb-0.5">
          <TrendingUp size={14} className="text-[#F5821F]" />
          <span className="text-[#F5821F] font-bold text-sm tracking-[0.2em]">FINSIGHT</span>
        </div>
        <p className="text-[#777] text-[9px] tracking-[0.15em] uppercase pl-5">
          Portfolio Terminal
        </p>
      </div>

      {/* Navigation */}
      <nav className="flex-1 pt-2">
        {nav.map(({ href, label, icon: Icon }) => {
          const active = path === href || (href !== "/" && path.startsWith(href));
          return (
            <Link
              key={href}
              href={href}
              className={`flex items-center gap-3 px-4 py-2.5 text-[10px] tracking-[0.15em] transition-colors border-l-2 ${
                active
                  ? "border-[#F5821F] text-[#F5821F] bg-[#F5821F]/8"
                  : "border-transparent text-[#AAA] hover:text-[#E0E0E0] hover:bg-[#111] hover:border-[#555]"
              }`}
            >
              <Icon size={12} />
              {label}
            </Link>
          );
        })}
      </nav>

      <div className="border-t border-[#2A2A2A]" />

      {/* System status */}
      <div className="px-4 py-3 bg-[#0D0D0D] space-y-1.5">
        <div className="flex items-center gap-2">
          <span className="w-1.5 h-1.5 rounded-full bg-[#00CC44] animate-pulse shrink-0" />
          <span className="text-[#00CC44] text-[9px] font-bold tracking-[0.15em]">LIVE</span>
          <span className="text-[#888] text-[9px] ml-auto">:8000</span>
        </div>
        <div className="flex justify-between">
          <span className="text-[#777] text-[9px] tracking-wider">RAG</span>
          <span className="text-[#AAA] text-[9px]">CHROMADB</span>
        </div>
        <div className="flex justify-between">
          <span className="text-[#777] text-[9px] tracking-wider">AI</span>
          <span className="text-[#AAA] text-[9px]">GPT-4o</span>
        </div>
      </div>
    </aside>
  );
}
