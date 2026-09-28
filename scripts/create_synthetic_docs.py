"""
Create Synthetic Regulatory Documents for ReguLens Testing.

Creates three deterministic documents for the critical supersession test:
  - 2019 Circular: Requirement = 10%
  - 2022 Amendment: Amends 2019, Requirement = 15%
  - 2024 Master Direction: Consolidates, Requirement = 20%

These synthetic documents are stored as plain-text PDFs using reportlab.
"""
from __future__ import annotations

import os
import sys

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from pathlib import Path


SYNTHETIC_DOCS = [
    {
        "filename": "RBI_Circular_2019_Capital_Requirements.pdf",
        "content": """RBI/2019-20/001
Reserve Bank of India
Circular on Capital Requirements for Scheduled Commercial Banks

Date: March 1, 2019

CIRCULAR

To,
All Scheduled Commercial Banks

Madam/Dear Sir,

1. INTRODUCTION

This circular sets out the capital requirements applicable to all scheduled commercial banks operating in India under the Banking Regulation Act, 1949.

2. CAPITAL REQUIREMENTS

2.1 Minimum Capital Adequacy Ratio

All scheduled commercial banks shall maintain a minimum Capital Adequacy Ratio (CAR) of 10 percent of the risk-weighted assets at all times.

2.2 Computation

The computation of risk-weighted assets shall be as per the guidelines specified by the Reserve Bank of India from time to time.

2.3 Reporting

Banks shall report their capital adequacy position to the Reserve Bank of India on a quarterly basis.

3. EFFECTIVE DATE

These guidelines shall come into effect from April 1, 2019.

4. APPLICABILITY

These requirements apply to all scheduled commercial banks licensed by the Reserve Bank of India.

5. PENALTIES

Non-compliance with these requirements may attract penalties as prescribed under the Banking Regulation Act, 1949.

Yours faithfully,

(Senior Officer)
Reserve Bank of India
""",
    },
    {
        "filename": "RBI_Circular_2022_Amendment_Capital_Requirements.pdf",
        "content": """RBI/2022-23/045
Reserve Bank of India
Amendment to Capital Requirements Circular (2019)

Date: June 15, 2022

CIRCULAR

To,
All Scheduled Commercial Banks

Madam/Dear Sir,

1. INTRODUCTION

In partial modification of RBI Circular RBI/2019-20/001 dated March 1, 2019, on Capital Requirements for Scheduled Commercial Banks, Reserve Bank of India hereby issues this amendment.

2. AMENDMENT TO CAPITAL REQUIREMENTS

2.1 Revised Minimum Capital Adequacy Ratio

The provisions of Para 2.1 of the Circular dated March 1, 2019 are hereby amended. All scheduled commercial banks shall maintain a minimum Capital Adequacy Ratio (CAR) of 15 percent of the risk-weighted assets at all times.

This requirement replaces the earlier requirement of 10 percent as specified in RBI/2019-20/001.

2.2 Additional Buffer

In addition to the minimum CAR of 15 percent, banks shall maintain a Capital Conservation Buffer of 2.5 percent of risk-weighted assets.

3. OTHER PROVISIONS

All other provisions of the Circular dated March 1, 2019 (RBI/2019-20/001) shall remain unchanged.

4. EFFECTIVE DATE

This amendment shall come into effect from July 1, 2022.

Yours faithfully,

(Senior Officer)
Reserve Bank of India
""",
    },
    {
        "filename": "RBI_Master_Direction_2024_Capital_Requirements.pdf",
        "content": """RBI/2024-25/MD-01
Reserve Bank of India
Master Direction — Capital Requirements for Scheduled Commercial Banks

Date: January 1, 2024

MASTER DIRECTION

To,
All Scheduled Commercial Banks

Madam/Dear Sir,

1. INTRODUCTION

In supersession of the earlier circulars on Capital Requirements, specifically RBI/2019-20/001 dated March 1, 2019 and RBI/2022-23/045 dated June 15, 2022, the Reserve Bank of India hereby issues this Master Direction on Capital Requirements for Scheduled Commercial Banks.

This Master Direction consolidates all existing instructions on capital requirements and supersedes the aforesaid circulars.

2. CAPITAL REQUIREMENTS

2.1 Minimum Capital Adequacy Ratio

All scheduled commercial banks shall maintain a minimum Capital Adequacy Ratio (CAR) of 20 percent of the risk-weighted assets at all times.

This requirement supersedes the earlier requirements of:
(a) 10 percent as per RBI/2019-20/001 dated March 1, 2019
(b) 15 percent as per RBI/2022-23/045 dated June 15, 2022

2.2 Capital Conservation Buffer

Banks shall maintain a Capital Conservation Buffer of 2.5 percent of risk-weighted assets in addition to the minimum CAR.

2.3 Countercyclical Capital Buffer

The Reserve Bank of India may, from time to time, prescribe a Countercyclical Capital Buffer (CCyB) of up to 2.5 percent.

2.4 Computation of Risk-Weighted Assets

The computation of risk-weighted assets shall be carried out as per the Basel III framework as applicable in India.

3. EVOLUTION OF CAPITAL REQUIREMENTS

Year    | Minimum CAR
2019    | 10%
2022    | 15%
2024    | 20%

4. REPORTING

Banks shall report their capital adequacy position to the Reserve Bank of India on a quarterly basis, using the formats prescribed from time to time.

5. PENALTIES

Non-compliance shall attract penalties as provided under the Banking Regulation Act, 1949, and the Reserve Bank of India Act, 1934.

6. EFFECTIVE DATE

This Master Direction shall come into effect from January 1, 2024.

7. SUPERSESSION

This Master Direction supersedes all earlier circulars and guidelines on the subject, including but not limited to:
(a) RBI/2019-20/001 dated March 1, 2019
(b) RBI/2022-23/045 dated June 15, 2022

Yours faithfully,

(Deputy Governor)
Reserve Bank of India
""",
    },
]


def create_pdf_from_text(text: str, output_path: str) -> None:
    """Create a simple PDF from text using reportlab (or write as .txt if not available)."""
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.platypus import Paragraph, SimpleDocTemplate

        doc = SimpleDocTemplate(output_path, pagesize=A4)
        styles = getSampleStyleSheet()
        story = []
        for line in text.split("\n"):
            line = line.strip()
            if line:
                story.append(Paragraph(line, styles["Normal"]))
        doc.build(story)
        print(f"Created PDF: {output_path}")
    except ImportError:
        # Fallback: write as .txt (useful for testing without reportlab)
        txt_path = output_path.replace(".pdf", ".txt")
        with open(txt_path, "w", encoding="utf-8") as f:
            f.write(text)
        print(f"reportlab not installed; wrote text file: {txt_path}")
        # Create a minimal PDF manually
        _write_minimal_pdf(text, output_path)


def _write_minimal_pdf(text: str, output_path: str) -> None:
    """Write a minimal valid PDF containing the text."""
    lines = text.split("\n")
    # Build PDF content
    content_stream = ""
    for i, line in enumerate(lines[:80]):  # Limit pages
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
    print(f"Created minimal PDF: {output_path}")


def main():
    output_dir = Path(__file__).parent.parent / "backend" / "data" / "synthetic"
    output_dir.mkdir(parents=True, exist_ok=True)

    for doc in SYNTHETIC_DOCS:
        output_path = output_dir / doc["filename"]
        if output_path.exists():
            print(f"Already exists: {output_path}")
            continue
        create_pdf_from_text(doc["content"], str(output_path))

    print(f"\nCreated {len(SYNTHETIC_DOCS)} synthetic documents in {output_dir}")
    print("\nDocument summary:")
    for doc in SYNTHETIC_DOCS:
        print(f"  - {doc['filename']}")


if __name__ == "__main__":
    main()
