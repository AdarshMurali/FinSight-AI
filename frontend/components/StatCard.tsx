interface StatCardProps {
  label: string;
  value: string | number;
  sub?: string;
  positive?: boolean;
  negative?: boolean;
  accent?: "blue" | "green" | "red" | "yellow" | "purple";
}

const accentColor = {
  blue:   "text-[#1e90ff]",
  green:  "text-[#00d084]",
  red:    "text-[#ff4d4d]",
  yellow: "text-[#f5c518]",
  purple: "text-[#a78bfa]",
};

export default function StatCard({ label, value, sub, positive, negative, accent }: StatCardProps) {
  const valueClass = positive
    ? "text-[#00d084]"
    : negative
    ? "text-[#ff4d4d]"
    : accent
    ? accentColor[accent]
    : "text-[#e8e8f0]";

  return (
    <div className="bg-[#111118] border border-[#2a2a3a] rounded-lg p-4">
      <p className="text-[#9898b0] text-[10px] uppercase tracking-widest mb-2">{label}</p>
      <p className={`text-xl font-semibold ${valueClass}`}>{value}</p>
      {sub && <p className="text-[#5a5a70] text-[11px] mt-1">{sub}</p>}
    </div>
  );
}
