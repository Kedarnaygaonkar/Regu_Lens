"""
RAG Answer Generator for ReguLens.

The LLM receives structured evidence and must:
  - Answer only from supplied evidence
  - Never invent citations
  - Distinguish current vs historical rules
  - Explicitly mention supersession
  - Explain conflicts
  - State when evidence is insufficient
  - Cite exact documents, sections, and page numbers

Supports:
  - OpenAI (gpt-4o, gpt-4-turbo)
  - Google Gemini (gemini-1.5-pro)
"""
from __future__ import annotations

import json
import logging
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

from app.config import get_settings
from app.database import Collections, get_sync_db
from app.detection.supersession_engine import get_document_lineage
from app.models.query import (
    AskRequest, AskResponse, AnswerStatus,
    Citation, SupersessionNote, QueryLog, EvidenceGraph
)
from app.rag.evidence_graph import build_evidence_graph
from app.rag.query_decomposer import decompose_query
from app.retrieval.hybrid_retriever import hybrid_retrieve

logger = logging.getLogger(__name__)

# ─── System prompt ─────────────────────────────────────────────────────────────
SYSTEM_PROMPT = """You are ReguLens, an expert regulatory intelligence assistant for Indian financial regulations.

Your role is to answer questions about RBI circulars, SEBI circulars, Master Directions, policy documents, and other regulatory instruments.

STRICT RULES:
1. ONLY answer based on the EVIDENCE provided to you. Never use external knowledge.
2. If the evidence is insufficient, explicitly state: "Insufficient evidence to determine the answer."
3. ALWAYS distinguish between CURRENT rules and HISTORICAL rules.
4. If a document has been SUPERSEDED or AMENDED, clearly state this.
5. When there is a conflict between documents, explain the conflict and state which is authoritative.
6. ALWAYS cite the specific document, section number, and page where possible.
7. NEVER invent citations, document names, or regulatory facts.
8. If multiple versions exist, clearly explain the evolution (e.g., 10% → 15% → 20%).

OUTPUT FORMAT: You must respond with a valid JSON object with this structure:
{
  "answer": "Your detailed answer here",
  "status": "CURRENT|HISTORICAL|CONFLICTING|INSUFFICIENT_EVIDENCE",
  "citations": [
    {
      "document_id": "...",
      "title": "Document title",
      "section": "Section number and title",
      "page": 18,
      "claim_supported": "Brief description of what this citation supports"
    }
  ],
  "supersession_notes": [
    {
      "description": "Description of supersession",
      "source_document_id": "...",
      "target_document_id": "..."
    }
  ]
}
"""


def _format_evidence(chunks: List[Dict[str, Any]]) -> str:
    """Format retrieved chunks as structured evidence for the LLM."""
    if not chunks:
        return "No evidence retrieved."

    parts = []
    for i, chunk in enumerate(chunks, 1):
        doc_status = chunk.get("document_status", "UNKNOWN")
        section = chunk.get("section_number", "")
        sec_title = chunk.get("section_title", "")
        section_str = f"§{section} {sec_title}".strip() if section else ""
        page_str = f"p.{chunk.get('page_start', '?')}" if chunk.get("page_start") else ""

        pub_date = chunk.get("publication_date") or chunk.get("document_effective_date")
        date_str = ""
        if pub_date:
            if isinstance(pub_date, datetime):
                date_str = pub_date.strftime("%Y-%m-%d")
            else:
                date_str = str(pub_date)[:10]

        parts.append(
            f"[EVIDENCE {i}]\n"
            f"Document: {chunk.get('document_title', 'Unknown')} "
            f"(ID: {chunk.get('document_id', 'N/A')})\n"
            f"Status: {doc_status}\n"
            f"Section: {section_str}\n"
            f"Page: {page_str}\n"
            f"Date: {date_str}\n"
            f"Text:\n{chunk.get('text', '')}\n"
            f"{'─' * 60}"
        )

    return "\n\n".join(parts)


def _call_openai(
    question: str,
    evidence_text: str,
    supersession_context: str,
    api_key: str,
    model: str,
) -> str:
    """Call OpenAI API for answer generation."""
    from openai import OpenAI

    client = OpenAI(api_key=api_key)
    user_message = (
        f"QUESTION: {question}\n\n"
        f"SUPERSESSION CONTEXT:\n{supersession_context}\n\n"
        f"EVIDENCE:\n{evidence_text}\n\n"
        "Based ONLY on the above evidence, answer the question. "
        "Output valid JSON as specified."
    )

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ],
        temperature=0.1,
        response_format={"type": "json_object"},
    )
    return response.choices[0].message.content


def _call_gemini(
    question: str,
    evidence_text: str,
    supersession_context: str,
    api_key: str,
    model: str,
) -> str:
    """Call Google Gemini API for answer generation with automatic fallback cascade."""
    import google.generativeai as genai

    genai.configure(api_key=api_key)
    prompt = (
        f"{SYSTEM_PROMPT}\n\n"
        f"QUESTION: {question}\n\n"
        f"SUPERSESSION CONTEXT:\n{supersession_context}\n\n"
        f"EVIDENCE:\n{evidence_text}\n\n"
        "Based ONLY on the above evidence, answer the question. "
        "Output valid JSON as specified."
    )

    # Build model cascade list: configured model first, followed by fallbacks
    candidates = [model]
    for fb in ["gemini-2.5-flash", "gemini-2.5-flash-lite", "gemini-3.5-flash", "gemini-3.8-flash"]:
        if fb not in candidates:
            candidates.append(fb)

    last_error = None
    for cand in candidates:
        try:
            gemini_model = genai.GenerativeModel(cand)
            response = gemini_model.generate_content(prompt)
            if cand != model:
                logger.info(f"Fallback to model '{cand}' succeeded.")
            return response.text
        except Exception as e:
            last_error = e
            err_msg = str(e)
            if "429" in err_msg or "ResourceExhausted" in err_msg:
                logger.warning(f"Gemini model '{cand}' quota exceeded (429). Trying fallback...")
                continue
            elif "404" in err_msg:
                logger.warning(f"Gemini model '{cand}' not found (404). Trying fallback...")
                continue
            else:
                logger.error(f"Error calling Gemini model '{cand}': {e}")
                break

    # If all models hit quota or failed, provide a graceful structured answer with retrieved evidence
    logger.error(f"All Gemini models exhausted or failed: {last_error}")
    return json.dumps({
        "answer": (
            "The Gemini API free-tier quota is currently exhausted for this API key. "
            "However, relevant regulatory evidence was successfully retrieved from the database. "
            "Please check the Evidence and Citations tabs below to view the indexed provisions."
        ),
        "status": "INSUFFICIENT_EVIDENCE",
        "citations": [],
        "supersession_notes": [
            {
                "description": f"AI Generation Notice: Gemini free-tier quota limit reached ({last_error}). Evidence retrieved from local Atlas index."
            }
        ],
    })


def _parse_llm_response(raw: str) -> Dict[str, Any]:
    """Parse LLM JSON response, with fallback."""
    try:
        # Remove markdown code fences if present
        raw = raw.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        return json.loads(raw)
    except Exception as e:
        logger.warning(f"Failed to parse LLM response as JSON: {e}")
        return {
            "answer": raw,
            "status": "INSUFFICIENT_EVIDENCE",
            "citations": [],
            "supersession_notes": [],
        }


def _build_supersession_context(retrieved_chunks: List[Dict[str, Any]]) -> str:
    """Build a concise supersession context from retrieved document lineages."""
    db = get_sync_db()
    doc_ids = list(set(c.get("document_id") for c in retrieved_chunks if c.get("document_id")))
    
    if not doc_ids:
        return "No supersession information available."

    rels_col = db[Collections.DOCUMENT_RELATIONSHIPS]
    relevant_rels = list(rels_col.find({
        "$or": [
            {"source_document_id": {"$in": doc_ids}},
            {"target_document_id": {"$in": doc_ids}},
        ]
    }, {"_id": 0}))

    if not relevant_rels:
        return "No supersession relationships found for retrieved documents."

    lines = []
    for rel in relevant_rels:
        lines.append(
            f"- {rel.get('source_document_id', 'N/A')} "
            f"--[{rel.get('relationship_type', '?')}]--> "
            f"{rel.get('target_document_id', 'N/A')} "
            f"(confidence: {rel.get('confidence', 0):.2f})"
        )
        for ev in rel.get("evidence", [])[:1]:
            lines.append(f"  Evidence: {ev[:200]}")

    return "\n".join(lines)


class AnswerGenerator:
    """Main RAG answer generator."""

    def __init__(self, embedding_provider=None):
        self.embedding_provider = embedding_provider
        self.settings = get_settings()

    def answer(self, request: AskRequest) -> AskResponse:
        """
        Generate a provenance-rich answer to a regulatory question.
        """
        start_time = time.time()

        # ── 1. Decompose query ────────────────────────────────────────────────
        decomposed = decompose_query(request.question)
        logger.info(
            f"Query type: {decomposed.reasoning_type}, "
            f"cross-doc: {decomposed.is_cross_document}, "
            f"subqueries: {len(decomposed.subqueries)}"
        )

        # ── 2. Retrieve evidence for each sub-query ───────────────────────────
        all_chunks: List[Dict[str, Any]] = []
        seen_chunk_ids = set()

        for subq in decomposed.subqueries:
            query_embedding = []
            if self.embedding_provider:
                try:
                    query_embedding = self.embedding_provider.embed_query(subq.query)
                except Exception as e:
                    logger.warning(f"Embedding failed for sub-query: {e}")

            results = hybrid_retrieve(
                query=subq.query,
                query_embedding=query_embedding,
                top_k=request.top_k,
                filters=request.filters or subq.filters,
                include_superseded=request.include_superseded,
            )

            for chunk in results:
                if chunk["chunk_id"] not in seen_chunk_ids:
                    seen_chunk_ids.add(chunk["chunk_id"])
                    all_chunks.append(chunk)

        # ── 3. If no results found ────────────────────────────────────────────
        if not all_chunks:
            elapsed = (time.time() - start_time) * 1000
            return AskResponse(
                question=request.question,
                answer="Insufficient evidence to determine the answer. No relevant documents were found.",
                status=AnswerStatus.INSUFFICIENT_EVIDENCE,
                citations=[],
                latency_ms=elapsed,
            )

        # ── 4. Build supersession context ─────────────────────────────────────
        supersession_context = _build_supersession_context(all_chunks)

        # ── 5. Format evidence ────────────────────────────────────────────────
        evidence_text = _format_evidence(all_chunks[:15])  # Cap at 15 chunks

        # ── 6. Call LLM ───────────────────────────────────────────────────────
        raw_response = self._call_llm(request.question, evidence_text, supersession_context)
        parsed = _parse_llm_response(raw_response)

        # ── 7. Build structured response ──────────────────────────────────────
        citations = []
        for c in parsed.get("citations", []):
            citations.append(Citation(
                document_id=c.get("document_id", ""),
                title=c.get("title", ""),
                section=c.get("section", ""),
                page=c.get("page"),
                claim_supported=c.get("claim_supported", ""),
            ))

        supersession_notes = []
        for sn in parsed.get("supersession_notes", []):
            supersession_notes.append(SupersessionNote(
                description=sn.get("description", ""),
                source_document_id=sn.get("source_document_id"),
                target_document_id=sn.get("target_document_id"),
            ))

        # Parse status
        status_str = parsed.get("status", "INSUFFICIENT_EVIDENCE")
        try:
            status = AnswerStatus(status_str)
        except ValueError:
            status = AnswerStatus.INSUFFICIENT_EVIDENCE

        # ── 8. Build evidence graph ───────────────────────────────────────────
        subquery_texts = [sq.query for sq in decomposed.subqueries]
        evidence_graph = build_evidence_graph(
            question=request.question,
            retrieved_chunks=all_chunks,
            citations=[c.model_dump() for c in citations],
            subqueries=subquery_texts,
        )

        elapsed = (time.time() - start_time) * 1000

        # ── 9. Log the query ──────────────────────────────────────────────────
        self._log_query(request.question, all_chunks, parsed.get("answer", ""), citations, elapsed)

        return AskResponse(
            question=request.question,
            answer=parsed.get("answer", "No answer generated."),
            status=status,
            citations=citations,
            evidence=[{
                "chunk_id": c.get("chunk_id"),
                "document_id": c.get("document_id"),
                "document_title": c.get("document_title", ""),
                "section_number": c.get("section_number", ""),
                "section_title": c.get("section_title", ""),
                "page_start": c.get("page_start"),
                "document_status": c.get("document_status", ""),
                "text": c.get("text", "")[:300],
                "score": c.get("hybrid_score", c.get("vector_score", 0.0)),
            } for c in all_chunks[:10]],
            related_documents=self._get_related_docs(all_chunks),
            supersession_notes=supersession_notes,
            evidence_graph=evidence_graph,
            latency_ms=elapsed,
            retrieved_chunk_ids=list(seen_chunk_ids),
        )

    def _call_llm(self, question: str, evidence_text: str, supersession_context: str) -> str:
        """Dispatch to the configured LLM provider."""
        settings = self.settings

        if not settings.llm_api_key:
            logger.warning("LLM_API_KEY not set; returning mock answer")
            return json.dumps({
                "answer": f"[Mock answer — LLM not configured] Evidence retrieved for: {question}",
                "status": "INSUFFICIENT_EVIDENCE",
                "citations": [],
                "supersession_notes": [],
            })

        provider = settings.llm_provider.lower()
        if provider == "openai":
            return _call_openai(question, evidence_text, supersession_context,
                                settings.llm_api_key, settings.llm_model)
        elif provider == "gemini":
            return _call_gemini(question, evidence_text, supersession_context,
                                settings.llm_api_key, settings.llm_model)
        else:
            raise ValueError(f"Unknown LLM provider: {provider!r}")

    def _get_related_docs(self, chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Get related document metadata for the response."""
        db = get_sync_db()
        doc_ids = list(set(c.get("document_id") for c in chunks))
        docs = list(db[Collections.DOCUMENTS].find(
            {"document_id": {"$in": doc_ids}},
            {"_id": 0, "document_id": 1, "title": 1, "issuer": 1, "status": 1,
             "publication_date": 1, "effective_date": 1},
        ))
        return docs

    def _log_query(
        self,
        query: str,
        chunks: List[Dict],
        answer: str,
        citations: List[Citation],
        latency_ms: float,
    ) -> None:
        """Log the query to MongoDB for observability."""
        try:
            db = get_sync_db()
            log = QueryLog(
                query=query,
                retrieved_chunks=[c.get("chunk_id", "") for c in chunks],
                retrieved_documents=list(set(c.get("document_id", "") for c in chunks)),
                answer=answer,
                citations=[c.model_dump() for c in citations],
                latency=latency_ms,
            )
            db[Collections.QUERY_LOGS].insert_one(log.model_dump())
        except Exception as e:
            logger.warning(f"Failed to log query: {e}")
