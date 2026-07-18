"use client";
import { useId } from "react";

// ── FinSight AI brand mark — ascending chart bars topped with the same
// sparkle glyph already used site-wide for "AI" (ticker, chat, insights).
// LogoTile is the rounded chip (sidebar/login); LogoMark is the bare
// transparent version for compact inline contexts (e.g. the footer strip).

function Bars({ gradId }: { gradId: string }) {
  return (
    <>
      <defs>
        <linearGradient id={gradId} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="#FCCB6B" />
          <stop offset="1" stopColor="#c47c10" />
        </linearGradient>
      </defs>
      <rect x="24" y="55" width="13" height="26" rx="6.5" fill={`url(#${gradId})`} />
      <rect x="44" y="42" width="13" height="39" rx="6.5" fill={`url(#${gradId})`} />
      <rect x="64" y="30" width="13" height="51" rx="6.5" fill={`url(#${gradId})`} />
      <circle cx="70.5" cy="23" r="13" fill="#fabd49" opacity="0.16" />
      <path
        d="M 70.5 14 C 71.3 19 73.2 20.9 78 21.8 C 73.2 22.6 71.3 24.6 70.5 29.5 C 69.7 24.6 67.8 22.6 63 21.8 C 67.8 20.9 69.7 19 70.5 14 Z"
        fill="#FFF6E0"
      />
    </>
  );
}

export function LogoTile({ size = 36 }: { size?: number }) {
  const gradId = useId();
  return (
    <svg width={size} height={size} viewBox="0 0 100 100" shapeRendering="geometricPrecision">
      <rect x="0" y="0" width="100" height="100" rx="22" fill="#0a0a0a" stroke="rgba(250,189,73,0.25)" strokeWidth="1.5" />
      <Bars gradId={gradId} />
    </svg>
  );
}

export function LogoMark({ size = 16 }: { size?: number }) {
  const gradId = useId();
  return (
    <svg width={size} height={size} viewBox="0 0 100 100" shapeRendering="geometricPrecision">
      <Bars gradId={gradId} />
    </svg>
  );
}
