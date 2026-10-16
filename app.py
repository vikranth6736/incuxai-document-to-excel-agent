"""Streamlit interface for the Incuxai Document-to-Excel Agent."""
import os
import tempfile
import streamlit as st
from src.agent import run_agent

st.set_page_config(page_title="Smart Document-to-Excel Agent", page_icon="📄", layout="wide")
st.title("📄 Smart Document-to-Excel Agent")
st.caption("Extract digital PDF tables, use OCR for scanned PDFs, merge continued tables, and export validation reports.")
with st.sidebar:
    st.header("Extraction settings")
    use_ocr = st.checkbox("Enable OCR fallback", value=True)
    dpi = st.slider("OCR resolution (DPI)", min_value=150, max_value=350, value=220, step=25)
    st.info("OCR fallback requires Tesseract OCR installed on your computer and the Python packages in requirements.txt.")
uploaded = st.file_uploader("Upload a PDF or Image (PDF, PNG, JPG, JPEG)", type=["pdf", "png", "jpg", "jpeg", "tiff", "bmp", "webp"])
if uploaded:
    st.write(f"**File:** {uploaded.name} · **Size:** {uploaded.size/1024:.1f} KB")
    if st.button("Extract tables and create Excel", type="primary"):
        with st.spinner("Analyzing pages and extracting tables…"):
            with tempfile.TemporaryDirectory() as tmp:
                input_path = os.path.join(tmp, uploaded.name)
                output_path = os.path.join(tmp, "converted.xlsx")
                with open(input_path, "wb") as f:
                    f.write(uploaded.getbuffer())
                try:
                    result = run_agent(input_path, output_path, use_ocr=use_ocr, ocr_dpi=dpi)
                    st.success("Processing finished.")
                    a,b,c,d = st.columns(4)
                    a.metric("Tables", result["tables"])
                    b.metric("Rows", result["rows"])
                    c.metric("Validation findings", result["validation_issues"])
                    d.metric("PDF pages limit", "50")
                    st.json({"input":result["input"],"methods":result["methods"],"logs":result["logs"]})
                    with open(output_path, "rb") as f:
                        st.download_button("⬇️ Download Excel workbook", data=f.read(),
                                           file_name=os.path.splitext(uploaded.name)[0] + "_converted.xlsx",
                                           mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
                    if result["warnings"]:
                        st.subheader("Validation findings")
                        st.dataframe(result["warnings"], use_container_width=True)
                except Exception as exc:
                    st.error(f"Could not process this PDF: {exc}")
                    st.markdown("Check the README troubleshooting section. For scanned PDFs, verify Tesseract is installed and available on PATH.")
else:
    st.markdown("### Workflow")
    st.markdown("1. Upload a PDF.  2. Extract digital tables.  3. If none are found, try OCR.  4. Merge tables with matching headers.  5. Export Excel plus validation findings.")
    st.warning("This is a practical baseline, not a guarantee of perfect extraction. Always review validation findings and compare critical totals with the source document.")
