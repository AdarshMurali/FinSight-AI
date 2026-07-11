"use client";
import { useEffect } from "react";
import { usePathname, useRouter } from "next/navigation";
import { useAuth } from "@/context/AuthContext";
import Sidebar from "@/components/Sidebar";

export default function AppShell({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth();
  const pathname = usePathname();
  const router = useRouter();
  const isLoginPage = pathname === "/login";

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
      <Sidebar />
      <main className="ml-52 min-h-screen p-5">{children}</main>
    </>
  );
}
