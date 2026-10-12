"""
Official RBI Document Downloader for ReguLens.

Downloads authentic Reserve Bank of India (RBI) Master Directions and Circulars
directly from rbi.org.in using session-initialized requests to handle
official portal session requirements.

Usage:
    python scripts/download_rbi_docs.py --count 5
    python scripts/download_rbi_docs.py --all
    python scripts/download_rbi_docs.py --category kyc
"""
from __future__ import annotations

import argparse
import logging
import os
import re
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional
import requests

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("rbi_downloader")

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "backend" / "data" / "official_rbi"

# Curated catalog of essential RBI Master Directions
CURATED_RBI_DOCS = [
    {
        "id": "kyc",
        "title": "Master Direction - Know Your Customer (KYC)",
        "filename": "RBI_MD_Know_Your_Customer_KYC.pdf",
        "url": "https://rbidocs.rbi.org.in/rdocs/notification/PDFs/169MD.PDF",
        "category": "compliance",
    },
    {
        "id": "outsourcing",
        "title": "Master Direction - Managing Risks in Outsourcing of Financial Services",
        "filename": "RBI_MD_Managing_Risks_in_Outsourcing.pdf",
        "url": "https://rbidocs.rbi.org.in/rdocs/notification/PDFs/171MD.PDF",
        "category": "risk",
    },
    {
        "id": "cards",
        "title": "Master Direction - Credit Cards and Debit Cards: Issuance and Conduct",
        "filename": "RBI_MD_Credit_and_Debit_Cards_Issuance_Conduct.pdf",
        "url": "https://rbidocs.rbi.org.in/rdocs/notification/PDFs/155MD.PDF",
        "category": "retail",
    },
    {
        "id": "irac_npa",
        "title": "Master Direction - Income Recognition, Asset Classification and Provisioning (IRAC)",
        "filename": "RBI_MD_Income_Recognition_Asset_Classification_IRAC.pdf",
        "url": "https://rbidocs.rbi.org.in/rdocs/notification/PDFs/164MD.PDF",
        "category": "prudential",
    },
    {
        "id": "stressed_assets",
        "title": "Master Direction - Resolution of Stressed Assets",
        "filename": "RBI_MD_Resolution_of_Stressed_Assets.pdf",
        "url": "https://rbidocs.rbi.org.in/rdocs/notification/PDFs/165MD.PDF",
        "category": "prudential",
    },
    {
        "id": "interest_advances",
        "title": "Master Direction - Interest Rates on Advances",
        "filename": "RBI_MD_Interest_Rates_on_Advances.pdf",
        "url": "https://rbidocs.rbi.org.in/rdocs/notification/PDFs/161MD.PDF",
        "category": "lending",
    },
    {
        "id": "interest_deposits",
        "title": "Master Direction - Interest Rate on Deposits",
        "filename": "RBI_MD_Interest_Rate_on_Deposits.pdf",
        "url": "https://rbidocs.rbi.org.in/rdocs/notification/PDFs/153MD.PDF",
        "category": "deposits",
    },
    {
        "id": "internal_ombudsman_banks",
        "title": "Master Direction - Internal Ombudsman (Commercial Banks)",
        "filename": "RBI_MD_Internal_Ombudsman_Commercial_Banks.pdf",
        "url": "https://rbidocs.rbi.org.in/rdocs/notification/PDFs/380MD14012026DAD56B73DC944F02AEA4530EC779AD7F.PDF",
        "category": "consumer_protection",
    },
    {
        "id": "internal_ombudsman_sfb",
        "title": "Master Direction - Internal Ombudsman (Small Finance Banks)",
        "filename": "RBI_MD_Internal_Ombudsman_Small_Finance_Banks.pdf",
        "url": "https://rbidocs.rbi.org.in/rdocs/notification/PDFs/381MD140120267212A1D4EF8349448E9416EF8F2D19B5.PDF",
        "category": "consumer_protection",
    },
    {
        "id": "internal_ombudsman_nbfc",
        "title": "Master Direction - Internal Ombudsman (NBFCs)",
        "filename": "RBI_MD_Internal_Ombudsman_NBFCs.pdf",
        "url": "https://rbidocs.rbi.org.in/rdocs/notification/PDFs/383MD14012026559E41DD96224880B75EDB2B96E4BD8B.PDF",
        "category": "consumer_protection",
    },
    {
        "id": "credit_risk",
        "title": "Master Direction - Credit Risk Management",
        "filename": "RBI_MD_Credit_Risk_Management.pdf",
        "url": "https://rbidocs.rbi.org.in/rdocs/notification/PDFs/157MD.PDF",
        "category": "risk",
    },
    {
        "id": "concentration_risk",
        "title": "Master Direction - Concentration Risk Management",
        "filename": "RBI_MD_Concentration_Risk_Management.pdf",
        "url": "https://rbidocs.rbi.org.in/rdocs/notification/PDFs/158MD.PDF",
        "category": "risk",
    },
    {
        "id": "securitisation",
        "title": "Master Direction - Securitisation Transactions",
        "filename": "RBI_MD_Securitisation_Transactions.pdf",
        "url": "https://rbidocs.rbi.org.in/rdocs/notification/PDFs/160MD.PDF",
        "category": "markets",
    },
    {
        "id": "market_risk",
        "title": "Master Direction - Minimum Capital Requirements for Market Risk",
        "filename": "RBI_MD_Market_Risk_Minimum_Capital_Requirements.pdf",
        "url": "https://rbidocs.rbi.org.in/rdocs/notification/PDFs/472MDACBA450D67234F52BA2983DA6AED9DFC.PDF",
        "category": "capital",
    },
    {
        "id": "climate_finance",
        "title": "Master Direction - Climate Finance and Management of Climate Change Risks",
        "filename": "RBI_MD_Climate_Finance_and_Climate_Change_Risks.pdf",
        "url": "https://rbidocs.rbi.org.in/rdocs/notification/PDFs/172MD.PDF",
        "category": "sustainability",
    },
    {
        "id": "business_conduct",
        "title": "Master Direction - Responsible Business Conduct",
        "filename": "RBI_MD_Responsible_Business_Conduct.pdf",
        "url": "https://rbidocs.rbi.org.in/rdocs/notification/PDFs/170MD.PDF",
        "category": "governance",
    },
]


def create_rbi_session() -> requests.Session:
    """Initialize a requests session that passes RBI portal security."""
    session = requests.Session()
    session.headers.update({
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://www.rbi.org.in/Scripts/BS_ViewMasDirections.aspx",
    })

    # Prime session cookies by loading Master Directions index page
    logger.info("Initializing session with rbi.org.in...")
    try:
        init_res = session.get(
            "https://www.rbi.org.in/Scripts/BS_ViewMasDirections.aspx",
            timeout=20,
        )
        if init_res.status_code == 200:
            logger.info("Session successfully established with RBI portal.")
        else:
            logger.warning(f"Session prime returned status {init_res.status_code}.")
    except Exception as exc:
        logger.warning(f"Session priming warning: {exc}. Proceeding with standard headers.")

    return session


def download_file(session: requests.Session, url: str, dest_path: Path) -> bool:
    """Download a single PDF with validation."""
    if dest_path.exists() and dest_path.stat().st_size > 10000:
        logger.info(f"Already downloaded: {dest_path.name} ({dest_path.stat().st_size // 1024} KB)")
        return True

    try:
        resp = session.get(url, timeout=30, stream=True)
        if resp.status_code != 200:
            logger.error(f"Failed to fetch {url}: HTTP {resp.status_code}")
            return False

        content = resp.content
        # Verify it is indeed a PDF and not an HTML challenge
        if not content.startswith(b"%PDF"):
            logger.warning(
                f"File {dest_path.name} returned non-PDF content (starts with {content[:15]!r}). Skipping."
            )
            return False

        dest_path.parent.mkdir(parents=True, exist_ok=True)
        with open(dest_path, "wb") as f:
            f.write(content)

        size_kb = len(content) // 1024
        logger.info(f"✓ Downloaded: {dest_path.name} ({size_kb} KB)")
        return True
    except Exception as exc:
        logger.error(f"Error downloading {url}: {exc}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Download official RBI Master Directions")
    parser.add_argument("--count", type=int, default=5, help="Number of documents to download (default: 5)")
    parser.add_argument("--all", action="store_true", help="Download all curated documents")
    parser.add_argument("--category", type=str, default="", help="Filter by category (e.g. risk, prudential, kyc)")
    parser.add_argument("--output-dir", type=str, default="", help="Custom output directory")
    args = parser.parse_args()

    out_dir = Path(args.output_dir) if args.output_dir else OUTPUT_DIR
    out_dir.mkdir(parents=True, exist_ok=True)

    items = CURATED_RBI_DOCS
    if args.category:
        items = [d for d in items if args.category.lower() in d.get("category", "").lower() or args.category.lower() in d["id"].lower()]

    if not args.all:
        items = items[: args.count]

    logger.info(f"Targeting {len(items)} official RBI Master Direction(s) into: {out_dir}")
    session = create_rbi_session()

    success_count = 0
    for item in items:
        dest_path = out_dir / item["filename"]
        logger.info(f"Fetching '{item['title']}'...")
        if download_file(session, item["url"], dest_path):
            success_count += 1
        time.sleep(1.0)  # Gentle delay between requests

    logger.info(f"Done! Successfully downloaded {success_count}/{len(items)} RBI PDF(s).")
    print(f"\nDownloaded files located at:\n{out_dir}\n")


if __name__ == "__main__":
    main()
