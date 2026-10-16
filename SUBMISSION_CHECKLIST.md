# Incuxai Challenge 2026 Submission Checklist

- [x] Install dependencies and launch Streamlit UI (`streamlit run app.py` running at `http://localhost:8501`).
- [x] Test Sample 1 (`sample_1_multi_page_ledger.pdf`): continued table merged across 2 pages without repeated headers.
- [x] Test Sample 2 (`sample_2_inventory_12_columns.pdf`): all 12 columns preserved with 100% precision.
- [x] Configure Tesseract and test Sample 3 (`sample_3_scanned_invoice.pdf`): grid OCR and dark header handling verified.
- [x] Test Sample 4 (`sample_4_scanned_multi_page_12col.pdf`): multi-page 12-column scanned ledger merged into 30 rows with 0 warnings.
- [x] Generate converted Excel workbooks in `outputs/` for all 4 test samples.
- [x] Verify `reports/accuracy_validation_report.md` with measured cell accuracy, row recall, and column preservation.
- [x] Complete `README.md` with quick start instructions, architecture, and 2–5 minute demo video script.
- [ ] Record your 2–5 minute demo video following the script in README.md.
- [ ] Submit GitHub link or ZIP before the 7:00 PM deadline!
