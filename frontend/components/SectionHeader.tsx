import { GOLD, AMBER_DARK } from "@/lib/theme";

interface SectionHeaderProps {
  title: string;
  sub?: string;
  action?: React.ReactNode;
}

export default function SectionHeader({ title, sub, action }: SectionHeaderProps) {
  return (
    <div
      className="flex items-center justify-between px-4 py-2.5"
      style={{ background: `linear-gradient(to right, ${GOLD}, ${AMBER_DARK})` }}
    >
      <div className="flex items-center gap-2">
        <span className="text-black text-[11px] font-bold tracking-wide uppercase">{title}</span>
        {sub && <span className="text-black/55 text-[10px] tracking-wide">/ {sub}</span>}
      </div>
      {action && <div>{action}</div>}
    </div>
  );
}
