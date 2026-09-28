"use client";

import { useState } from "react";
import { uploadDocument } from "@/lib/api";

export default function UploadPage() {
  const [file, setFile] = useState<File | null>(null);
  const [title, setTitle] = useState("");
  const [issuer, setIssuer] = useState("RBI");
  const [docType, setDocType] = useState("CIRCULAR");
  const [status, setStatus] = useState("UNKNOWN");
  const [pubDate, setPubDate] = useState("");
  const [version, setVersion] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<Record<string, unknown> | null>(null);
  const [error, setError] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file) { setError("Please select a PDF file"); return; }
    if (!title) { setError("Please enter a document title"); return; }
    if (!issuer) { setError("Please enter an issuer"); return; }

    setLoading(true);
    setError("");
    setResult(null);

    const formData = new FormData();
    formData.append("file", file);
    formData.append("title", title);
    formData.append("issuer", issuer);
    formData.append("document_type", docType);
    formData.append("status", status);
    if (pubDate) formData.append("publication_date", pubDate);
    if (version) formData.append("version", version);

    try {
      const res = await uploadDocument(formData);
      if (res.errors && res.errors.length > 0) {
        setError(res.errors.join("; "));
      } else {
        setResult(res);
      }
    } catch (err) {
      setError("Upload failed. Check if the backend is running.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="p-8 max-w-2xl">
      <div className="mb-8">
        <h1 className="text-3xl font-black mb-2">
          <span className="gradient-text">Upload Document</span>
        </h1>
        <p style={{ color: "#94a3b8" }}>
          Ingest a regulatory PDF. The pipeline will extract, chunk, and index the document automatically.
        </p>
      </div>

      <form onSubmit={handleSubmit} className="glass-card p-8 space-y-5">
        {/* File drop */}
        <div>
          <label className="block text-sm font-semibold mb-2" style={{ color: "#94a3b8" }}>
            PDF Document *
          </label>
          <div
            className="border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-all"
            style={{ borderColor: file ? "#6366f1" : "rgba(99, 102, 241, 0.3)" }}
            onClick={() => document.getElementById("file-input")?.click()}
          >
            <input
              id="file-input"
              type="file"
              accept=".pdf"
              className="hidden"
              onChange={(e) => setFile(e.target.files?.[0] || null)}
            />
            {file ? (
              <div>
                <p className="text-2xl mb-2">◫</p>
                <p className="font-semibold text-white">{file.name}</p>
                <p className="text-sm" style={{ color: "#64748b" }}>
                  {(file.size / 1024).toFixed(1)} KB
                </p>
              </div>
            ) : (
              <div>
                <p className="text-4xl mb-3" style={{ color: "#6366f1" }}>⬆</p>
                <p className="font-semibold text-white">Drop PDF here or click to browse</p>
                <p className="text-sm mt-1" style={{ color: "#64748b" }}>
                  Only PDF files are supported
                </p>
              </div>
            )}
          </div>
        </div>

        {/* Title */}
        <div>
          <label className="block text-sm font-semibold mb-2" style={{ color: "#94a3b8" }}>Title *</label>
          <input
            className="search-input w-full px-4 py-3"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="e.g. RBI Circular on Capital Requirements 2024"
          />
        </div>

        {/* Issuer + Type */}
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-semibold mb-2" style={{ color: "#94a3b8" }}>Issuer *</label>
            <select
              className="search-input w-full px-4 py-3"
              value={issuer}
              onChange={(e) => setIssuer(e.target.value)}
            >
              {["RBI", "SEBI", "IRDAI", "PFRDA", "MoF", "Other"].map((o) => (
                <option key={o} value={o}>{o}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-sm font-semibold mb-2" style={{ color: "#94a3b8" }}>Document Type</label>
            <select
              className="search-input w-full px-4 py-3"
              value={docType}
              onChange={(e) => setDocType(e.target.value)}
            >
              {["CIRCULAR", "MASTER_DIRECTION", "NOTIFICATION", "AMENDMENT", "ANNUAL_REPORT", "OTHER"].map((o) => (
                <option key={o} value={o}>{o}</option>
              ))}
            </select>
          </div>
        </div>

        {/* Status + Date */}
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-semibold mb-2" style={{ color: "#94a3b8" }}>Status</label>
            <select
              className="search-input w-full px-4 py-3"
              value={status}
              onChange={(e) => setStatus(e.target.value)}
            >
              {["CURRENT", "SUPERSEDED", "AMENDED", "HISTORICAL", "UNKNOWN"].map((o) => (
                <option key={o} value={o}>{o}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-sm font-semibold mb-2" style={{ color: "#94a3b8" }}>Publication Date</label>
            <input
              type="date"
              className="search-input w-full px-4 py-3"
              value={pubDate}
              onChange={(e) => setPubDate(e.target.value)}
            />
          </div>
        </div>

        {/* Version */}
        <div>
          <label className="block text-sm font-semibold mb-2" style={{ color: "#94a3b8" }}>Version / Reference Number</label>
          <input
            className="search-input w-full px-4 py-3"
            value={version}
            onChange={(e) => setVersion(e.target.value)}
            placeholder="e.g. RBI/2024-25/001"
          />
        </div>

        {error && (
          <div className="rounded-lg p-4" style={{ background: "rgba(239, 68, 68, 0.1)", border: "1px solid rgba(239, 68, 68, 0.3)" }}>
            <p className="text-sm font-semibold text-red-400">{error}</p>
          </div>
        )}

        <button type="submit" className="btn-primary w-full py-3 text-base" disabled={loading}>
          {loading ? "Processing…" : "Upload & Ingest Document"}
        </button>
      </form>

      {result && (
        <div className="mt-6 glass-card p-6 animate-fade-in-up">
          <div className="flex items-center gap-3 mb-4">
            <span className="text-2xl">✓</span>
            <h2 className="text-lg font-bold text-green-400">
              {result.was_duplicate ? "Duplicate Detected — Skipped" : "Ingestion Complete"}
            </h2>
          </div>
          <div className="grid grid-cols-2 gap-3 text-sm">
            <div>
              <p style={{ color: "#64748b" }}>Document ID</p>
              <p className="font-mono font-semibold text-white">{String(result.document_id).substring(0, 16)}…</p>
            </div>
            <div>
              <p style={{ color: "#64748b" }}>Sections Created</p>
              <p className="font-bold text-indigo-400">{String(result.sections_created)}</p>
            </div>
            <div>
              <p style={{ color: "#64748b" }}>Chunks Created</p>
              <p className="font-bold text-indigo-400">{String(result.chunks_created)}</p>
            </div>
            <div>
              <p style={{ color: "#64748b" }}>Time Elapsed</p>
              <p className="font-bold text-cyan-400">{Number(result.elapsed_seconds).toFixed(2)}s</p>
            </div>
          </div>
          <a href={`/documents/${result.document_id}`} className="btn-secondary mt-4 inline-block">
            View Document →
          </a>
        </div>
      )}
    </div>
  );
}
