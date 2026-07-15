"use client";
import { useState, type ReactNode } from "react";
import { ChevronDown, ChevronUp, Database } from "lucide-react";

// ── Inline bold parser (avoids dangerouslySetInnerHTML) ───────────────────
export function InlineText({ text }: { text: string }) {
  const parts = text.split(/(\*\*[^*]+\*\*)/g);
  return (
    <>
      {parts.map((part, i) =>
        part.startsWith("**") && part.endsWith("**")
          ? <strong key={i} className="text-[#E0E0E0] font-semibold">{part.slice(2, -2)}</strong>
          : <span key={i}>{part}</span>
      )}
    </>
  );
}

// ── Smart text renderer: turns AI plain text into structured elements ──────
export function SmartText({ text, bulletColor }: { text: string; bulletColor: string }) {
  const lines = text.split("\n");
  const result: ReactNode[] = [];
  let bullets: string[] = [];
  let paraLines: string[] = [];

  const flushBullets = (key: string | number) => {
    if (!bullets.length) return;
    result.push(
      <ul key={`ul-${key}`} className="space-y-2 my-2 ml-1">
        {bullets.map((b, i) => (
          <li key={i} className="flex gap-2.5 items-start">
            <span className={`mt-[7px] w-1.5 h-1.5 rounded-full shrink-0 ${bulletColor}`} />
            <span className="text-[#888] text-xs leading-6"><InlineText text={b} /></span>
          </li>
        ))}
      </ul>
    );
    bullets = [];
  };

  const flushPara = (key: string | number) => {
    if (!paraLines.length) return;
    result.push(
      <p key={`p-${key}`} className="text-[#888] text-xs leading-6">
        <InlineText text={paraLines.join(" ")} />
      </p>
    );
    paraLines = [];
  };

  lines.forEach((line, i) => {
    const t = line.trim();
    if (!t) { flushBullets(i); flushPara(i); return; }

    const bulletMatch = t.match(/^[-•*]\s+(.+)/);
    const numberedMatch = t.match(/^\d+[.)]\s+(.+)/);

    if (bulletMatch || numberedMatch) {
      flushPara(i);
      bullets.push((bulletMatch ?? numberedMatch)![1]);
      return;
    }

    flushBullets(i);

    const isHeader =
      /^\*\*[^*]+\*\*:?$/.test(t) ||
      (t.endsWith(":") && t.length < 80 && !t.includes("."));

    if (isHeader) {
      flushPara(i);
      const label = t.replace(/^\*\*|\*\*:?$|:$/g, "").trim();
      result.push(
        <p key={`h-${i}`} className="text-[#E0E0E0] font-bold text-[10px] mt-5 mb-1 uppercase tracking-widest">
          {label}
        </p>
      );
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
    <div className="pt-3 border-t border-[#1A1A1A]">
      <button
        onClick={() => setOpen(o => !o)}
        className="flex items-center gap-1.5 text-[#555] text-[10px] hover:text-[#888] transition-colors"
      >
        <Database size={10} />
        {open ? <ChevronUp size={10} /> : <ChevronDown size={10} />}
        {open ? "Hide" : `${sources.length}`} RAG sources used
      </button>
      {open && (
        <div className="mt-2 space-y-1.5">
          {sources.map((s, i) => (
            <div key={i} className="flex gap-2 text-[10px] bg-black px-2.5 py-1.5 border border-[#1A1A1A]">
              <span className="text-[#F5821F] font-mono shrink-0 opacity-80">{s.collection}</span>
              <span className="text-[#555] truncate">{s.snippet}</span>
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
    <span className="text-white/70 text-[9px] font-mono border border-white/25 px-1.5 py-0.5 bg-black/15 shrink-0">
      ${cost.toFixed(4)} cost
    </span>
  );
}
