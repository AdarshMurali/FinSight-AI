export default function LoadingSpinner({ label = "Loading..." }: { label?: string }) {
  return (
    <div className="flex items-center gap-3 text-[#5a5a70] text-sm py-8">
      <span className="w-4 h-4 border-2 border-[#2a2a3a] border-t-[#1e90ff] rounded-full animate-spin" />
      {label}
    </div>
  );
}
