"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { LayoutDashboard, BarChart3, Sparkles, Radio, TrendingUp } from "lucide-react";

const nav = [
  { href: "/",              label: "Dashboard",      icon: LayoutDashboard },
  { href: "/portfolios",    label: "Portfolios",     icon: BarChart3 },
  { href: "/ai-insights",   label: "AI Insights",   icon: Sparkles },
  { href: "/market-events", label: "Market Events", icon: Radio },
];

export default function Sidebar() {
  const path = usePathname();

  return (
    <aside className="fixed top-0 left-0 h-screen w-56 bg-[#111118] border-r border-[#2a2a3a] flex flex-col z-50">
      {/* Logo */}
      <div className="px-5 py-5 border-b border-[#2a2a3a]">
        <div className="flex items-center gap-2">
          <TrendingUp size={18} className="text-[#1e90ff]" />
          <span className="text-[#e8e8f0] font-semibold text-sm tracking-wider">FinSight AI</span>
        </div>
        <p className="text-[#5a5a70] text-[10px] mt-0.5 tracking-widest uppercase">Portfolio Intelligence</p>
      </div>

      {/* Nav */}
      <nav className="flex-1 px-3 py-4 space-y-1">
        {nav.map(({ href, label, icon: Icon }) => {
          const active = path === href || (href !== "/" && path.startsWith(href));
          return (
            <Link
              key={href}
              href={href}
              className={`flex items-center gap-3 px-3 py-2.5 rounded text-sm transition-colors ${
                active
                  ? "bg-[#1e90ff]/10 text-[#1e90ff] border border-[#1e90ff]/20"
                  : "text-[#9898b0] hover:text-[#e8e8f0] hover:bg-[#1a1a24]"
              }`}
            >
              <Icon size={15} />
              {label}
            </Link>
          );
        })}
      </nav>

      {/* Footer */}
      <div className="px-5 py-4 border-t border-[#2a2a3a]">
        <p className="text-[#5a5a70] text-[10px]">API: localhost:8000</p>
        <div className="flex items-center gap-1.5 mt-1">
          <span className="w-1.5 h-1.5 rounded-full bg-[#00d084] animate-pulse" />
          <span className="text-[#5a5a70] text-[10px]">Live</span>
        </div>
      </div>
    </aside>
  );
}
