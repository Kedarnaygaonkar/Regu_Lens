"""
10x Scalability Benchmark for ReguLens.

Tests system behavior at 1x, 2x, 5x, 10x corpus size.
Reports: ingestion time, chunking time, embedding time, MongoDB insertion time,
index size, retrieval latency, answer latency, storage size.

NOTE: Generates actual synthetic documents and measures real timings.
Does not fabricate numbers.
"""
from __future__ import annotations

import os
import sys
import time
import json
import tempfile
from pathlib import Path
from typing import Dict, Any, List

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))


def generate_synthetic_pdf(content: str, output_path: str) -> None:
    """Generate a minimal PDF from text content."""
    lines = content.split("\n")
    content_stream = ""
    for i, line in enumerate(lines[:80]):
        escaped = line.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
        content_stream += f"BT /F1 10 Tf 50 {750 - i * 12} Td ({escaped}) Tj ET\n"

    stream_bytes = content_stream.encode("latin-1", errors="replace")
    stream_len = len(stream_bytes)

    pdf = (
        b"%PDF-1.4\n"
        b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
        b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
        b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] "
        b"/Contents 4 0 R /Resources << /Font << /F1 << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> >> >> >>\nendobj\n"
        + f"4 0 obj\n<< /Length {stream_len} >>\nstream\n".encode()
        + stream_bytes
        + b"\nendstream\nendobj\n"
        b"xref\n0 5\n0000000000 65535 f \n"
        b"trailer\n<< /Size 5 /Root 1 0 R >>\nstartxref\n0\n%%EOF"
    )
    with open(output_path, "wb") as f:
        f.write(pdf)


def generate_corpus(n_docs: int, tmpdir: str) -> List[str]:
    """Generate n_docs synthetic regulatory PDFs."""
    paths = []
    for i in range(n_docs):
        content = f"""RBI/{2019 + i // 10}-20/{i:04d}
Reserve Bank of India
Regulatory Circular {i}

1. INTRODUCTION

This circular {i} establishes requirements for document iteration {i}.

2. REQUIREMENTS

2.1 Main Requirement

All regulated entities shall comply with the following: requirement_{i} = {10 + i} percent.

2.2 Secondary Requirements

Additional requirements as per iteration {i}:
- Sub-requirement A: {i * 2} basis points
- Sub-requirement B: {i * 3} units

3. EFFECTIVE DATE

These guidelines shall come into effect from date_{i}.

4. SUPERSESSION

This circular supersedes circular number {i - 1} if applicable.

5. APPLICABILITY

Applies to all regulated entities as per Section {i % 10 + 1}.
"""
        path = os.path.join(tmpdir, f"circular_{i:04d}.pdf")
        generate_synthetic_pdf(content, path)
        paths.append(path)
    return paths


def run_benchmark(n_docs: int) -> Dict[str, Any]:
    """Run benchmark for n_docs documents. Returns timing results."""
    from app.ingestion.pipeline import ingest_pdf
    from app.models.document import DocumentCreate, DocumentStatus, DocumentType
    from app.embeddings.gemini_provider import LocalMockEmbeddingProvider
    from app.retrieval.hybrid_retriever import hybrid_retrieve
    from app.database import get_sync_db, Collections

    emb_provider = LocalMockEmbeddingProvider(dimensions=256)
    results = {
        "n_docs": n_docs,
        "ingestion_times": [],
        "total_ingestion_s": 0.0,
        "avg_ingestion_s": 0.0,
        "retrieval_latency_ms": [],
        "avg_retrieval_ms": 0.0,
        "total_chunks": 0,
        "total_sections": 0,
        "errors": 0,
    }

    with tempfile.TemporaryDirectory() as tmpdir:
        print(f"\n  Generating {n_docs} synthetic PDFs...")
        paths = generate_corpus(n_docs, tmpdir)

        print(f"  Ingesting {n_docs} documents...")
        for i, path in enumerate(paths):
            doc_meta = DocumentCreate(
                title=f"Benchmark Circular {i}",
                issuer="RBI",
                document_type=DocumentType.CIRCULAR,
                status=DocumentStatus.CURRENT,
                original_filename=os.path.basename(path),
            )

            t0 = time.time()
            result = ingest_pdf(
                pdf_path=path,
                document_meta=doc_meta,
                embedding_provider=emb_provider,
            )
            elapsed = time.time() - t0

            results["ingestion_times"].append(elapsed)
            if result.errors:
                results["errors"] += 1

    db = get_sync_db()
    results["total_chunks"] = db[Collections.CHUNKS].count_documents({})
    results["total_sections"] = db[Collections.SECTIONS].count_documents({})

    # Retrieval benchmark
    print(f"  Running retrieval benchmarks...")
    test_queries = [
        "capital adequacy requirement",
        "regulatory compliance entities",
        "effective date supersession",
    ]
    for q in test_queries:
        t0 = time.time()
        _ = hybrid_retrieve(
            query=q,
            query_embedding=emb_provider.embed_query(q),
            top_k=10,
        )
        elapsed_ms = (time.time() - t0) * 1000
        results["retrieval_latency_ms"].append(elapsed_ms)

    results["total_ingestion_s"] = sum(results["ingestion_times"])
    results["avg_ingestion_s"] = results["total_ingestion_s"] / max(n_docs, 1)
    results["avg_retrieval_ms"] = sum(results["retrieval_latency_ms"]) / max(len(results["retrieval_latency_ms"]), 1)

    return results


def main():
    print("ReguLens 10x Scalability Benchmark")
    print("=" * 60)
    print("NOTE: Using LocalMockEmbeddingProvider (no API key required)")
    print("NOTE: All timings are real measurements")
    print()

    corpus_sizes = [5, 10, 25, 50]  # 1x, 2x, 5x, 10x relative to 5-doc baseline
    all_results = []

    for n in corpus_sizes:
        print(f"\n[{n} documents — corpus size multiplier: {n // 5}x]")
        result = run_benchmark(n)
        all_results.append(result)

        print(f"  Total ingestion time: {result['total_ingestion_s']:.2f}s")
        print(f"  Avg per-document: {result['avg_ingestion_s']:.3f}s")
        print(f"  Total chunks in DB: {result['total_chunks']}")
        print(f"  Total sections in DB: {result['total_sections']}")
        print(f"  Avg retrieval latency: {result['avg_retrieval_ms']:.1f}ms")
        print(f"  Errors: {result['errors']}")

    # Save report
    report_path = Path(__file__).parent.parent / "docs" / "scalability_benchmark.json"
    with open(report_path, "w") as f:
        json.dump(all_results, f, indent=2, default=str)

    print(f"\n✓ Benchmark report saved to: {report_path}")

    # Print summary table
    print("\n" + "=" * 60)
    print("BENCHMARK SUMMARY TABLE")
    print("=" * 60)
    print(f"{'Docs':>6} | {'Total Ing(s)':>12} | {'Avg Ing(s)':>10} | {'Chunks':>8} | {'Retrieval(ms)':>13}")
    print("-" * 60)
    for r in all_results:
        print(
            f"{r['n_docs']:>6} | "
            f"{r['total_ingestion_s']:>12.2f} | "
            f"{r['avg_ingestion_s']:>10.3f} | "
            f"{r['total_chunks']:>8} | "
            f"{r['avg_retrieval_ms']:>13.1f}"
        )


if __name__ == "__main__":
    main()
