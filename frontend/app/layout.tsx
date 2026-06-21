import type { Metadata } from "next";
import "./globals.css";
import Sidebar from "@/components/Sidebar";

export const metadata: Metadata = {
  title: "FinSight AI Terminal",
  description: "AI-powered hedge fund portfolio intelligence",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-black">
        <Sidebar />
        <main className="ml-52 min-h-screen p-5">{children}</main>
      </body>
    </html>
  );
}
