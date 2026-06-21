interface StatCardProps {
  label: string;
  value: string | number;
  sub?: string;
  positive?: boolean;
  negative?: boolean;
  accent?: "blue" | "green" | "red" | "yellow" | "purple" | "orange";
}

const accentColor: Record<string, string> = {
  blue:   "text-[#F5821F]",
  orange: "text-[#F5821F]",
  green:  "text-[#00CC44]",
  red:    "text-[#FF4040]",
  yellow: "text-[#FFB300]",
  purple: "text-[#FFB300]",
};

export default function StatCard({ label, value, sub, positive, negative, accent }: StatCardProps) {
  const valueClass = positive
    ? "text-[#00CC44]"
    : negative
    ? "text-[#FF4040]"
    : accent
    ? (accentColor[accent] ?? "text-[#E0E0E0]")
    : "text-[#E0E0E0]";

  return (
    <div className="bg-[#0D0D0D] border border-[#2A2A2A] p-4">
      <p className="text-[#F5821F] text-[9px] font-bold tracking-[0.15em] uppercase mb-2">{label}</p>
      <p className={`text-2xl font-bold tabular-nums ${valueClass}`}>{value}</p>
      {sub && <p className="text-[#AAA] text-[10px] mt-1 tracking-wider uppercase">{sub}</p>}
    </div>
  );
}
