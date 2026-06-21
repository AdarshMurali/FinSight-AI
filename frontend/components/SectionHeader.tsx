interface SectionHeaderProps {
  title: string;
  sub?: string;
  action?: React.ReactNode;
}

export default function SectionHeader({ title, sub, action }: SectionHeaderProps) {
  return (
    <div className="flex items-start justify-between mb-4">
      <div>
        <h2 className="text-[#e8e8f0] text-sm font-semibold tracking-wide">{title}</h2>
        {sub && <p className="text-[#5a5a70] text-[11px] mt-0.5">{sub}</p>}
      </div>
      {action && <div>{action}</div>}
    </div>
  );
}
