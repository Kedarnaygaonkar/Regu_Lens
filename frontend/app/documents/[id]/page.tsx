import { fetchDocument, fetchDocumentSections, fetchDocumentRelationships } from "@/lib/api";
import { notFound } from "next/navigation";

function StatusBadge({ status }: { status: string }) {
  return <span className={`badge status-${status.toLowerCase()}`}>{status}</span>;
}

export default async function DocumentDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const [doc, sectionsData, lineage] = await Promise.allSettled([
    fetchDocument(id),
    fetchDocumentSections(id),
    fetchDocumentRelationships(id),
  ]);

  if (doc.status === "rejected" || !doc.value) return notFound();
  const document = doc.value;
  const sections = sectionsData.status === "fulfilled" ? sectionsData.value.sections || [] : [];
  const rels = lineage.status === "fulfilled" ? lineage.value : null;

  return (
    <div className="p-8">
      {/* Header */}
      <div className="glass-card p-6 mb-6">
        <div className="flex items-start justify-between">
          <div className="flex-1">
            <div className="flex items-center gap-3 mb-2">
              <StatusBadge status={document.status} />
              <span className="text-sm" style={{ color: "#64748b" }}>
                {document.issuer} · {document.document_type}
              </span>
            </div>
            <h1 className="text-2xl font-black text-white mb-2">{document.title}</h1>
            {document.version && (
              <p className="text-sm font-mono" style={{ color: "#6366f1" }}>
                {document.version}
              </p>
            )}
          </div>
          <div className="text-right text-sm ml-8 space-y-1" style={{ color: "#64748b" }}>
            {document.publication_date && (
              <p>Published: {new Date(document.publication_date).toLocaleDateString("en-IN")}</p>
            )}
            {document.effective_date && (
              <p>Effective: {new Date(document.effective_date).toLocaleDateString("en-IN")}</p>
            )}
            <p>{document.section_count} sections · {document.chunk_count} chunks</p>
          </div>
        </div>
        {document.summary && (
          <div className="mt-4 p-4 rounded-lg" style={{ background: "rgba(99, 102, 241, 0.08)", borderLeft: "3px solid #6366f1" }}>
            <p className="text-sm" style={{ color: "#94a3b8" }}>{document.summary}</p>
          </div>
        )}
      </div>

      {/* Relationships / Supersession */}
      {rels && (rels.supersedes?.length > 0 || rels.superseded_by?.length > 0) && (
        <div className="glass-card p-6 mb-6">
          <h2 className="text-lg font-bold text-white mb-4">Document Lineage</h2>
          {rels.superseded_by?.length > 0 && (
            <div className="mb-4">
              <p className="text-sm font-semibold mb-2" style={{ color: "#ef4444" }}>
                Superseded By:
              </p>
              {rels.superseded_by.map((r: { relationship_id: string; relationship_type: string; source_info: { document_id: string; title: string; status: string; publication_date?: string } }) => (
                <a
                  key={r.relationship_id}
                  href={`/documents/${r.source_info?.document_id}`}
                  className="citation-card block mb-2"
                  style={{ textDecoration: "none" }}
                >
                  <p className="font-semibold text-white text-sm">{r.source_info?.title}</p>
                  <p className="text-xs mt-1" style={{ color: "#64748b" }}>
                    {r.relationship_type}
                    {r.source_info?.publication_date &&
                      ` · ${new Date(r.source_info.publication_date).toLocaleDateString("en-IN")}`}
                  </p>
                </a>
              ))}
            </div>
          )}
          {rels.supersedes?.length > 0 && (
            <div>
              <p className="text-sm font-semibold mb-2" style={{ color: "#10b981" }}>
                Supersedes:
              </p>
              {rels.supersedes.map((r: { relationship_id: string; relationship_type: string; confidence: number; target_info: { document_id: string; title: string; status: string; publication_date?: string } }) => (
                <a
                  key={r.relationship_id}
                  href={`/documents/${r.target_info?.document_id}`}
                  className="citation-card block mb-2"
                  style={{ textDecoration: "none" }}
                >
                  <p className="font-semibold text-white text-sm">{r.target_info?.title}</p>
                  <p className="text-xs mt-1" style={{ color: "#64748b" }}>
                    {r.relationship_type} · confidence: {(r.confidence * 100).toFixed(0)}%
                  </p>
                </a>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Sections */}
      <div className="glass-card p-6">
        <h2 className="text-lg font-bold text-white mb-4">
          Sections ({sections.length})
        </h2>
        {sections.length === 0 ? (
          <p style={{ color: "#64748b" }}>No sections extracted.</p>
        ) : (
          <div className="space-y-3">
            {sections.slice(0, 20).map((sec: { section_id: string; section_number?: string; section_title?: string; page_start?: number; page_end?: number; text: string }) => (
              <div
                key={sec.section_id}
                className="p-4 rounded-lg"
                style={{ background: "rgba(99, 102, 241, 0.05)", border: "1px solid rgba(99, 102, 241, 0.12)" }}
              >
                <div className="flex items-center gap-2 mb-2">
                  {sec.section_number && (
                    <span className="text-xs font-bold px-2 py-0.5 rounded" style={{ background: "rgba(99, 102, 241, 0.2)", color: "#818cf8" }}>
                      §{sec.section_number}
                    </span>
                  )}
                  {sec.section_title && (
                    <p className="font-semibold text-white text-sm">{sec.section_title}</p>
                  )}
                  {sec.page_start && (
                    <span className="ml-auto text-xs" style={{ color: "#64748b" }}>
                      p.{sec.page_start}{sec.page_end && sec.page_end !== sec.page_start ? `–${sec.page_end}` : ""}
                    </span>
                  )}
                </div>
                <p className="text-xs" style={{ color: "#94a3b8", lineHeight: "1.7" }}>
                  {sec.text.substring(0, 300)}
                  {sec.text.length > 300 && "…"}
                </p>
              </div>
            ))}
            {sections.length > 20 && (
              <p className="text-sm text-center" style={{ color: "#64748b" }}>
                …and {sections.length - 20} more sections
              </p>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
