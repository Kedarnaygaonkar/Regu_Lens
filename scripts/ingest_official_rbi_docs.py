"""
Batch Ingestion Script for Official RBI Documents into ReguLens.

Sends downloaded PDFs to the running ReguLens backend API (http://localhost:8000/upload)
or ingests directly via the backend pipeline.

Usage:
    python scripts/ingest_official_rbi_docs.py
"""
from __future__ import annotations

import argparse
import logging
import os
import sys
import time
from pathlib import Path
import requests

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("rbi_ingest")

RBI_DIR = Path(__file__).resolve().parent.parent / "backend" / "data" / "official_rbi"
API_URL = "http://localhost:8000/upload"


def ingest_via_api(pdf_path: Path) -> bool:
    """Upload PDF to running ReguLens API."""
    title = pdf_path.stem.replace("_", " ").replace("RBI MD ", "RBI Master Direction: ")
    logger.info(f"Ingesting '{pdf_path.name}' via API...")

    try:
        with open(pdf_path, "rb") as f:
            files = {"file": (pdf_path.name, f, "application/pdf")}
            data = {
                "title": title,
                "issuer": "Reserve Bank of India",
                "document_type": "Master Direction",
                "source_url": "https://www.rbi.org.in/Scripts/BS_ViewMasDirections.aspx",
                "status": "ACTIVE",
            }
            resp = requests.post(API_URL, files=files, data=data, timeout=120)

        if resp.status_code == 200:
            res_data = resp.json()
            doc_id = res_data.get("document_id")
            chunks = res_data.get("chunks_created", 0)
            sections = res_data.get("sections_created", 0)
            was_dup = res_data.get("was_duplicate", False)
            if was_dup:
                logger.info(f"↷ {pdf_path.name} was already ingested (id: {doc_id})")
            else:
                logger.info(
                    f"✓ Ingested: {pdf_path.name} → {sections} sections, {chunks} chunks (id: {doc_id})"
                )
            return True
        else:
            logger.error(f"API Error {resp.status_code}: {resp.text}")
            return False
    except Exception as exc:
        logger.error(f"Failed to ingest {pdf_path.name}: {exc}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Ingest downloaded RBI PDFs into ReguLens")
    parser.add_argument("--dir", type=str, default="", help="Directory with PDFs")
    parser.add_argument("--limit", type=int, default=0, help="Limit number of files to ingest")
    args = parser.parse_args()

    target_dir = Path(args.dir) if args.dir else RBI_DIR
    if not target_dir.exists():
        logger.error(f"Directory not found: {target_dir}")
        sys.exit(1)

    pdf_files = sorted(list(target_dir.glob("*.pdf")))
    if not pdf_files:
        logger.warning(f"No PDFs found in {target_dir}. Run 'python scripts/download_rbi_docs.py' first.")
        return

    if args.limit > 0:
        pdf_files = pdf_files[: args.limit]

    logger.info(f"Found {len(pdf_files)} PDF(s) to ingest in {target_dir}")
    success_count = 0
    for pdf_file in pdf_files:
        if ingest_via_api(pdf_file):
            success_count += 1
        time.sleep(1.0)

    logger.info(f"Ingestion complete: {success_count}/{len(pdf_files)} documents processed.")


if __name__ == "__main__":
    main()
