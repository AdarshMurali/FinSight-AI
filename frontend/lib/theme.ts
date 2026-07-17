import { Manrope } from "next/font/google";

// ── Site-wide design system — Bloomberg Professional–inspired (black + gold),
// shared by every authenticated page so the whole app reads as one product.
// See app/page.tsx for how the palette was originally derived from
// professional.bloomberg.com's own CSS.
export const manrope = Manrope({ subsets: ["latin"], weight: ["400", "500", "600", "700", "800"] });

export const NEAR_BLACK = "#0a0a0a";
export const GOLD    = "#fabd49";
export const AMBER_DARK = "#c47c10";
export const WHITE   = "#FFFFFF";
export const MUTED   = "#9C9CA5";
export const GREEN   = "#00C853";
export const RED     = "#e51e3c";
export const WARNING = "#FFCC1D";
export const BORDER  = "rgba(250,189,73,0.14)";
export const GOLD_SOFT = "rgba(250,189,73,0.12)";

// On-brand gold ramp (bright → dark) for categorical/ordinal chart data —
// colorblind-safe by construction (differentiated by lightness, not hue).
export const GOLD_SCALE = ["#FFE7A8", "#FCCB6B", "#FABD49", "#E0A030", "#C47C10", "#9C6410", "#7A4E0E", "#5C3B0C"];
export const OTHER_GRAY = "#5a5b63";
export const CHART_SURFACE = "#1a1a19";

export function goldByRank(index: number, total: number): string {
  const i = Math.min(
    Math.round((index / Math.max(total - 1, 1)) * (GOLD_SCALE.length - 1)),
    GOLD_SCALE.length - 1
  );
  return GOLD_SCALE[i];
}

export const CARD_SHADOW       = "0 1rem 2.8rem rgba(0,0,0,0.5)";
export const CARD_SHADOW_HOVER = "0 1.6rem 4rem rgba(196,124,16,0.28)";

export function fmt(n: number | null | undefined) {
  if (n == null) return "—";
  if (Math.abs(n) >= 1e9) return `$${(n / 1e9).toFixed(2)}B`;
  if (Math.abs(n) >= 1e6) return `$${(n / 1e6).toFixed(2)}M`;
  return `$${n.toLocaleString()}`;
}

export function pct(n: number | null | undefined) {
  if (n == null) return "—";
  const v = Number(n) * 100;
  return `${v >= 0 ? "+" : ""}${v.toFixed(2)}%`;
}

export function initials(name: string | null | undefined) {
  if (!name) return "?";
  const parts = name.trim().split(/\s+/);
  return ((parts[0]?.[0] ?? "") + (parts[1]?.[0] ?? "")).toUpperCase() || "?";
}

export function impactColor(level: string | null | undefined) {
  if (level === "high") return RED;
  if (level === "medium") return WARNING;
  if (level === "low") return GREEN;
  return MUTED;
}
