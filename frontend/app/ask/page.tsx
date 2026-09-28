"use client";

import { useState } from "react";
import { ask } from "@/lib/api";

interface Citation {
  document_id: string;
  title: string;
  section?: string;
  page?: number;
  claim_supported: string;
}

interface SupersessionNote {
  description: string;
  source_document_id?: string;
  target_document_id?: string;
}

interface AskResponse {
  question: string;
  answer: string;
  status: string;
  citations: Citation[];
  evidence: Array<{ chunk_id: string; document_title: string; section_number?: string; page_start?: number; text: string; document_status: string; score?: number }>;
  supersession_notes: SupersessionNote[];
  evidence_graph?: { nodes: Array<{ node_id: string; node_type: string; label: string }>; edges: Array<{ from: string; to: string; label: string }> };
  latency_ms: number;
}

function StatusBadge({ status }: { status: string }) {
  const colors: Record<string, string> = {
    CURRENT: "#10b981",
    HISTORICAL: "#6366f1",
    CONFLICTING: "#f59e0b",
    INSUFFICIENT_EVIDENCE: "#ef4444",
  };
  return (
    <span
      className="badge"
      style={{
        color: colors[status] || "#64748b",
        background: `${colors[status] || "#64748b"}18`,
        borderColor: `${colors[status] || "#64748b"}40`,
      }}
    >
      {status.replace(/_/g, " ")}
    </span>
  );
}

const EXAMPLE_QUESTIONS = [
  "What is the current minimum capital adequacy requirement?",
  "Was the 2019 circular superseded?",
  "How did capital requirements change between 2019 and 2024?",
  "Explain the evolution from 2019 to 2024.",
];

export default function AskPage() {
  const [question, setQuestion] = useState("");
  const [response, setResponse] = useState<AskResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [includeSuperseded, setIncludeSuperseded] = useState(false);
  const [activeTab, setActiveTab] = useState<"answer" | "evidence" | "graph">("answer");

  const handleAsk = async (q: string = question) => {
    if (!q.trim()) return;
    setLoading(true);
    setResponse(null);
    setActiveTab("answer");
    try {
      const res = await ask(q, 10, includeSuperseded);
      setResponse(res);
    } catch {
      setResponse(null);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="p-8">
      <div className="mb-8">
        <h1 className="text-3xl font-black mb-2">
          <span className="gradient-text">Ask AI</span>
        </h1>
        <p style={{ color: "#94a3b8" }}>
          Regulatory Q&A with supersession awareness, provenance, and citations.
        </p>
      </div>

      {/* Input */}
      <div className="glass-card p-6 mb-6">
        <textarea
          className="search-input w-full p-4 text-base resize-none mb-4"
          rows={3}
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder="Ask a regulatory question… e.g. 'What is the current capital adequacy requirement?'"
          onKeyDown={(e) => { if (e.key === "Enter" && e.metaKey) handleAsk(); }}
        />
        <div className="flex items-center justify-between">
          <label className="flex items-center gap-2 text-sm cursor-pointer" style={{ color: "#94a3b8" }}>
            <input
              type="checkbox"
              checked={includeSuperseded}
              onChange={(e) => setIncludeSuperseded(e.target.checked)}
              className="accent-indigo-500"
            />
            Include superseded documents
          </label>
          <button
            className="btn-primary px-8 py-3"
            onClick={() => handleAsk()}
            disabled={loading || !question.trim()}
          >
            {loading ? "Reasoning…" : "Ask →"}
          </button>
        </div>

        {/* Examples */}
        <div className="mt-4 flex flex-wrap gap-2">
          {EXAMPLE_QUESTIONS.map((q) => (
            <button
              key={q}
              className="btn-secondary text-xs"
              onClick={() => { setQuestion(q); handleAsk(q); }}
            >
              {q.substring(0, 50)}…
            </button>
          ))}
        </div>
      </div>

      {/* Loading */}
      {loading && (
        <div className="glass-card p-8 text-center">
          <div className="w-12 h-12 border-2 border-indigo-500 border-t-transparent rounded-full mx-auto mb-4 animate-spin" />
          <p className="text-lg font-semibold text-white mb-1">Analyzing regulatory documents…</p>
          <p style={{ color: "#64748b" }}>Performing hybrid retrieval and cross-document reasoning</p>
        </div>
      )}

      {/* Response */}
      {response && (
        <div className="space-y-4 animate-fade-in-up">
          {/* Answer card */}
          <div className="glass-card p-6">
            <div className="flex items-center gap-3 mb-4">
              <StatusBadge status={response.status} />
              <span className="text-xs" style={{ color: "#64748b" }}>
                {response.latency_ms.toFixed(0)}ms · {response.citations.length} citations
              </span>
            </div>
            <div
              className="rounded-xl p-5 mb-4"
              style={{ background: "rgba(99, 102, 241, 0.06)", borderLeft: "3px solid #6366f1" }}
            >
              <p className="text-sm font-semibold mb-2" style={{ color: "#6366f1" }}>
                Question
              </p>
              <p className="text-white">{response.question}</p>
            </div>
            <div
              className="rounded-xl p-5"
              style={{ background: "rgba(16, 185, 129, 0.05)", borderLeft: "3px solid #10b981" }}
            >
              <p className="text-sm font-semibold mb-2" style={{ color: "#10b981" }}>
                Answer
              </p>
              <p className="text-white leading-relaxed whitespace-pre-wrap">{response.answer}</p>
            </div>
          </div>

          {/* Supersession Notes */}
          {response.supersession_notes?.length > 0 && (
            <div className="glass-card p-5">
              <h3 className="font-bold text-white mb-3 flex items-center gap-2">
                <span style={{ color: "#f59e0b" }}>⚠</span> Supersession Notes
              </h3>
              <div className="space-y-2">
                {response.supersession_notes.map((note, i) => (
                  <div
                    key={i}
                    className="p-3 rounded-lg text-sm"
                    style={{ background: "rgba(245, 158, 11, 0.08)", border: "1px solid rgba(245, 158, 11, 0.2)", color: "#fbbf24" }}
                  >
                    {note.description}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Tabs */}
          <div className="glass-card overflow-hidden">
            <div className="flex border-b" style={{ borderColor: "rgba(99, 102, 241, 0.15)" }}>
              {(["answer", "evidence", "graph"] as const).map((tab) => (
                <button
                  key={tab}
                  onClick={() => setActiveTab(tab)}
                  className={`px-6 py-3 text-sm font-semibold transition-all ${
                    activeTab === tab
                      ? "text-indigo-400 border-b-2 border-indigo-500"
                      : "text-gray-400 hover:text-white"
                  }`}
                >
                  {tab.charAt(0).toUpperCase() + tab.slice(1)}
                  {tab === "evidence" && ` (${response.citations.length})`}
                </button>
              ))}
            </div>

            <div className="p-5">
              {activeTab === "answer" && (
                <div className="space-y-3">
                  {response.citations.map((cite, i) => (
                    <div key={i} className="citation-card">
                      <div className="flex items-start justify-between">
                        <div>
                          <a
                            href={`/documents/${cite.document_id}`}
                            className="font-semibold text-sm hover:underline"
                            style={{ color: "#818cf8" }}
                          >
                            {cite.title}
                          </a>
                          {cite.section && (
                            <p className="text-xs mt-0.5" style={{ color: "#64748b" }}>
                              §{cite.section}{cite.page && ` · page ${cite.page}`}
                            </p>
                          )}
                        </div>
                        <span className="text-xs font-bold ml-4" style={{ color: "#6366f1" }}>
                          #{i + 1}
                        </span>
                      </div>
                      <p className="text-xs mt-2 italic" style={{ color: "#94a3b8" }}>
                        {cite.claim_supported}
                      </p>
                    </div>
                  ))}
                  {response.citations.length === 0 && (
                    <p style={{ color: "#64748b" }}>No citations generated.</p>
                  )}
                </div>
              )}

              {activeTab === "evidence" && (
                <div className="space-y-3">
                  {response.evidence?.map((ev, i) => (
                    <div
                      key={ev.chunk_id}
                      className="p-4 rounded-lg"
                      style={{ background: "rgba(99, 102, 241, 0.05)", border: "1px solid rgba(99, 102, 241, 0.12)" }}
                    >
                      <div className="flex items-center justify-between mb-2">
                        <div className="flex items-center gap-2">
                          <span className="text-xs font-bold" style={{ color: "#6366f1" }}>#{i + 1}</span>
                          <a href={`/documents/${ev.document_id}`} className="text-sm font-semibold hover:underline" style={{ color: "#818cf8" }}>
                            {ev.document_title}
                          </a>
                          <span className={`badge status-${ev.document_status.toLowerCase()}`}>{ev.document_status}</span>
                        </div>
                        <span className="text-xs" style={{ color: "#64748b" }}>
                          {ev.section_number && `§${ev.section_number}`}
                          {ev.page_start && ` · p.${ev.page_start}`}
                        </span>
                      </div>
                      <p className="text-xs leading-relaxed" style={{ color: "#94a3b8" }}>
                        {ev.text}
                      </p>
                    </div>
                  ))}
                </div>
              )}

              {activeTab === "graph" && response.evidence_graph && (
                <div>
                  <p className="text-sm font-semibold mb-3 text-white">
                    Evidence Graph ({response.evidence_graph.nodes.length} nodes, {response.evidence_graph.edges.length} edges)
                  </p>
                  <div className="space-y-2">
                    {response.evidence_graph.nodes.map((node) => (
                      <div
                        key={node.node_id}
                        className="flex items-center gap-3 p-3 rounded-lg"
                        style={{
                          background: {
                            question: "rgba(99, 102, 241, 0.1)",
                            document: "rgba(6, 182, 212, 0.08)",
                            chunk: "rgba(16, 185, 129, 0.08)",
                            claim: "rgba(245, 158, 11, 0.08)",
                            answer: "rgba(99, 102, 241, 0.15)",
                          }[node.node_type] || "rgba(255,255,255,0.04)",
                        }}
                      >
                        <span
                          className="text-xs font-bold uppercase px-2 py-0.5 rounded"
                          style={{
                            color: {
                              question: "#6366f1",
                              document: "#06b6d4",
                              chunk: "#10b981",
                              claim: "#f59e0b",
                              answer: "#818cf8",
                            }[node.node_type] || "#64748b",
                            background: "rgba(0,0,0,0.2)",
                          }}
                        >
                          {node.node_type}
                        </span>
                        <p className="text-sm" style={{ color: "#cbd5e1" }}>{node.label}</p>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
