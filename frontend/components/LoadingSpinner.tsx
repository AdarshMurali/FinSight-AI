export default function LoadingSpinner({ label = "LOADING..." }: { label?: string }) {
  return (
    <div className="flex items-center gap-3 text-[#555] text-[11px] py-8 tracking-widest uppercase">
      <span className="w-3 h-3 border border-[#2A2A2A] border-t-[#F5821F] animate-spin" />
      {label}
    </div>
  );
}
