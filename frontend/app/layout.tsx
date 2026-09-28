import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { Sidebar } from "@/components/Sidebar";

const inter = Inter({ subsets: ["latin"], variable: "--font-inter" });

export const metadata: Metadata = {
  title: "ReguLens — Regulatory Intelligence",
  description:
    "Version-Aware Regulatory Intelligence & Retrieval System for Indian financial regulations. Track RBI circulars, SEBI circulars, amendments, and supersessions with AI-powered provenance.",
  keywords: ["RBI", "SEBI", "regulatory", "compliance", "RAG", "India", "banking"],
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className={inter.variable}>
      <body className="bg-gray-950 text-gray-100 min-h-screen font-sans antialiased">
        <div className="flex min-h-screen">
          <Sidebar />
          <main className="flex-1 ml-64 min-h-screen overflow-auto">{children}</main>
        </div>
      </body>
    </html>
  );
}
