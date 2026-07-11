"use client";
import { useState, FormEvent } from "react";
import { useRouter } from "next/navigation";
import { TrendingUp } from "lucide-react";
import { useAuth } from "@/context/AuthContext";

export default function LoginPage() {
  const { login } = useAuth();
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await login(email, password);
      router.push("/");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Invalid email or password");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-black px-4">
      <div
        className="w-full max-w-sm"
        style={{ border: "1px solid rgba(255,120,0,0.18)", background: "#0D0D0D" }}
      >
        <div style={{ height: "3px", background: "linear-gradient(to right, #FF8000, #7A2500)" }} />

        <div className="px-8 pt-8 pb-6 text-center" style={{ borderBottom: "1px solid rgba(255,120,0,0.15)" }}>
          <div className="flex items-center justify-center gap-2 mb-1">
            <TrendingUp size={18} className="text-[#FF8000]" />
            <span className="text-[#FF8000] font-bold text-lg tracking-[0.22em]">FINSIGHT</span>
          </div>
          <p className="text-[10px] tracking-[0.18em] uppercase" style={{ color: "#8A6040" }}>
            Portfolio Terminal
          </p>
        </div>

        <form onSubmit={handleSubmit} className="px-8 py-6 space-y-4">
          <div>
            <label className="block text-[9px] tracking-[0.15em] uppercase mb-1.5" style={{ color: "#8A6040" }}>
              Email
            </label>
            <input
              type="email"
              required
              autoFocus
              value={email}
              onChange={e => setEmail(e.target.value)}
              className="w-full px-3 py-2 text-sm outline-none"
              style={{
                background: "#000",
                border: "1px solid rgba(255,120,0,0.25)",
                color: "#E8C090",
              }}
              placeholder="you@finsight.demo"
            />
          </div>

          <div>
            <label className="block text-[9px] tracking-[0.15em] uppercase mb-1.5" style={{ color: "#8A6040" }}>
              Password
            </label>
            <input
              type="password"
              required
              value={password}
              onChange={e => setPassword(e.target.value)}
              className="w-full px-3 py-2 text-sm outline-none"
              style={{
                background: "#000",
                border: "1px solid rgba(255,120,0,0.25)",
                color: "#E8C090",
              }}
              placeholder="••••••••••••"
            />
          </div>

          {error && (
            <p className="text-[11px]" style={{ color: "#FF4040" }}>
              {error}
            </p>
          )}

          <button
            type="submit"
            disabled={submitting}
            className="w-full py-2.5 text-[11px] font-bold tracking-[0.15em] uppercase transition-opacity disabled:opacity-50"
            style={{ background: "linear-gradient(to right, #FF8000, #7A2500)", color: "#000" }}
          >
            {submitting ? "Signing in…" : "Sign In"}
          </button>
        </form>

        <div style={{ height: "2px", background: "linear-gradient(to right, #7A2500, #FF8000)" }} />
      </div>
    </div>
  );
}
