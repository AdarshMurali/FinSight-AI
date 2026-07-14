interface SectionHeaderProps {
  title: string;
  sub?: string;
  action?: React.ReactNode;
}

export default function SectionHeader({ title, sub, action }: SectionHeaderProps) {
  return (
    <div
      className="flex items-center justify-between px-3 py-1.5"
      style={{ background: "linear-gradient(to right, #FF8000, #7A2500)" }}
    >
      <div className="flex items-center gap-2">
        <span className="text-white text-[10px] font-bold tracking-[0.18em] uppercase drop-shadow">{title}</span>
        {sub && <span className="text-white/60 text-[9px] tracking-wider">/ {sub}</span>}
      </div>
      {action && <div>{action}</div>}
    </div>
  );
}
