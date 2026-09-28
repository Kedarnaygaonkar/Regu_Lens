import { fetchDocuments } from "@/lib/api";
import Link from "next/link";

function StatusBadge({ status }: { status: string }) {
  return (
    <span className={`badge status-${status.toLowerCase()}`}>{status}</span>
  );
}

export default async function DocumentsPage({
  searchParams,
}: {
  searchParams: Promise<{ status?: string; issuer?: string }>;
}) {
  const params = await searchParams;
  const data = await fetchDocuments({ status: params.status, issuer: params.issuer, limit: 50 });
  const docs = data.documents || [];

  return (
    <div className="p-8">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-3xl font-black mb-1">
            <span className="gradient-text">Document Library</span>
          </h1>
          <p style={{ color: "#94a3b8" }}>
            {data.total} regulatory documents indexed
          </p>
        </div>
        <Link href="/upload" className="btn-primary">+ Upload Document</Link>
      </div>

      {/* Filters */}
      <div className="glass-card p-4 mb-6 flex gap-3">
        {["", "CURRENT", "SUPERSEDED", "AMENDED", "HISTORICAL"].map((s) => (
          <Link
            key={s}
            href={s ? `/documents?status=${s}` : "/documents"}
            className={`px-4 py-2 rounded-lg text-sm font-semibold transition-all ${
              params.status === s || (!params.status && !s)
                ? "bg-indigo-500/20 text-indigo-400 border border-indigo-500/30"
                : "text-gray-400 hover:text-white"
            }`}
          >
            {s || "All"}
          </Link>
        ))}
      </div>

      {docs.length === 0 ? (
        <div className="glass-card p-16 text-center">
          <p className="text-5xl mb-4">◫</p>
          <p className="text-xl font-bold text-white mb-2">No documents found</p>
          <p style={{ color: "#64748b" }}>
            <Link href="/upload" style={{ color: "#6366f1" }}>Upload your first regulatory document →</Link>
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          {docs.map((doc: { document_id: string; title: string; issuer: string; document_type: string; status: string; publication_date?: string; version?: string; section_count?: number; chunk_count?: number }) => (
            <Link
              key={doc.document_id}
              href={`/documents/${doc.document_id}`}
              className="glass-card p-5 flex items-center justify-between hover:scale-[1.005] transition-transform block"
              style={{ textDecoration: "none" }}
            >
              <div className="flex-1">
                <div className="flex items-center gap-3 mb-1">
                  <p className="font-bold text-white">{doc.title}</p>
                  <StatusBadge status={doc.status} />
                </div>
                <p className="text-sm" style={{ color: "#64748b" }}>
                  {doc.issuer} · {doc.document_type}
                  {doc.version && ` · ${doc.version}`}
                  {doc.publication_date && ` · ${new Date(doc.publication_date).toLocaleDateString("en-IN")}`}
                </p>
              </div>
              <div className="text-right text-xs ml-6" style={{ color: "#64748b" }}>
                {doc.section_count !== undefined && (
                  <>
                    <p>{doc.section_count} sections</p>
                    <p>{doc.chunk_count} chunks</p>
                  </>
                )}
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
