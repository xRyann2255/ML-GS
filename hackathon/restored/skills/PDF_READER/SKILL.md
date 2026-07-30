---
name: PDF_READER
description: "Extract text and metadata from PDF files using pypdf."
---

# PDF_READER — PDF Text Extraction

> **Purpose:** Extract text content from PDF files for summarisation, search, or ingestion into memory.

**Out of scope:** PDF creation/editing, OCR (scanned images), form filling, digital signatures.

---

## Skill Identity

| Field | Value |
|-------|-------|
| **Name** | `PDF_READER` |
| **Scope** | Extract text and metadata from PDF files |
| **Inputs** | PDF file path, optional page numbers |
| **Tool** | `skills/PDF_READER/src/read_pdf.py` |
| **Outputs** | Plain text (concatenated or per-page JSON) |
| **Auth** | None — local file access only |
| **Authority** | Read-only |

---

## When to Use

- Need to read text from a PDF attachment (e.g. downloaded from Confluence).
- Summarising or distilling PDF content.
- Extracting structured data from a text-based PDF.
- Checking PDF metadata (page count, title, author).

---

## Prerequisites

- `pypdf` installed in the active Python environment (`pip install pypdf`).
- **Memory:** `memory/ref/python-setup.md` (UV/venv paths, uv-env.cmd invocation)

---

## Quick Start

### As a library

```python
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "skills" / "PDF_READER" / "src"))
from read_pdf import read_pdf, read_pdf_pages, pdf_metadata

# All pages as a single string
text = read_pdf("workspace/tmp/report.pdf")

# Specific pages as structured dicts
pages = read_pdf_pages("workspace/tmp/report.pdf", pages=[1, 2])
# [{"page": 1, "chars": 1474, "text": "..."}, ...]

# Metadata only
meta = pdf_metadata("workspace/tmp/report.pdf")
# {"pages": 3, "title": "...", "author": "...", ...}
```

### CLI

```bash
# All pages to stdout
python skills/PDF_READER/src/read_pdf.py workspace/tmp/report.pdf

# Specific pages, JSON output
python skills/PDF_READER/src/read_pdf.py workspace/tmp/report.pdf --pages 1,2 --json

# Save to file
python skills/PDF_READER/src/read_pdf.py workspace/tmp/report.pdf --out workspace/tmp/report.txt

# Metadata only
python skills/PDF_READER/src/read_pdf.py workspace/tmp/report.pdf --meta
```

---

## Key Functions

| Function | Use case |
|----------|----------|
| `read_pdf(path, pages=None)` | Full text extraction, all or selected pages |
| `read_pdf_pages(path, pages=None)` | Per-page dicts with `page`, `chars`, `text` |
| `pdf_metadata(path)` | Page count, title, author, subject, creator |

---

## Integration with CONFLUENCE

Typical workflow: download a PDF attachment, then extract text.

```python
from client import ConfluenceClient
from read_pdf import read_pdf

client = ConfluenceClient.from_env()
attachments = client.list_attachments("12345678")
pdf_att = [a for a in attachments if a["title"].endswith(".pdf")][0]

client.download_attachment(pdf_att["download_url"], "workspace/tmp/doc.pdf")
text = read_pdf("workspace/tmp/doc.pdf")
```

---

## Anti-patterns

| Pattern | Why it's wrong | Correct approach |
|---------|---------------|-----------------|
| Using `read_pdf` on scanned PDFs | Returns empty strings — no OCR | Tell user OCR is needed (e.g. Tesseract) |
| Reading 500-page PDFs without `--pages` | Slow, huge output | Select relevant pages first |
| Parsing tables from `extract_text()` | Text extraction loses table structure | Use `pdfplumber` or `tabula` for tables |

---

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| Empty text from scanned PDF | No OCR support in pypdf | Use Tesseract or other OCR tool |
| Slow on large PDFs | Reading all pages | Use `--pages` to select relevant pages |
| Table structure lost | `extract_text()` loses layout | Use `pdfplumber` or `tabula` for tables |

## Task-Based Execution

**Task label:** `pdf-reader` | **Args file:** `workspace/tmp/pdf_reader_args.json`

Preferred. Write args JSON, then `run_task("pdf-reader")`. CLI args pass through via `%*`.

## Links

- [pypdf documentation](https://pypdf.readthedocs.io/)
