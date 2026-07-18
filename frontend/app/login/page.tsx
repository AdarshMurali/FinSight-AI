"use client";
import { useState, FormEvent } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/context/AuthContext";
import { manrope, GOLD, AMBER_DARK, NEAR_BLACK, WHITE, MUTED, RED, WARNING, BORDER } from "@/lib/theme";
import { LogoTile } from "@/components/Logo";

const PAGE_GRADIENT = "radial-gradient(ellipse 100% 90% at 100% 100%, #fabd49 0%, #c47c10 20%, #4a2f08 42%, #0a0a0a 68%, #010101 100%)";

export default function LoginPage() {
  const { login } = useAuth();
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [warmingUp, setWarmingUp] = useState(false);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    setWarmingUp(false);
    setSubmitting(true);
    try {
      await login(email, password, () => setWarmingUp(true));
      router.push("/");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Invalid email or password");
    } finally {
      setSubmitting(false);
      setWarmingUp(false);
    }
  };

  return (
    <div
      className={`min-h-screen flex items-center justify-center px-4 ${manrope.className}`}
      style={{ background: PAGE_GRADIENT }}
    >
      <div className="w-full max-w-sm rounded-2xl overflow-hidden" style={{ background: NEAR_BLACK, border: `1px solid ${BORDER}`, boxShadow: "0 1.6rem 4rem rgba(196,124,16,0.28)" }}>

        <div className="px-8 pt-9 pb-6 text-center" style={{ borderBottom: `1px solid ${BORDER}` }}>
          <div className="flex items-center justify-center gap-2 mb-1.5">
            <LogoTile size={40} />
          </div>
          <p className="font-extrabold text-[22px] tracking-tight">
            <span style={{ color: WHITE }}>Fin</span><span style={{ color: GOLD }}>Sight</span><span style={{ color: WHITE }}> AI</span>
          </p>
          <p className="text-[11px] tracking-wide mt-1" style={{ color: MUTED }}>
            Portfolio Intelligence Terminal
          </p>
        </div>

        <form onSubmit={handleSubmit} className="px-8 py-6 space-y-4">
          <div>
            <label className="block text-[10px] tracking-wide uppercase mb-1.5" style={{ color: MUTED }}>
              Email
            </label>
            <input
              type="email"
              required
              autoFocus
              value={email}
              onChange={e => setEmail(e.target.value)}
              className="w-full px-3.5 py-2.5 text-sm rounded-lg outline-none transition-colors"
              style={{ background: "#000", border: `1px solid ${BORDER}`, color: WHITE }}
              onFocus={e => (e.currentTarget.style.borderColor = GOLD)}
              onBlur={e => (e.currentTarget.style.borderColor = BORDER)}
              placeholder="you@finsight.demo"
            />
          </div>

          <div>
            <label className="block text-[10px] tracking-wide uppercase mb-1.5" style={{ color: MUTED }}>
              Password
            </label>
            <input
              type="password"
              required
              value={password}
              onChange={e => setPassword(e.target.value)}
              className="w-full px-3.5 py-2.5 text-sm rounded-lg outline-none transition-colors"
              style={{ background: "#000", border: `1px solid ${BORDER}`, color: WHITE }}
              onFocus={e => (e.currentTarget.style.borderColor = GOLD)}
              onBlur={e => (e.currentTarget.style.borderColor = BORDER)}
              placeholder="••••••••••••"
            />
          </div>

          {warmingUp && (
            <div className="flex items-start gap-2.5 px-3.5 py-3 rounded-lg" style={{ background: "rgba(255,204,29,0.08)", border: `1px solid ${WARNING}40` }}>
              <span className="w-1.5 h-1.5 rounded-full mt-1 shrink-0 animate-pulse" style={{ background: WARNING }} />
              <p className="text-[11px] leading-relaxed" style={{ color: MUTED }}>
                <span className="font-bold tracking-wide" style={{ color: WARNING }}>SYSTEM WARMING UP — </span>
                our database sleeps after a period of inactivity to save cost, and takes up to a minute
                to wake on the first request. This only happens occasionally — hang tight, you&apos;ll be
                signed in automatically once it&apos;s ready.
              </p>
            </div>
          )}

          {error && (
            <p className="text-[12px]" style={{ color: RED }}>
              {error}
            </p>
          )}

          <button
            type="submit"
            disabled={submitting}
            className="w-full py-3 text-[12px] font-bold tracking-wide uppercase rounded-lg transition-opacity disabled:opacity-50"
            style={{ background: `linear-gradient(to right, ${GOLD}, ${AMBER_DARK})`, color: "#000" }}
          >
            {warmingUp ? "Warming up…" : submitting ? "Signing in…" : "Sign In"}
          </button>
        </form>
      </div>
    </div>
  );
}
