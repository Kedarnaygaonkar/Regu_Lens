"use client";

import { useState } from "react";
import { search } from "@/lib/api";

interface ChunkResult {
  chunk_id: string;
  document_id: string;
  document_title?: string;
  document_issuer?: string;
  section_number?: string;
  section_title?: string;
  page_start?: number;
  text: string;
  document_status: string;
  hybrid_score?: number;
  vector_score?: number;
  keyword_score?: number;
}

function StatusBadge({ status }: { status: string }) {
  return <span className={`badge status-${status.toLowerCase()}`}>{status}</span>;
}

export default function SearchPage() {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<ChunkResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [latency, setLatency] = useState(0);
  const [includeSuperseded, setIncludeSuperseded] = useState(false);
  const [searched, setSearched] = useState(false);

  const handleSearch = async (q: string = query) => {
    if (!q.trim()) return;
    setLoading(true);
    setSearched(true);
    try {
      const res = await search(q, 15, includeSuperseded);
      setResults(res.results || []);
      setLatency(res.latency_ms || 0);
    } catch {
      setResults([]);
    } finally {
      setLoading(false);
    }
  };

  const EXAMPLE_QUERIES = [
    "capital adequacy ratio requirements",
    "supersession of earlier circulars",
    "reporting obligations banks",
    "effective date compliance",
  ];

  return (
    <div className="p-8">
      <div className="mb-8">
        <h1 className="text-3xl font-black mb-2">
          <span className="gradient-text">Hybrid Search</span>
        </h1>
        <p style={{ color: "#94a3b8" }}>
          Vector + keyword retrieval across all indexed regulatory documents.
        </p>
      </div>

      {/* Search bar */}
      <div className="flex gap-3 mb-6">
        <input
          className="search-input flex-1 px-5 py-4 text-base"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search regulatory content…"
          onKeyDown={(e) => e.key === "Enter" && handleSearch()}
        />
        <label className="flex items-center gap-2 text-sm cursor-pointer" style={{ color: "#94a3b8" }}>
          <input
            type="checkbox"
            checked={includeSuperseded}
            onChange={(e) => setIncludeSuperseded(e.target.checked)}
            className="accent-indigo-500"
          />
          Include superseded
        </label>
        <button className="btn-primary px-8" onClick={() => handleSearch()} disabled={loading}>
          {loading ? "Searching…" : "Search"}
        </button>
      </div>

      {/* Example queries */}
      {!searched && (
        <div className="mb-8">
          <p className="text-xs uppercase tracking-widest mb-3" style={{ color: "#64748b" }}>
            Example searches
          </p>
          <div className="flex flex-wrap gap-2">
            {EXAMPLE_QUERIES.map((q) => (
              <button
                key={q}
                className="btn-secondary"
                onClick={() => { setQuery(q); handleSearch(q); }}
              >
                {q}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Results */}
      {searched && !loading && (
        <div>
          <div className="flex items-center justify-between mb-4">
            <p className="text-sm" style={{ color: "#64748b" }}>
              {results.length} results in {latency.toFixed(0)}ms
            </p>
          </div>

          {results.length === 0 ? (
            <div className="glass-card p-12 text-center">
              <p className="text-4xl mb-3">◎</p>
              <p className="text-lg font-bold text-white mb-1">No results found</p>
              <p style={{ color: "#64748b" }}>Try different keywords or upload more documents</p>
            </div>
          ) : (
            <div className="space-y-4">
              {results.map((result, idx) => (
                <div
                  key={result.chunk_id}
                  className="glass-card p-5 animate-fade-in-up"
                  style={{ animationDelay: `${idx * 30}ms` }}
                >
                  <div className="flex items-start justify-between mb-3">
                    <div className="flex-1">
                      <div className="flex items-center gap-2 flex-wrap">
                        <a
                          href={`/documents/${result.document_id}`}
                          className="font-semibold text-sm hover:underline"
                          style={{ color: "#818cf8" }}
                        >
                          {result.document_title || result.document_id}
                        </a>
                        <StatusBadge status={result.document_status} />
                      </div>
                      {(result.section_number || result.section_title) && (
                        <p className="text-xs mt-1" style={{ color: "#64748b" }}>
                          {result.section_number && `§${result.section_number}`}
                          {result.section_title && ` · ${result.section_title}`}
                          {result.page_start && ` · p.${result.page_start}`}
                        </p>
                      )}
                    </div>
                    <div className="text-right text-xs ml-4" style={{ color: "#64748b" }}>
                      <p className="font-bold" style={{ color: "#6366f1" }}>
                        Score: {((result.hybrid_score || result.vector_score || 0) * 100).toFixed(0)}
                      </p>
                      <p>#{idx + 1}</p>
                    </div>
                  </div>
                  <p className="text-sm leading-relaxed" style={{ color: "#cbd5e1" }}>
                    {result.text.substring(0, 400)}
                    {result.text.length > 400 && "…"}
                  </p>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {loading && (
        <div className="space-y-4">
          {[1, 2, 3].map((i) => (
            <div key={i} className="glass-card p-5">
              <div className="skeleton h-4 w-1/3 mb-3" />
              <div className="skeleton h-3 w-full mb-2" />
              <div className="skeleton h-3 w-4/5" />
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
