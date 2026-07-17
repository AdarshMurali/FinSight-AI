"use client";
import { useState, type ReactNode } from "react";
import { ChevronDown, ChevronUp, Database } from "lucide-react";
import { GOLD, WHITE, MUTED, BORDER } from "@/lib/theme";

// ── Inline bold parser (avoids dangerouslySetInnerHTML) ───────────────────
export function InlineText({ text }: { text: string }) {
  const parts = text.split(/(\*\*[^*]+\*\*)/g);
  return (
    <>
      {parts.map((part, i) =>
        part.startsWith("**") && part.endsWith("**")
          ? <strong key={i} style={{ color: WHITE }} className="font-semibold">{part.slice(2, -2)}</strong>
          : <span key={i}>{part}</span>
      )}
    </>
  );
}

// ── Smart text renderer: turns AI plain text into structured elements ──────
const HEADER_RE = /^\*\*[^*]+\*\*:?$/;
const isHeaderText = (t: string) => HEADER_RE.test(t) || (t.endsWith(":") && t.length < 80 && !t.includes("."));

export function SmartText({ text, bulletColor }: { text: string; bulletColor: string }) {
  const lines = text.split("\n");
  const result: ReactNode[] = [];
  let bullets: string[] = [];
  let paraLines: string[] = [];
  // True right after a header is emitted, until the next paragraph consumes
  // it — that paragraph is the header's explanation, so it renders indented
  // ("starts after a tab") instead of flush-left like an unrelated paragraph.
  let afterHeader = false;

  const flushBullets = (key: string | number) => {
    if (!bullets.length) return;
    afterHeader = false;
    result.push(
      <ul key={`ul-${key}`} className="space-y-2 my-2 ml-1">
        {bullets.map((b, i) => (
          <li key={i} className="flex gap-2.5 items-start">
            <span className={`mt-[7px] w-1.5 h-1.5 rounded-full shrink-0 ${bulletColor}`} />
            <span className="text-xs leading-6" style={{ color: MUTED }}><InlineText text={b} /></span>
          </li>
        ))}
      </ul>
    );
    bullets = [];
  };

  const flushPara = (key: string | number) => {
    if (!paraLines.length) return;
    const indented = afterHeader;
    afterHeader = false;
    result.push(
      <p key={`p-${key}`} className={`text-xs leading-6 ${indented ? "pl-4" : ""}`} style={{ color: MUTED }}>
        <InlineText text={paraLines.join(" ")} />
      </p>
    );
    paraLines = [];
  };

  const pushHeader = (raw: string, key: string | number) => {
    const label = raw.replace(/^\*\*|\*\*:?$|:$/g, "").trim();
    result.push(
      <p key={`h-${key}`} className="font-bold text-[10px] mt-5 mb-1 uppercase tracking-widest" style={{ color: WHITE }}>
        {label}
      </p>
    );
    afterHeader = true;
  };

  lines.forEach((line, i) => {
    const t = line.trim();
    if (!t) { flushBullets(i); flushPara(i); return; }

    const bulletMatch = t.match(/^[-•*]\s+(.+)/);
    const numberedMatch = t.match(/^\d+[.)]\s+(.+)/);

    if (bulletMatch || numberedMatch) {
      const inner = (bulletMatch ?? numberedMatch)![1].trim();
      // A bullet whose entire content is a bold label (e.g. "- **Healthcare
      // Allocation:**") is a sub-heading the model chose to prefix with a
      // dash, not a genuine list item — render it as a header so the
      // paragraph underneath reads as its explanation, not an orphaned bullet.
      if (HEADER_RE.test(inner)) {
        flushBullets(i);
        flushPara(i);
        pushHeader(inner, i);
        return;
      }
      flushPara(i);
      bullets.push(inner);
      return;
    }

    flushBullets(i);

    if (isHeaderText(t)) {
      flushPara(i);
      pushHeader(t, i);
      return;
    }

    paraLines.push(t);
  });

  flushBullets("end");
  flushPara("end");

  return <div className="space-y-1.5">{result}</div>;
}

// ── RAG sources collapsible ────────────────────────────────────────────────
export function RagSources({ sources }: { sources: { collection: string; snippet: string }[] }) {
  const [open, setOpen] = useState(false);
  if (!sources.length) return null;
  return (
    <div className="pt-3" style={{ borderTop: `1px solid ${BORDER}` }}>
      <button
        onClick={() => setOpen(o => !o)}
        className="flex items-center gap-1.5 text-[10px] transition-colors"
        style={{ color: MUTED }}
        onMouseEnter={e => (e.currentTarget.style.color = WHITE)}
        onMouseLeave={e => (e.currentTarget.style.color = MUTED)}
      >
        <Database size={10} />
        {open ? <ChevronUp size={10} /> : <ChevronDown size={10} />}
        {open ? "Hide" : `${sources.length}`} RAG sources used
      </button>
      {open && (
        <div className="mt-2 space-y-1.5">
          {sources.map((s, i) => (
            <div key={i} className="flex gap-2 text-[10px] rounded-lg px-2.5 py-1.5" style={{ background: "rgba(255,255,255,0.03)", border: `1px solid ${BORDER}` }}>
              <span className="shrink-0 opacity-90" style={{ color: GOLD }}>{s.collection}</span>
              <span className="truncate" style={{ color: MUTED }}>{s.snippet}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// ── Cost tag ──────────────────────────────────────────────────────────────
export function CostTag({ cost }: { cost: number }) {
  return (
    <span className="text-[9px] rounded-full px-1.5 py-0.5 shrink-0" style={{ color: MUTED, border: `1px solid ${BORDER}`, background: "rgba(255,255,255,0.03)" }}>
      ${cost.toFixed(4)} cost
    </span>
  );
}
