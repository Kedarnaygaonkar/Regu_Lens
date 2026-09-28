// API client for ReguLens backend

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export async function fetchHealth() {
  const res = await fetch(`${API_BASE}/health`);
  return res.json();
}

export async function fetchDocuments(params?: {
  status?: string;
  issuer?: string;
  skip?: number;
  limit?: number;
}) {
  const url = new URL(`${API_BASE}/documents`);
  if (params?.status) url.searchParams.set("status", params.status);
  if (params?.issuer) url.searchParams.set("issuer", params.issuer);
  if (params?.skip !== undefined) url.searchParams.set("skip", String(params.skip));
  if (params?.limit !== undefined) url.searchParams.set("limit", String(params.limit));
  const res = await fetch(url.toString(), { cache: "no-store" });
  return res.json();
}

export async function fetchDocument(id: string) {
  const res = await fetch(`${API_BASE}/documents/${id}`, { cache: "no-store" });
  if (!res.ok) return null;
  return res.json();
}

export async function fetchDocumentSections(id: string) {
  const res = await fetch(`${API_BASE}/documents/${id}/sections`, { cache: "no-store" });
  return res.json();
}

export async function fetchDocumentRelationships(id: string) {
  const res = await fetch(`${API_BASE}/documents/${id}/relationships`, { cache: "no-store" });
  return res.json();
}

export async function search(query: string, topK = 10, includeSuperseded = false) {
  const res = await fetch(`${API_BASE}/search`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ query, top_k: topK, include_superseded: includeSuperseded }),
  });
  return res.json();
}

export async function ask(question: string, topK = 10, includeSuperseded = false) {
  const res = await fetch(`${API_BASE}/ask`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      question,
      top_k: topK,
      include_superseded: includeSuperseded,
      use_cross_document_reasoning: true,
    }),
  });
  return res.json();
}

export async function uploadDocument(formData: FormData) {
  const res = await fetch(`${API_BASE}/documents/upload`, {
    method: "POST",
    body: formData,
  });
  return res.json();
}

export async function fetchEvaluationCases() {
  const res = await fetch(`${API_BASE}/evaluation/cases`, { cache: "no-store" });
  return res.json();
}

export async function fetchEvaluationResults(systemName?: string) {
  const url = new URL(`${API_BASE}/evaluation/results`);
  if (systemName) url.searchParams.set("system_name", systemName);
  const res = await fetch(url.toString(), { cache: "no-store" });
  return res.json();
}

export async function runEvaluation(system: string) {
  const res = await fetch(`${API_BASE}/evaluation/run`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ system }),
  });
  return res.json();
}

export async function seedEvaluationCases() {
  const res = await fetch(`${API_BASE}/evaluation/cases/seed`, { method: "POST" });
  return res.json();
}
