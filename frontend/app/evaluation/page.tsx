"use client";

import { useState, useEffect } from "react";
import { fetchEvaluationCases, fetchEvaluationResults, runEvaluation, seedEvaluationCases } from "@/lib/api";

interface EvalCase {
  case_id: string;
  question: string;
  question_type: string;
  expected_answer: string;
  requires_supersession_reasoning: boolean;
  requires_multiple_documents: boolean;
}

interface Metrics {
  recall_at_k: number;
  precision_at_k: number;
  mrr: number;
  answer_correctness: number;
  citation_accuracy: number;
  supersession_accuracy: number;
  cross_document_accuracy: number;
  latency_ms: number;
}

function MetricBar({ label, value }: { label: string; value: number }) {
  const pct = Math.round(value * 100);
  const color = value >= 0.7 ? "#10b981" : value >= 0.4 ? "#f59e0b" : "#ef4444";
  return (
    <div className="mb-3">
      <div className="flex justify-between text-xs mb-1">
        <span style={{ color: "#94a3b8" }}>{label}</span>
        <span style={{ color }} className="font-bold">{pct}%</span>
      </div>
      <div className="h-2 rounded-full overflow-hidden" style={{ background: "rgba(255,255,255,0.08)" }}>
        <div
          className="h-full rounded-full transition-all duration-700"
          style={{ width: `${pct}%`, background: color }}
        />
      </div>
    </div>
  );
}

const TYPE_COLORS: Record<string, string> = {
  CURRENT_RULE: "#10b981",
  SUPERSESSION: "#ef4444",
  CROSS_DOCUMENT: "#6366f1",
  HISTORICAL: "#8b5cf6",
  SINGLE_DOCUMENT: "#06b6d4",
  CITATION: "#f59e0b",
  TABLE_QUESTION: "#ec4899",
  INSUFFICIENT_EVIDENCE: "#64748b",
  SECTION_RETRIEVAL: "#f97316",
};

export default function EvaluationPage() {
  const [cases, setCases] = useState<EvalCase[]>([]);
  const [results, setResults] = useState<{ regulens?: { metrics: Metrics }; naive_rag?: { metrics: Metrics } }>({});
  const [loading, setLoading] = useState(false);
  const [seeding, setSeeding] = useState(false);
  const [runSystem, setRunSystem] = useState("both");

  useEffect(() => {
    fetchEvaluationCases().then((d) => setCases(d.cases || []));
    loadResults();
  }, []);

  const loadResults = async () => {
    const [rl, nr] = await Promise.allSettled([
      fetchEvaluationResults("regulens"),
      fetchEvaluationResults("naive_rag"),
    ]);
    const res: { regulens?: { metrics: Metrics }; naive_rag?: { metrics: Metrics } } = {};
    if (rl.status === "fulfilled" && rl.value.results?.length > 0) {
      const metrics = rl.value.results.reduce(
        (acc: Metrics, r: { metrics: Metrics }) => {
          acc.recall_at_k += r.metrics.recall_at_k / rl.value.results.length;
          acc.precision_at_k += r.metrics.precision_at_k / rl.value.results.length;
          acc.mrr += r.metrics.mrr / rl.value.results.length;
          acc.answer_correctness += r.metrics.answer_correctness / rl.value.results.length;
          acc.citation_accuracy += r.metrics.citation_accuracy / rl.value.results.length;
          acc.supersession_accuracy += r.metrics.supersession_accuracy / rl.value.results.length;
          acc.cross_document_accuracy += r.metrics.cross_document_accuracy / rl.value.results.length;
          acc.latency_ms += r.metrics.latency_ms / rl.value.results.length;
          return acc;
        },
        { recall_at_k: 0, precision_at_k: 0, mrr: 0, answer_correctness: 0, citation_accuracy: 0, supersession_accuracy: 0, cross_document_accuracy: 0, latency_ms: 0 } as Metrics
      );
      res.regulens = { metrics };
    }
    setResults(res);
  };

  const handleSeed = async () => {
    setSeeding(true);
    await seedEvaluationCases();
    const data = await fetchEvaluationCases();
    setCases(data.cases || []);
    setSeeding(false);
  };

  const handleRun = async () => {
    setLoading(true);
    await runEvaluation(runSystem);
    await loadResults();
    setLoading(false);
  };

  const typeCounts = cases.reduce((acc: Record<string, number>, c) => {
    acc[c.question_type] = (acc[c.question_type] || 0) + 1;
    return acc;
  }, {});

  return (
    <div className="p-8">
      <div className="mb-8">
        <h1 className="text-3xl font-black mb-2">
          <span className="gradient-text">Evaluation Dashboard</span>
        </h1>
        <p style={{ color: "#94a3b8" }}>
          Benchmark ReguLens vs Naive RAG across {cases.length} evaluation cases.
        </p>
      </div>

      {/* Actions */}
      <div className="glass-card p-5 flex items-center gap-4 mb-6">
        <button className="btn-secondary" onClick={handleSeed} disabled={seeding}>
          {seeding ? "Seeding…" : "Seed Evaluation Cases"}
        </button>
        <select
          className="search-input px-4 py-2 text-sm"
          value={runSystem}
          onChange={(e) => setRunSystem(e.target.value)}
        >
          <option value="both">Both Systems</option>
          <option value="regulens">ReguLens Only</option>
          <option value="naive_rag">Naive RAG Only</option>
        </select>
        <button className="btn-primary" onClick={handleRun} disabled={loading}>
          {loading ? "Running…" : "Run Evaluation"}
        </button>
        <p className="text-xs ml-auto" style={{ color: "#64748b" }}>
          {cases.length} cases loaded
        </p>
      </div>

      {/* Metrics comparison */}
      {results.regulens && (
        <div className="grid grid-cols-2 gap-4 mb-6">
          <div className="glass-card p-6">
            <h2 className="font-bold text-white mb-4 flex items-center gap-2">
              <span className="w-3 h-3 rounded-full" style={{ background: "#6366f1" }} />
              ReguLens Metrics
            </h2>
            <MetricBar label="Recall@K" value={results.regulens.metrics.recall_at_k} />
            <MetricBar label="Precision@K" value={results.regulens.metrics.precision_at_k} />
            <MetricBar label="MRR" value={results.regulens.metrics.mrr} />
            <MetricBar label="Answer Correctness" value={results.regulens.metrics.answer_correctness} />
            <MetricBar label="Citation Accuracy" value={results.regulens.metrics.citation_accuracy} />
            <MetricBar label="Supersession Accuracy" value={results.regulens.metrics.supersession_accuracy} />
            <MetricBar label="Cross-Doc Accuracy" value={results.regulens.metrics.cross_document_accuracy} />
            <p className="text-xs mt-2" style={{ color: "#64748b" }}>
              Avg latency: {results.regulens.metrics.latency_ms.toFixed(0)}ms
            </p>
          </div>

          {results.naive_rag ? (
            <div className="glass-card p-6">
              <h2 className="font-bold text-white mb-4 flex items-center gap-2">
                <span className="w-3 h-3 rounded-full" style={{ background: "#64748b" }} />
                Naive RAG Metrics
              </h2>
              <MetricBar label="Recall@K" value={results.naive_rag.metrics.recall_at_k} />
              <MetricBar label="Precision@K" value={results.naive_rag.metrics.precision_at_k} />
              <MetricBar label="MRR" value={results.naive_rag.metrics.mrr} />
              <MetricBar label="Answer Correctness" value={results.naive_rag.metrics.answer_correctness} />
              <MetricBar label="Citation Accuracy" value={results.naive_rag.metrics.citation_accuracy} />
              <MetricBar label="Supersession Accuracy" value={results.naive_rag.metrics.supersession_accuracy} />
              <MetricBar label="Cross-Doc Accuracy" value={results.naive_rag.metrics.cross_document_accuracy} />
            </div>
          ) : (
            <div className="glass-card p-6 text-center" style={{ opacity: 0.5 }}>
              <p style={{ color: "#64748b" }}>Run naive_rag evaluation to compare</p>
            </div>
          )}
        </div>
      )}

      {/* Case breakdown by type */}
      <div className="glass-card p-6 mb-6">
        <h2 className="font-bold text-white mb-4">Cases by Question Type</h2>
        <div className="flex flex-wrap gap-2">
          {Object.entries(typeCounts).map(([type, count]) => (
            <div
              key={type}
              className="px-3 py-2 rounded-lg text-sm"
              style={{
                background: `${TYPE_COLORS[type] || "#64748b"}18`,
                border: `1px solid ${TYPE_COLORS[type] || "#64748b"}30`,
                color: TYPE_COLORS[type] || "#64748b",
              }}
            >
              <span className="font-bold">{count}</span> {type.replace(/_/g, " ")}
            </div>
          ))}
        </div>
      </div>

      {/* Case list */}
      <div className="glass-card p-6">
        <h2 className="font-bold text-white mb-4">Evaluation Cases ({cases.length})</h2>
        <div className="space-y-2">
          {cases.map((c) => (
            <div
              key={c.case_id}
              className="p-4 rounded-lg"
              style={{ background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.06)" }}
            >
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-1">
                    <span className="text-xs font-mono" style={{ color: "#6366f1" }}>{c.case_id}</span>
                    <span
                      className="text-xs px-2 py-0.5 rounded"
                      style={{
                        background: `${TYPE_COLORS[c.question_type] || "#64748b"}18`,
                        color: TYPE_COLORS[c.question_type] || "#64748b",
                      }}
                    >
                      {c.question_type.replace(/_/g, " ")}
                    </span>
                    {c.requires_supersession_reasoning && (
                      <span className="text-xs px-2 py-0.5 rounded" style={{ background: "rgba(239,68,68,0.1)", color: "#ef4444" }}>
                        Supersession
                      </span>
                    )}
                  </div>
                  <p className="text-sm text-white">{c.question}</p>
                  <p className="text-xs mt-1 italic" style={{ color: "#64748b" }}>
                    Expected: {c.expected_answer.substring(0, 80)}
                    {c.expected_answer.length > 80 && "…"}
                  </p>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
