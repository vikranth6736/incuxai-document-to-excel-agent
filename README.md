# Smart Document-to-Excel Agent — Incuxai Challenge 2026

An AI Agent that converts digital PDFs, multi-page continuation tables, and scanned documents/images into clean, structured Excel spreadsheets with automated validation, quality checks, and provenance logging.

---

## 🎯 Incuxai Challenge Checklist Alignment

| Challenge Requirement | Implementation Details | Status |
|---|---|:---:|
| **1️⃣ Handle PDFs up to 50 pages** | Streaming page processor; handles high page counts without memory bottlenecks | ✅ Implemented |
| **2️⃣ Extract tables with 10+ columns** | Dynamic & interval column extractors; verified on 12-column digital & scanned tables | ✅ Implemented |
| **3️⃣ Read scanned PDFs & images with OCR** | Dual-engine OCR (Ruled Grid Detector + Layout-Aware Extractor) via Tesseract & PyMuPDF | ✅ Implemented |
| **4️⃣ Automatically detect tables & headers** | Header keyword clustering & spatial anchor detection with noise suppression | ✅ Implemented |
| **5️⃣ Join tables across multiple pages** | Schema-based continuation merging (`_same_schema`) that removes repeated headers | ✅ Implemented |
| **6️⃣ Detect errors & validate data** | Automated validation sheet checking empty columns, missing values, and mixed types | ✅ Implemented |

---

## 🚀 Quick Start

### 1. Requirements
- Python 3.10+
- Tesseract OCR (auto-detected on Windows `C:\Program Files\Tesseract-OCR\tesseract.exe`, Linux `/usr/bin/tesseract`, and macOS Homebrew)

### 2. Setup
```bash
# Clone or open the project folder
cd incuxai_document_to_excel_agent

# Create virtual environment
python -m venv .venv

# Activate environment
# On Windows:
.venv\Scripts\activate
# On macOS/Linux:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Run the Web Interface (Streamlit)
```bash
streamlit run app.py
```
Open **`http://localhost:8501`** in your browser. Upload any PDF or scanned image (`.pdf`, `.png`, `.jpg`, `.jpeg`), configure OCR options, and download the converted `.xlsx` workbook.

### 4. Run via Command Line (CLI)
```bash
# Example 1: Multi-page continuation ledger (digital)
python run_cli.py samples/sample_1_multi_page_ledger.pdf outputs/sample_1_multi_page_ledger_converted.xlsx

# Example 2: Wide 12-column table (digital)
python run_cli.py samples/sample_2_inventory_12_columns.pdf outputs/sample_2_inventory_12_columns_converted.xlsx

# Example 3: Scanned invoice (OCR)
python run_cli.py samples/sample_3_scanned_invoice.pdf outputs/sample_3_scanned_invoice_converted.xlsx

# Example 4: Multi-page 12-column scanned ledger (OCR + Continuation)
python run_cli.py samples/sample_4_scanned_multi_page_12col.pdf outputs/sample_4_scanned_multi_page_12col_converted.xlsx
```

---

## 📁 Included Test Samples & Outputs

The repository comes with 4 comprehensive test documents covering all challenge requirements:

| Sample | Format | Test Purpose | Result |
|---|---|---|---|
| [`sample_1_multi_page_ledger.pdf`](samples/sample_1_multi_page_ledger.pdf) | Digital PDF | Multi-page table continuation across 2 pages | Merged into 1 table of 12 rows × 9 cols |
| [`sample_2_inventory_12_columns.pdf`](samples/sample_2_inventory_12_columns.pdf) | Digital PDF | Wide 12-column table alignment | 1 table of 6 rows × 12 cols preserved |
| [`sample_3_scanned_invoice.pdf`](samples/sample_3_scanned_invoice.pdf) | Scanned PDF | Scanned page OCR with inverted header | 1 table of 3 rows × 5 cols extracted |
| [`sample_4_scanned_multi_page_12col.pdf`](samples/sample_4_scanned_multi_page_12col.pdf) | Scanned PDF | 3-page scanned ledger (12 cols, multi-page) | Merged into 1 table of 30 rows × 12 cols |

All converted workbooks are pre-built in [`outputs/`](outputs/).

---

## 📊 Structure of the Generated Excel Workbook

Every generated workbook contains three structured sheets:
1. **`Table_1`** (or `Table_N`): Pure business data without clutter, formatted with auto-fitted column widths and styled headers.
2. **`Validation`**: Quality assurance findings listing severity (`WARNING`, `INFO`, `ERROR`), check type (`empty_columns`, `many_missing_values`, `duplicate_headers`, `mixed_numeric_text`), and affected source.
3. **`Extraction_Log`**: Complete audit trail detailing page number, table index, extraction backend (`pdfplumber`, `tesseract-ocr-grid`, or `tesseract-ocr`), and extracted row/column counts.

---

## 🎥 2–5 Minute Demo Script (For Video Presentation)

1. **Introduction (0:00 - 0:30)**: State project title, introduce the challenge, and launch the Streamlit app.
2. **Digital Multi-Page Continuation (0:30 - 1:15)**: Upload `sample_1_multi_page_ledger.pdf`. Show that the table spanning across 2 pages was seamlessly merged into a single sheet without repeating headers.
3. **Wide 12-Column Table (1:15 - 1:45)**: Upload `sample_2_inventory_12_columns.pdf`. Demonstrate perfect 12-column alignment and zero data loss.
4. **Scanned Documents & OCR Pipeline (1:45 - 2:45)**: Upload `sample_4_scanned_multi_page_12col.pdf` or `sample_3_scanned_invoice.pdf`. Explain how the dual-engine OCR detects ruled grids, handles dark headers, and joins 3 scanned pages into one 30-row table.
5. **Validation & Audit Logs (2:45 - 3:15)**: Open the downloaded Excel workbook. Show `Table_1`, the `Validation` sheet, and the `Extraction_Log` audit trail.
6. **Conclusion (3:15 - 3:30)**: Highlight deterministic reliability, zero paid LLM API dependencies, and high execution speed.
