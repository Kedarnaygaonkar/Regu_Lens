"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const navItems = [
  { href: "/", label: "Dashboard", icon: "⬡" },
  { href: "/upload", label: "Upload", icon: "⬆" },
  { href: "/documents", label: "Documents", icon: "◫" },
  { href: "/search", label: "Search", icon: "◎" },
  { href: "/ask", label: "Ask AI", icon: "◈" },
  { href: "/relationships", label: "Relationships", icon: "◇" },
  { href: "/evaluation", label: "Evaluation", icon: "◉" },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside
      className="fixed left-0 top-0 h-full w-64 border-r z-50 flex flex-col"
      style={{
        background: "rgba(3, 7, 18, 0.95)",
        backdropFilter: "blur(20px)",
        borderColor: "rgba(99, 102, 241, 0.15)",
      }}
    >
      {/* Logo */}
      <div className="p-6 border-b" style={{ borderColor: "rgba(99, 102, 241, 0.15)" }}>
        <div className="flex items-center gap-3">
          <div
            className="w-9 h-9 rounded-lg flex items-center justify-center text-white font-black text-lg"
            style={{ background: "linear-gradient(135deg, #6366f1, #06b6d4)" }}
          >
            R
          </div>
          <div>
            <h1 className="font-black text-white text-base tracking-tight">ReguLens</h1>
            <p className="text-xs" style={{ color: "#64748b" }}>
              Regulatory Intelligence
            </p>
          </div>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 p-3 space-y-1 overflow-auto">
        {navItems.map((item) => {
          const isActive = pathname === item.href;
          return (
            <Link
              key={item.href}
              href={item.href}
              className={`sidebar-link ${isActive ? "active" : ""}`}
            >
              <span className="text-base w-5 text-center">{item.icon}</span>
              <span>{item.label}</span>
            </Link>
          );
        })}
      </nav>

      {/* Footer */}
      <div className="p-4 border-t" style={{ borderColor: "rgba(99, 102, 241, 0.15)" }}>
        <div
          className="rounded-lg p-3"
          style={{ background: "rgba(99, 102, 241, 0.08)" }}
        >
          <p className="text-xs font-semibold mb-1" style={{ color: "#6366f1" }}>
            ReguLens v1.0
          </p>
          <p className="text-xs" style={{ color: "#64748b" }}>
            RBI · SEBI · IRDAI
          </p>
        </div>
      </div>
    </aside>
  );
}
