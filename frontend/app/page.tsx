import { fetchDocuments, fetchHealth } from "@/lib/api";

function StatusBadge({ status }: { status: string }) {
  const cls = `badge status-${status.toLowerCase()}`;
  return <span className={cls}>{status}</span>;
}

function StatCard({
  label,
  value,
  icon,
  color,
}: {
  label: string;
  value: string | number;
  icon: string;
  color: string;
}) {
  return (
    <div className="glass-card p-6 animate-fade-in-up">
      <div className="flex items-start justify-between mb-4">
        <p className="text-sm font-medium" style={{ color: "#94a3b8" }}>
          {label}
        </p>
        <span
          className="text-2xl w-10 h-10 rounded-lg flex items-center justify-center"
          style={{ background: `${color}18`, fontSize: "18px" }}
        >
          {icon}
        </span>
      </div>
      <p className="text-3xl font-black" style={{ color }}>
        {value}
      </p>
    </div>
  );
}

export default async function Dashboard() {
  const [health, docsData] = await Promise.allSettled([
    fetchHealth(),
    fetchDocuments({ limit: 5 }),
  ]);

  const healthOk = health.status === "fulfilled" && health.value?.status === "healthy";
  const docs = docsData.status === "fulfilled" ? docsData.value : { documents: [], total: 0 };

  const statusCounts = docs.documents.reduce(
    (acc: Record<string, number>, doc: { status: string }) => {
      acc[doc.status] = (acc[doc.status] || 0) + 1;
      return acc;
    },
    {}
  );

  return (
    <div className="p-8">
      {/* Header */}
      <div className="mb-10">
        <div className="flex items-center gap-3 mb-3">
          <div
            className="w-2 h-2 rounded-full animate-pulse-glow"
            style={{ background: healthOk ? "#10b981" : "#ef4444" }}
          />
          <span className="text-xs font-semibold uppercase tracking-widest" style={{ color: "#64748b" }}>
            {healthOk ? "System Online" : "System Offline"}
          </span>
        </div>
        <h1 className="text-4xl font-black mb-2">
          <span className="gradient-text">Regulatory Intelligence</span>
        </h1>
        <p className="text-lg" style={{ color: "#94a3b8" }}>
          Version-aware RAG for RBI circulars, SEBI regulations, and Master Directions.
        </p>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-4 gap-4 mb-10">
        <StatCard label="Total Documents" value={docs.total} icon="◫" color="#6366f1" />
        <StatCard label="Current" value={statusCounts.CURRENT || 0} icon="●" color="#10b981" />
        <StatCard label="Superseded" value={statusCounts.SUPERSEDED || 0} icon="✕" color="#ef4444" />
        <StatCard label="DB Status" value={healthOk ? "Connected" : "Error"} icon="◉" color={healthOk ? "#10b981" : "#ef4444"} />
      </div>

      {/* Recent Documents */}
      <div className="glass-card p-6 mb-8">
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-lg font-bold text-white">Recent Documents</h2>
          <a href="/documents" className="btn-secondary">View All →</a>
        </div>
        {docs.documents.length === 0 ? (
          <div className="text-center py-12">
            <p className="text-4xl mb-3">◫</p>
            <p className="text-lg font-semibold mb-1 text-white">No documents yet</p>
            <p style={{ color: "#64748b" }}>
              <a href="/upload" style={{ color: "#6366f1" }}>Upload your first document →</a>
            </p>
          </div>
        ) : (
          <div className="space-y-3">
            {docs.documents.map((doc: { document_id: string; title: string; issuer: string; status: string; publication_date?: string; document_type?: string }) => (
              <a
                key={doc.document_id}
                href={`/documents/${doc.document_id}`}
                className="flex items-center justify-between p-4 rounded-lg transition-all hover:bg-indigo-950/30"
                style={{ border: "1px solid rgba(99, 102, 241, 0.12)" }}
              >
                <div>
                  <p className="font-semibold text-white text-sm">{doc.title}</p>
                  <p className="text-xs mt-1" style={{ color: "#64748b" }}>
                    {doc.issuer} · {doc.document_type} ·{" "}
                    {doc.publication_date ? new Date(doc.publication_date).toLocaleDateString("en-IN") : "No date"}
                  </p>
                </div>
                <StatusBadge status={doc.status} />
              </a>
            ))}
          </div>
        )}
      </div>

      {/* Quick Actions */}
      <div className="grid grid-cols-3 gap-4">
        {[
          { href: "/upload", icon: "⬆", title: "Upload Document", desc: "Ingest a new regulatory PDF" },
          { href: "/ask", icon: "◈", title: "Ask AI", desc: "Query with supersession awareness" },
          { href: "/search", icon: "◎", title: "Hybrid Search", desc: "Vector + keyword retrieval" },
        ].map((action) => (
          <a
            key={action.href}
            href={action.href}
            className="glass-card p-5 block hover:scale-105 transition-transform"
            style={{ textDecoration: "none" }}
          >
            <p className="text-3xl mb-3">{action.icon}</p>
            <p className="font-bold text-white text-sm mb-1">{action.title}</p>
            <p className="text-xs" style={{ color: "#64748b" }}>
              {action.desc}
            </p>
          </a>
        ))}
      </div>
    </div>
  );
}
