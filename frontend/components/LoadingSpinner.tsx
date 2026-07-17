import { GOLD, MUTED, BORDER } from "@/lib/theme";

export default function LoadingSpinner({ label = "Loading..." }: { label?: string }) {
  return (
    <div className="flex items-center gap-3 text-[12px] py-8 tracking-wide" style={{ color: MUTED }}>
      <span className="w-3.5 h-3.5 rounded-full border-2 animate-spin" style={{ borderColor: BORDER, borderTopColor: GOLD }} />
      {label}
    </div>
  );
}
