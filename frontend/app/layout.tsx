import type { Metadata } from "next";
import "./globals.css";
import { AuthProvider } from "@/hooks/useAuth";
import { Navbar } from "@/components/Navbar";

export const metadata: Metadata = {
  title: "DevHire — Next-Gen AI Applicant Tracking System",
  description: "Enterprise ATS powered by AI resume matching, real-time WebSockets, and distributed workflows.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="bg-slate-50 min-h-screen text-slate-900 flex flex-col">
        <AuthProvider>
          <Navbar />
          <main className="flex-1">{children}</main>
          <footer className="border-t border-slate-200 bg-white py-6 mt-16 text-center text-xs text-slate-400">
            © 2026 DevHire Technologies Inc. Built with FastAPI, PostgreSQL, Redis, Celery & Next.js.
          </footer>
        </AuthProvider>
      </body>
    </html>
  );
}

