"use client";
import Link from "next/link";
import {
  Sparkles, ShieldCheck, Radio, Bell, Users, Plug, ArrowRight,
  Brain, Wrench, MessageSquare,
} from "lucide-react";
import { LogoTile } from "@/components/Logo";
import {
  manrope, GOLD, AMBER_DARK, NEAR_BLACK, WHITE, MUTED, BORDER, GOLD_SOFT,
  CARD_SHADOW, CARD_SHADOW_HOVER,
} from "@/lib/theme";

// ── Public landing page — the first thing a signed-out visitor sees, instead
// of being dropped straight onto a bare login form. Reuses the site's own
// design tokens (lib/theme.ts) and brand mark (components/Logo.tsx) so it
// reads as the same product, not a separate marketing site bolted on.
// AppShell routes unauthenticated visitors here (see components/AppShell.tsx);
// the CTA below sends them on to /login, same as before.

const PAGE_GRADIENT =
  "radial-gradient(ellipse 100% 90% at 100% 100%, #fabd49 0%, #c47c10 20%, #4a2f08 42%, #0a0a0a 68%, #010101 100%)";

const FEATURES: { icon: React.ComponentType<{ size?: number; style?: React.CSSProperties }>; title: string; body: string }[] = [
  {
    icon: MessageSquare,
    title: "Ask it anything — it investigates first",
    body: "The AI chat doesn't answer from memory. GPT-4o decides which of six tools it needs — portfolio data, position history, market context, live quotes — runs them, then drafts an answer grounded in what it actually found.",
  },
  {
    icon: ShieldCheck,
    title: "Real risk math, not AI guesswork",
    body: "VaR, five historical stress scenarios (2008, COVID, the 2022 rate shock, and more), factor exposure — all closed-form or regression code, recomputed daily. The model reasons about risk; it never calculates it.",
  },
  {
    icon: Radio,
    title: "Live market intelligence",
    body: "A Kafka + Flink streaming pipeline watches live trade ticks for abnormal volatility, alongside Fed, earnings, and M&A event tracking — so context is current, not last week's snapshot.",
  },
  {
    icon: Bell,
    title: "Alerts that find you",
    body: "Threshold breaches, market-event exposure, and AI-flagged catalysts land in your feed automatically. You don't go looking for risk — it comes looking for you.",
  },
  {
    icon: Users,
    title: "Built for real fund teams",
    body: "Role-scoped access enforced at the database layer, not just hidden in the UI — a manager sees their own book, an admin sees the firm, and that boundary holds everywhere, including inside the AI chat.",
  },
  {
    icon: Plug,
    title: "Query it from your own tools",
    body: "An MCP server exposes live portfolio and risk data to Claude Desktop, Cursor, or VS Code — so the same intelligence is reachable without opening a browser tab.",
  },
];

const STACK: { group: string; items: string[] }[] = [
  { group: "AI / LLM", items: ["GPT-4o", "GPT-4o-mini", "text-embedding-3-small", "ChromaDB RAG"] },
  { group: "Streaming", items: ["Kafka", "Apache Flink (PyFlink)"] },
  { group: "Backend", items: ["FastAPI", "Python", "Azure SQL"] },
  { group: "Frontend", items: ["Next.js", "React", "Tailwind CSS"] },
  { group: "Infra", items: ["AWS EC2", "Lambda + EventBridge", "Vercel"] },
  { group: "CI/CD", items: ["GitHub Actions", "Docker", "human-approved deploys"] },
];

function FeatureCard({ icon: Icon, title, body }: (typeof FEATURES)[number]) {
  return (
    <div
      className="p-6 rounded-2xl transition-all duration-300 hover:-translate-y-1"
      style={{ background: NEAR_BLACK, border: `1px solid ${BORDER}`, boxShadow: CARD_SHADOW }}
      onMouseEnter={e => (e.currentTarget.style.boxShadow = CARD_SHADOW_HOVER)}
      onMouseLeave={e => (e.currentTarget.style.boxShadow = CARD_SHADOW)}
    >
      <div className="w-10 h-10 rounded-xl flex items-center justify-center mb-4" style={{ background: GOLD_SOFT }}>
        <Icon size={18} style={{ color: GOLD }} />
      </div>
      <h3 className="text-[15px] font-bold text-white mb-2 leading-snug">{title}</h3>
      <p className="text-[13px] leading-relaxed" style={{ color: MUTED }}>{body}</p>
    </div>
  );
}

export default function WelcomePage() {
  return (
    <div className={`min-h-screen overflow-x-hidden ${manrope.className}`} style={{ background: "#010101" }}>
      <div className="fixed inset-0 pointer-events-none" style={{ background: PAGE_GRADIENT }} />

      <div className="relative max-w-6xl mx-auto px-6 sm:px-8">

        {/* ── Top bar ─────────────────────────────────────────────────────── */}
        <div className="flex items-center justify-between py-6">
          <div className="flex items-center gap-2.5">
            <LogoTile size={34} />
            <span className="font-extrabold text-[18px] tracking-tight">
              <span style={{ color: WHITE }}>Fin</span><span style={{ color: GOLD }}>Sight</span><span style={{ color: WHITE }}> AI</span>
            </span>
          </div>
          <Link
            href="/login"
            className="text-[12px] font-semibold px-4 py-2 rounded-lg transition-colors"
            style={{ color: WHITE, border: `1px solid ${BORDER}` }}
          >
            Sign In
          </Link>
        </div>

        {/* ── Hero ────────────────────────────────────────────────────────── */}
        <div className="pt-10 pb-16 sm:pt-16 sm:pb-24 text-center max-w-3xl mx-auto">
          <div
            className="flex w-fit max-w-full mx-auto items-center gap-2 px-3.5 py-1.5 rounded-full mb-6 text-[11px] font-bold tracking-wide text-center"
            style={{ background: GOLD_SOFT, color: GOLD, border: `1px solid ${BORDER}` }}
          >
            <Sparkles size={12} className="shrink-0" />
            AI-POWERED HEDGE FUND PORTFOLIO ANALYZER
          </div>

          <h1 className="text-[28px] sm:text-[52px] font-extrabold leading-[1.15] sm:leading-[1.08] tracking-tight mb-5 break-words">
            <span style={{ color: WHITE }}>Every question, fully investigated.</span>
            <br />
            <span style={{ color: GOLD }}>Every answer, fully sourced.</span>
          </h1>

          <p className="text-[16px] sm:text-[18px] leading-relaxed mb-9 break-words" style={{ color: MUTED }}>
            FinSight AI is an agentic portfolio-intelligence platform built for hedge funds and
            institutional investors. Ask it anything about risk, performance, or a breaking market
            event — it pulls live data, runs the numbers, and grounds every answer in evidence it
            actually retrieved. No canned dashboards. No waiting on an analyst.
          </p>

          <div className="flex flex-col items-center gap-3">
            <Link
              href="/login"
              className="inline-flex items-center gap-2 px-7 py-3.5 text-[13px] font-bold tracking-wide uppercase rounded-lg transition-transform hover:scale-[1.03]"
              style={{ background: `linear-gradient(to right, ${GOLD}, ${AMBER_DARK})`, color: "#000" }}
            >
              Sign Up
              <ArrowRight size={15} />
            </Link>
            <p className="text-[11px]" style={{ color: MUTED }}>
              This is a live, working demo — hosted on a lean cloud footprint to keep the project
              cost-efficient, so it may occasionally be resting outside active hours.
            </p>
          </div>
        </div>

        {/* ── Feature grid ────────────────────────────────────────────────── */}
        <div className="pb-16 sm:pb-24">
          <h2 className="text-[12px] font-bold tracking-[0.14em] text-center mb-10" style={{ color: MUTED }}>
            WHAT IT ACTUALLY DOES
          </h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
            {FEATURES.map(f => <FeatureCard key={f.title} {...f} />)}
          </div>
        </div>

        {/* ── How the chat loop works ─────────────────────────────────────── */}
        <div
          className="rounded-2xl p-7 sm:p-10 mb-16 sm:mb-24"
          style={{ background: NEAR_BLACK, border: `1px solid ${BORDER}`, boxShadow: CARD_SHADOW }}
        >
          <h2 className="text-[12px] font-bold tracking-[0.14em] mb-8" style={{ color: MUTED }}>
            THE CENTERPIECE: AN AGENTIC LOOP, NOT A CHATBOT
          </h2>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-6">
            {[
              { icon: MessageSquare, step: "1", title: "You ask", body: "“Why did tech exposure drop, and what's driving today's volatility?”" },
              { icon: Brain, step: "2", title: "GPT-4o decides", body: "It picks which tools it needs — data, risk, live market context — with no fixed script." },
              { icon: Wrench, step: "3", title: "It investigates, then answers", body: "Tools run, results feed back in, and the loop repeats until it has enough to answer — with sources cited." },
            ].map(s => (
              <div key={s.step}>
                <div className="flex items-center gap-2.5 mb-3">
                  <div className="w-8 h-8 rounded-lg flex items-center justify-center shrink-0" style={{ background: GOLD_SOFT }}>
                    <s.icon size={15} style={{ color: GOLD }} />
                  </div>
                  <span className="text-[11px] font-bold tracking-wide" style={{ color: GOLD }}>STEP {s.step}</span>
                </div>
                <h3 className="text-[14px] font-bold text-white mb-1.5">{s.title}</h3>
                <p className="text-[13px] leading-relaxed" style={{ color: MUTED }}>{s.body}</p>
              </div>
            ))}
          </div>
        </div>

        {/* ── Tech stack ──────────────────────────────────────────────────── */}
        <div className="pb-16 sm:pb-24">
          <h2 className="text-[12px] font-bold tracking-[0.14em] text-center mb-10" style={{ color: MUTED }}>
            UNDER THE HOOD
          </h2>
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-4">
            {STACK.map(s => (
              <div key={s.group} className="p-4 rounded-xl" style={{ background: NEAR_BLACK, border: `1px solid ${BORDER}` }}>
                <p className="text-[10px] font-bold tracking-wide mb-2.5" style={{ color: GOLD }}>{s.group.toUpperCase()}</p>
                <div className="space-y-1">
                  {s.items.map(i => (
                    <p key={i} className="text-[11.5px] leading-snug" style={{ color: MUTED }}>{i}</p>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* ── Closing CTA ─────────────────────────────────────────────────── */}
        <div className="pb-16 sm:pb-24 text-center">
          <h2 className="text-[24px] sm:text-[30px] font-extrabold text-white mb-4">
            Your portfolio has a lot to say.<br />Ask it.
          </h2>
          <Link
            href="/login"
            className="inline-flex items-center gap-2 px-7 py-3.5 text-[13px] font-bold tracking-wide uppercase rounded-lg transition-transform hover:scale-[1.03]"
            style={{ background: `linear-gradient(to right, ${GOLD}, ${AMBER_DARK})`, color: "#000" }}
          >
            Sign Up
            <ArrowRight size={15} />
          </Link>
        </div>

        {/* ── Footer ──────────────────────────────────────────────────────── */}
        <div
          className="flex flex-col sm:flex-row items-center justify-between gap-3 py-6 text-[11px]"
          style={{ borderTop: `1px solid ${BORDER}`, color: MUTED }}
        >
          <span className="flex items-center gap-2">
            <LogoTile size={16} />
            FinSight AI — a portfolio-intelligence platform built as a systems-engineering showcase
          </span>
          <span>GPT-4o &middot; ChromaDB RAG &middot; Kafka + Flink &middot; AWS &middot; Azure SQL</span>
        </div>
      </div>
    </div>
  );
}
