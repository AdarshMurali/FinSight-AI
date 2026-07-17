"use client";
import { useEffect } from "react";
import { usePathname, useRouter } from "next/navigation";
import { useAuth } from "@/context/AuthContext";
import BloombergSidebar from "@/components/BloombergSidebar";

// Bloomberg's own gradient stops (sampled from professional.bloomberg.com's
// CSS), anchored bottom-right — matching the glow direction on their own
// cards — so the sidebar corner stays near-black and the far content corner
// warms up toward gold. Rendered once here (not per-page) so it spans behind
// both the sidebar and main content with no seam at the sidebar boundary.
const BLOOMBERG_PAGE_GRADIENT = "radial-gradient(ellipse 100% 90% at 100% 100%, #fabd49 0%, #c47c10 20%, #4a2f08 42%, #0a0a0a 68%, #010101 100%)";

export default function AppShell({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth();
  const pathname = usePathname();
  const router = useRouter();
  const isLoginPage = pathname === "/login";
  // The dashboard ("/") keeps the slightly tighter p-4 from its earlier
  // density trim; every other page uses the roomier p-5 it was built against.
  const isDashboard = pathname === "/";

  useEffect(() => {
    if (!loading && !user && !isLoginPage) {
      router.replace("/login");
    }
  }, [loading, user, isLoginPage, router]);

  if (isLoginPage) {
    return <>{children}</>;
  }

  if (loading || !user) {
    // Either still checking the session, or redirecting to /login — render nothing
    // rather than flashing protected content or a half-built sidebar.
    return <div className="min-h-screen bg-black" />;
  }

  return (
    <>
      <div className="fixed inset-0" style={{ background: "#010101", zIndex: 0 }} />
      <div className="fixed inset-0" style={{ background: BLOOMBERG_PAGE_GRADIENT, zIndex: 0 }} />
      <BloombergSidebar />
      <main className={`relative ml-64 min-h-screen ${isDashboard ? "p-4" : "p-5"}`} style={{ zIndex: 1 }}>{children}</main>
    </>
  );
}
