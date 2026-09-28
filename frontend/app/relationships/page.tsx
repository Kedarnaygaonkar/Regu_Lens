"use client";

import { useState, useEffect } from "react";
import { fetchDocuments, fetchDocumentRelationships } from "@/lib/api";

interface Doc {
  document_id: string;
  title: string;
  status: string;
  issuer?: string;
}

interface Relationship {
  relationship_id: string;
  relationship_type: string;
  source_document_id: string;
  target_document_id: string;
  confidence: number;
  evidence?: string[];
}

function StatusBadge({ status }: { status: string }) {
  return <span className={`badge status-${status.toLowerCase()}`}>{status}</span>;
}

const REL_TYPE_COLORS: Record<string, string> = {
  SUPERSEDES: "#ef4444",
  AMENDS: "#f59e0b",
  PARTIALLY_AMENDS: "#f97316",
  CONSOLIDATES: "#8b5cf6",
  REPLACES: "#ec4899",
  CLARIFIES: "#06b6d4",
  REFERENCES: "#64748b",
};

export default function RelationshipsPage() {
  const [docs, setDocs] = useState<Doc[]>([]);
  const [selectedDoc, setSelectedDoc] = useState<string>("");
  const [lineage, setLineage] = useState<{ supersedes: Relationship[]; superseded_by: Relationship[] } | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    fetchDocuments({ limit: 50 }).then((data) => setDocs(data.documents || []));
  }, []);

  const loadLineage = async (docId: string) => {
    setSelectedDoc(docId);
    setLoading(true);
    try {
      const data = await fetchDocumentRelationships(docId);
      setLineage(data);
    } finally {
      setLoading(false);
    }
  };

  const docMap = new Map<string, Doc>(docs.map((d) => [d.document_id, d]));

  return (
    <div className="p-8">
      <div className="mb-8">
        <h1 className="text-3xl font-black mb-2">
          <span className="gradient-text">Document Relationships</span>
        </h1>
        <p style={{ color: "#94a3b8" }}>
          Explore the supersession graph — how circulars amend and supersede each other.
        </p>
      </div>

      <div className="grid grid-cols-3 gap-6">
        {/* Document selector */}
        <div className="glass-card p-5">
          <h2 className="font-bold text-white mb-4">Select Document</h2>
          <div className="space-y-2">
            {docs.length === 0 && (
              <p className="text-sm" style={{ color: "#64748b" }}>No documents found. Upload some first.</p>
            )}
            {docs.map((doc) => (
              <button
                key={doc.document_id}
                onClick={() => loadLineage(doc.document_id)}
                className={`w-full text-left p-3 rounded-lg transition-all text-sm ${
                  selectedDoc === doc.document_id
                    ? "bg-indigo-500/20 border border-indigo-500/40"
                    : "hover:bg-white/5"
                }`}
              >
                <p className="font-semibold text-white">{doc.title.substring(0, 50)}</p>
                <StatusBadge status={doc.status} />
              </button>
            ))}
          </div>
        </div>

        {/* Lineage view */}
        <div className="col-span-2">
          {loading && (
            <div className="glass-card p-12 text-center">
              <div className="w-10 h-10 border-2 border-indigo-500 border-t-transparent rounded-full mx-auto mb-3 animate-spin" />
              <p style={{ color: "#64748b" }}>Loading relationships…</p>
            </div>
          )}

          {!loading && !lineage && (
            <div className="glass-card p-12 text-center">
              <p className="text-4xl mb-3">◇</p>
              <p className="text-lg font-bold text-white mb-1">Select a document</p>
              <p style={{ color: "#64748b" }}>Choose a document to view its relationship graph</p>
            </div>
          )}

          {!loading && lineage && (
            <div className="space-y-4">
              {/* Current doc */}
              <div className="glass-card p-5" style={{ borderColor: "rgba(99, 102, 241, 0.4)" }}>
                <div className="flex items-center gap-2 mb-1">
                  <span className="w-3 h-3 rounded-full" style={{ background: "#6366f1" }} />
                  <p className="text-xs uppercase font-bold" style={{ color: "#6366f1" }}>Selected Document</p>
                </div>
                <p className="font-bold text-white">{docMap.get(selectedDoc)?.title || selectedDoc}</p>
                {docMap.get(selectedDoc) && <StatusBadge status={docMap.get(selectedDoc)!.status} />}
              </div>

              {/* Superseded By */}
              {lineage.superseded_by?.length > 0 && (
                <div className="glass-card p-5">
                  <h3 className="font-bold mb-4 flex items-center gap-2" style={{ color: "#ef4444" }}>
                    <span>↑</span> Superseded By ({lineage.superseded_by.length})
                  </h3>
                  <div className="space-y-3">
                    {lineage.superseded_by.map((rel: { relationship_id: string; relationship_type: string; source_document_id: string; confidence: number; evidence?: string[] }) => {
                      const relColor = REL_TYPE_COLORS[rel.relationship_type] || "#64748b";
                      const doc = docMap.get(rel.source_document_id);
                      return (
                        <div
                          key={rel.relationship_id}
                          className="p-4 rounded-lg"
                          style={{ background: `${relColor}0a`, border: `1px solid ${relColor}30` }}
                        >
                          <div className="flex items-center justify-between mb-2">
                            <div>
                              <a
                                href={`/documents/${rel.source_document_id}`}
                                className="font-semibold text-white text-sm hover:underline"
                              >
                                {doc?.title || rel.source_document_id}
                              </a>
                              {doc && <StatusBadge status={doc.status} />}
                            </div>
                            <div className="text-right">
                              <span
                                className="text-xs font-bold uppercase"
                                style={{ color: relColor }}
                              >
                                {rel.relationship_type}
                              </span>
                              <p className="text-xs" style={{ color: "#64748b" }}>
                                conf: {(rel.confidence * 100).toFixed(0)}%
                              </p>
                            </div>
                          </div>
                          {rel.evidence?.[0] && (
                            <p className="text-xs italic" style={{ color: "#94a3b8" }}>
                              &ldquo;{rel.evidence[0].substring(0, 150)}…&rdquo;
                            </p>
                          )}
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}

              {/* Supersedes */}
              {lineage.supersedes?.length > 0 && (
                <div className="glass-card p-5">
                  <h3 className="font-bold mb-4 flex items-center gap-2" style={{ color: "#10b981" }}>
                    <span>↓</span> Supersedes ({lineage.supersedes.length})
                  </h3>
                  <div className="space-y-3">
                    {lineage.supersedes.map((rel: { relationship_id: string; relationship_type: string; target_document_id: string; confidence: number; evidence?: string[] }) => {
                      const relColor = REL_TYPE_COLORS[rel.relationship_type] || "#64748b";
                      const doc = docMap.get(rel.target_document_id);
                      return (
                        <div
                          key={rel.relationship_id}
                          className="p-4 rounded-lg"
                          style={{ background: `${relColor}0a`, border: `1px solid ${relColor}30` }}
                        >
                          <div className="flex items-center justify-between mb-2">
                            <div>
                              <a
                                href={`/documents/${rel.target_document_id}`}
                                className="font-semibold text-white text-sm hover:underline"
                              >
                                {doc?.title || rel.target_document_id}
                              </a>
                              {doc && <StatusBadge status={doc.status} />}
                            </div>
                            <div className="text-right">
                              <span className="text-xs font-bold uppercase" style={{ color: relColor }}>
                                {rel.relationship_type}
                              </span>
                              <p className="text-xs" style={{ color: "#64748b" }}>
                                conf: {(rel.confidence * 100).toFixed(0)}%
                              </p>
                            </div>
                          </div>
                          {rel.evidence?.[0] && (
                            <p className="text-xs italic" style={{ color: "#94a3b8" }}>
                              &ldquo;{rel.evidence[0].substring(0, 150)}…&rdquo;
                            </p>
                          )}
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}

              {lineage.supersedes?.length === 0 && lineage.superseded_by?.length === 0 && (
                <div className="glass-card p-8 text-center">
                  <p style={{ color: "#64748b" }}>No relationships defined for this document yet.</p>
                  <p className="text-sm mt-1" style={{ color: "#64748b" }}>
                    Use POST /documents/&#123;id&#125;/relationships to add relationships.
                  </p>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
