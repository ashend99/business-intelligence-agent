"""
tests/ingestion/conftest.py

Pytest fixtures that create real sample files in a temporary directory.
These are used across all ingestion tests.

No external files needed — everything is generated in memory during the test run.
"""

import csv
import textwrap
from pathlib import Path

import pytest
from docx import Document as DocxDocument
from openpyxl import Workbook


# ---------------------------------------------------------------------------
# Individual file fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def txt_file(tmp_path: Path) -> Path:
    """A plain text file with multi-line content."""
    f = tmp_path / "sample.txt"
    f.write_text(
        textwrap.dedent("""\
            Café & Restaurant — Daily Summary
            Date: 2026-05-08
            Total covers: 120
            Revenue: $4,850.00
            Top dish: Grilled Salmon
        """),
        encoding="utf-8",
    )
    return f


@pytest.fixture()
def txt_file_utf8_special(tmp_path: Path) -> Path:
    """A text file containing non-ASCII characters (accents, symbols)."""
    f = tmp_path / "special_chars.txt"
    f.write_text("Café · résumé · naïve · 日本語 · العربية", encoding="utf-8")
    return f


@pytest.fixture()
def csv_file(tmp_path: Path) -> Path:
    """A CSV file with a header row and several data rows."""
    f = tmp_path / "sales.csv"
    with open(f, "w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(["date", "item", "quantity", "revenue"])
        writer.writerow(["2026-05-01", "Espresso", "45", "180.00"])
        writer.writerow(["2026-05-01", "Latte", "30", "150.00"])
        writer.writerow(["2026-05-02", "Cappuccino", "50", "200.00"])
    return f


@pytest.fixture()
def docx_file(tmp_path: Path) -> Path:
    """A Word document with a heading and two paragraphs."""
    f = tmp_path / "brand_guide.docx"
    doc = DocxDocument()
    doc.add_heading("Brand Guidelines", level=1)
    doc.add_paragraph("Our gem business stands for quality and authenticity.")
    doc.add_paragraph("All stones are ethically sourced from certified suppliers.")
    doc.save(str(f))
    return f


@pytest.fixture()
def xlsx_file(tmp_path: Path) -> Path:
    """An Excel workbook with one sheet and a few rows of data."""
    f = tmp_path / "hotel_occupancy.xlsx"
    wb = Workbook()
    ws = wb.active
    ws.title = "Occupancy"
    ws.append(["date", "room_type", "rooms_sold", "adr"])
    ws.append(["2026-05-01", "Standard", 40, 120.00])
    ws.append(["2026-05-01", "Deluxe", 15, 180.00])
    ws.append(["2026-05-02", "Suite", 5, 350.00])
    wb.save(str(f))
    return f


@pytest.fixture()
def empty_txt_file(tmp_path: Path) -> Path:
    """A text file with no content."""
    f = tmp_path / "empty.txt"
    f.write_text("", encoding="utf-8")
    return f


@pytest.fixture()
def unsupported_file(tmp_path: Path) -> Path:
    """A file with an unsupported extension."""
    f = tmp_path / "image.png"
    f.write_bytes(b"\x89PNG\r\n\x1a\n")  # PNG magic bytes
    return f


@pytest.fixture()
def docs_directory(
    tmp_path: Path,
    txt_file: Path,
    csv_file: Path,
    docx_file: Path,
    xlsx_file: Path,
) -> Path:
    """
    A directory tree with one file of each supported type plus an
    unsupported file — mirrors the real docs/ structure.

        tmp/
        ├── cafe/
        │   ├── sales.csv
        │   └── summary.txt
        ├── hotel/
        │   └── hotel_occupancy.xlsx
        └── gems/
            ├── brand_guide.docx
            └── logo.png      ← unsupported, should be skipped
    """
    (tmp_path / "cafe").mkdir()
    (tmp_path / "hotel").mkdir()
    (tmp_path / "gems").mkdir()

    # Copy fixture files into the sub-directories
    (tmp_path / "cafe" / "sales.csv").write_bytes(csv_file.read_bytes())
    (tmp_path / "cafe" / "summary.txt").write_bytes(txt_file.read_bytes())
    (tmp_path / "hotel" / "hotel_occupancy.xlsx").write_bytes(xlsx_file.read_bytes())
    (tmp_path / "gems" / "brand_guide.docx").write_bytes(docx_file.read_bytes())
    (tmp_path / "gems" / "logo.png").write_bytes(b"\x89PNG\r\n\x1a\n")  # unsupported

    return tmp_path
