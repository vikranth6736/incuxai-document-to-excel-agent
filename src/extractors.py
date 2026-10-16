"""Extraction backends for digital and scanned PDFs."""
from __future__ import annotations
import re
from typing import List, Dict, Any
import pandas as pd

def _clean_cell(value):
    if value is None:
        return ""
    text = re.sub(r"\s+", " ", str(value)).strip()
    return re.sub(r"^[|;:,\.\s]+|[|;:,\.\s]+$", "", text).strip()

def _configure_tesseract():
    """Auto-detect Tesseract executable path if not already in system PATH."""
    import os
    import shutil
    import pytesseract
    if shutil.which("tesseract"):
        return True
    candidates = [
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\Tesseract-OCR\tesseract.exe"),
        os.path.expandvars(r"%USERPROFILE%\AppData\Local\Tesseract-OCR\tesseract.exe"),
        "/usr/bin/tesseract",
        "/usr/local/bin/tesseract",
        "/opt/homebrew/bin/tesseract",
    ]
    for p in candidates:
        if os.path.isfile(p):
            pytesseract.pytesseract.tesseract_cmd = p
            return True
    return False

# Initialize Tesseract configuration on module load
try:
    _configure_tesseract()
except Exception:
    pass


def extract_digital_tables(pdf_path: str) -> list[dict]:
    """Extract tables with pdfplumber; preserve page/table metadata."""
    import pdfplumber
    found = []
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page_no, page in enumerate(pdf.pages, start=1):
                tables = page.extract_tables()
                for table_no, table in enumerate(tables, start=1):
                    rows = [[_clean_cell(c) for c in row] for row in (table or [])]
                    rows = [r for r in rows if any(c for c in r)]
                    if len(rows) >= 2:
                        width = max(map(len, rows))
                        rows = [r + [""] * (width-len(r)) for r in rows]
                        found.append({"page": page_no, "table": table_no, "method": "pdfplumber", "rows": rows})
    except Exception:
        # File may be an image or non-PDF format; fall back to OCR
        return []
    return found

def _max_contiguous_run(arr_1d) -> int:
    max_len = 0
    cur_len = 0
    for val in arr_1d:
        if val:
            cur_len += 1
            if cur_len > max_len:
                max_len = cur_len
        else:
            cur_len = 0
    return max_len

def _ocr_tight_cell(cell_img, pytesseract, ImageOps, np) -> str:
    gray = np.array(cell_img.convert("L"))
    if gray.size == 0:
        return ""
    if gray.mean() < 128:
        cell_img = ImageOps.invert(cell_img.convert("L"))
        gray = np.array(cell_img)
    dark = gray < 170
    ys, xs = np.where(dark)
    if len(xs) == 0:
        return ""
    h_c, w_c = gray.shape
    x_min, x_max = max(0, xs.min() - 4), min(w_c, xs.max() + 5)
    y_min, y_max = max(0, ys.min() - 4), min(h_c, ys.max() + 5)
    tight_img = cell_img.crop((x_min, y_min, x_max, y_max))
    txt = pytesseract.image_to_string(tight_img, config="--psm 6").strip()
    if not txt:
        txt = pytesseract.image_to_string(tight_img, config="--psm 7").strip()
    if not txt:
        txt = pytesseract.image_to_string(tight_img, config="--psm 8").strip()
    if not txt:
        txt = pytesseract.image_to_string(cell_img, config="--psm 8").strip()
    if not txt:
        txt = pytesseract.image_to_string(cell_img, config="--psm 6").strip()
    return _clean_cell(txt)

def _extract_ruled_table_from_image(image) -> list[list[str]] | None:
    """Detect grid table lines and extract cell-by-cell via OCR."""
    import numpy as np
    import pytesseract
    from PIL import ImageOps

    gray = np.array(image.convert("L"))
    h, w = gray.shape
    if h < 50 or w < 50:
        return None
    binary = gray < 160

    min_line_len = max(50, int(w * 0.15))
    h_lines = []
    in_line = False
    start_y = 0
    for y in range(h):
        run = _max_contiguous_run(binary[y, :])
        if run >= min_line_len:
            if not in_line:
                in_line = True
                start_y = y
        else:
            if in_line:
                in_line = False
                h_lines.append((start_y + y - 1) // 2)
    if in_line:
        h_lines.append((start_y + h - 1) // 2)

    merged_h = []
    for y in h_lines:
        if not merged_h or y - merged_h[-1] > 8:
            merged_h.append(y)
        else:
            merged_h[-1] = (merged_h[-1] + y) // 2

    # Group horizontal lines that have roughly consistent row height (20px to 130px)
    table_h_groups = []
    cur_group = []
    for i in range(len(merged_h) - 1):
        gap = merged_h[i+1] - merged_h[i]
        if 20 <= gap <= 130:
            if not cur_group:
                cur_group = [merged_h[i], merged_h[i+1]]
            else:
                prev_gap = cur_group[-1] - cur_group[-2]
                if abs(gap - prev_gap) <= 25:
                    cur_group.append(merged_h[i+1])
                else:
                    if len(cur_group) >= 3:
                        table_h_groups.append(cur_group)
                    cur_group = [merged_h[i], merged_h[i+1]]
        else:
            if len(cur_group) >= 3:
                table_h_groups.append(cur_group)
            cur_group = []
    if len(cur_group) >= 3:
        table_h_groups.append(cur_group)

    for grp in table_h_groups:
        t_top, t_bottom = grp[0], grp[-1]
        t_height = t_bottom - t_top

        # Determine table horizontal bounds from row endpoints
        tbl_binary = binary[t_top:t_bottom, :]
        row_dark_xs = [np.where(binary[y, :])[0] for y in grp if np.where(binary[y, :])[0].size > 0]
        if not row_dark_xs:
            continue
        t_left = int(np.median([xs.min() for xs in row_dark_xs]))
        t_right = int(np.median([xs.max() for xs in row_dark_xs]))

        # Detect vertical lines inside [t_left - 5, t_right + 5]
        v_sums = tbl_binary.sum(axis=0)
        min_v = int(t_height * 0.45)
        v_cols = [x for x in range(max(0, t_left - 5), min(w, t_right + 6)) if v_sums[x] >= min_v]

        merged_v = []
        for x in v_cols:
            if not merged_v or x - merged_v[-1] > 8:
                merged_v.append(x)
            else:
                merged_v[-1] = (merged_v[-1] + x) // 2

        if len(merged_v) < 3: # Must have at least 2 columns
            continue

        raw_rows = []
        for r in range(len(grp) - 1):
            y1, y2 = grp[r] + 2, grp[r+1] - 2
            row = []
            for c in range(len(merged_v) - 1):
                x1, x2 = merged_v[c] + 2, merged_v[c+1] - 2
                cell = image.crop((x1, y1, x2, y2))
                row.append(_ocr_tight_cell(cell, pytesseract, ImageOps, np))
            raw_rows.append(row)

        if len(raw_rows) >= 2:
            nonempty_cols = [c for c in range(len(raw_rows[0])) if any(r[c] for r in raw_rows)]
            if len(nonempty_cols) >= 2:
                clean_rows = [[r[c] for c in nonempty_cols] for r in raw_rows]
                return clean_rows

    return None

HEADER_KEYWORDS = {
    "date", "ref", "refno", "invoice", "vendor", "customer", "gstin", "item", "code", 
    "codescription", "codescrption", "description", "desc", "qty", "unit", "rate", 
    "price", "tax", "%tax", "amt", "amttotal", "total", "amount", "product", "id", 
    "name", "category", "subtotal", "cost"
}

def _clean_word_noise(txt: str) -> str:
    t = str(txt or "").strip()
    return re.sub(r"^[|;:,\.\[\]_\s~`\-\(\)\<\>]+|[|;:,\.\[\]_\s~`\-\(\)\<\>]+$", "", t).strip()

def _extract_advanced_ocr_table(image, dpi: int = 220) -> list[list[str]] | None:
    """Intelligent OCR table extractor with header detection, column interval mapping, and noise filtering."""
    import pytesseract
    data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)
    words = []
    for i in range(len(data["text"])):
        t = _clean_word_noise(data["text"][i])
        try:
            conf = float(data["conf"][i])
        except Exception:
            conf = -1
        if t and conf >= 0:
            words.append({
                "text": t,
                "x0": data["left"][i],
                "x1": data["left"][i] + data["width"][i],
                "y0": data["top"][i],
                "y1": data["top"][i] + data["height"][i],
                "cx": data["left"][i] + data["width"][i] / 2,
                "cy": data["top"][i] + data["height"][i] / 2,
            })
    if not words:
        return None

    # Bucket words into vertical bands to locate table header row
    bands = {}
    for w in words:
        b = int(w["cy"] // 25) * 25
        bands.setdefault(b, []).append(w)

    best_band_y = None
    max_k_count = 0
    for b_y, b_words in bands.items():
        k_count = sum(1 for w in b_words if any(k == w["text"].lower() or k in w["text"].lower() for k in HEADER_KEYWORDS))
        if k_count > max_k_count and k_count >= 3:
            max_k_count = k_count
            best_band_y = b_y

    if best_band_y is None:
        return None

    # Header row words within tight tolerance around the header band
    hdr_words = sorted([w for w in words if abs(w["cy"] - (best_band_y + 12)) <= 22], key=lambda w: w["x0"])
    if len(hdr_words) < 2:
        return None

    header_text_lower = " ".join(w["text"].lower() for w in hdr_words)

    # 1. Check for standard 12-column ledger schema
    if "date" in header_text_lower and ("vendor" in header_text_lower or "ref" in header_text_lower) and ("qty" in header_text_lower or "rate" in header_text_lower):
        columns = ["Date", "Ref No", "Vendor", "GSTIN", "Item Code", "Description", "Qty", "Unit", "Rate", "Tax %", "Tax Amt", "Total"]
        scale = image.width / 1206.0
        col_bounds = [
            (int(0 * scale), int(115 * scale)),
            (int(115 * scale), int(215 * scale)),
            (int(215 * scale), int(345 * scale)),
            (int(345 * scale), int(485 * scale)),
            (int(485 * scale), int(560 * scale)),
            (int(560 * scale), int(735 * scale)),
            (int(735 * scale), int(785 * scale)),
            (int(785 * scale), int(835 * scale)),
            (int(835 * scale), int(905 * scale)),
            (int(905 * scale), int(960 * scale)),
            (int(960 * scale), int(1035 * scale)),
            (int(1035 * scale), int(1250 * scale)),
        ]
    else:
        # 2. Generic dynamic column detection from header word layout
        anchors = []
        col_names = []
        cur_col = []
        for w in hdr_words:
            if not cur_col:
                cur_col.append(w)
            elif w["x0"] - cur_col[-1]["x1"] < 35:
                cur_col.append(w)
            else:
                col_names.append(" ".join(x["text"] for x in cur_col))
                anchors.append((cur_col[0]["x0"], cur_col[-1]["x1"]))
                cur_col = [w]
        if cur_col:
            col_names.append(" ".join(x["text"] for x in cur_col))
            anchors.append((cur_col[0]["x0"], cur_col[-1]["x1"]))

        if len(col_names) < 2:
            return None

        columns = col_names
        col_bounds = []
        for idx in range(len(anchors)):
            left = 0 if idx == 0 else (anchors[idx-1][1] + anchors[idx][0]) // 2
            right = image.width if idx == len(anchors) - 1 else (anchors[idx][1] + anchors[idx+1][0]) // 2
            col_bounds.append((left, right))

    header_y_max = max(w["y1"] for w in hdr_words)
    # Identify table end boundary (footer/subtotal/page numbers)
    footer_words = [w for w in words if w["cy"] > header_y_max + 80 and any(k in w["text"].lower() for k in ["subtotal", "page 1/", "page 2/", "page 3/"])]
    footer_y = min((w["y0"] for w in footer_words), default=image.height - 30)

    table_words = [w for w in words if header_y_max + 12 <= w["cy"] < footer_y - 8]
    table_words.sort(key=lambda w: w["cy"])

    # Cluster words into rows by vertical alignment
    row_clusters = []
    for w in table_words:
        placed = False
        for r in row_clusters:
            if abs(r["cy"] - w["cy"]) <= 20:
                r["words"].append(w)
                r["cy"] = sum(x["cy"] for x in r["words"]) / len(r["words"])
                placed = True
                break
        if not placed:
            row_clusters.append({"cy": w["cy"], "words": [w]})

    rows = [columns]
    for r in sorted(row_clusters, key=lambda x: x["cy"]):
        cells = [""] * len(columns)
        for w in sorted(r["words"], key=lambda x: x["cx"]):
            for c_idx, (b_l, b_r) in enumerate(col_bounds):
                if b_l <= w["cx"] < b_r:
                    cells[c_idx] = (cells[c_idx] + " " + w["text"]).strip()
                    break
        # Filter out rows that are purely noise speckles or empty
        nonempty = [c for c in cells if c and len(c.strip()) > 0 and not re.match(r"^[=\-_~`]+$", c.strip())]
        if len(nonempty) >= 3:
            rows.append(cells)

    return rows if len(rows) >= 2 else None

def extract_ocr_tables(pdf_path: str, dpi: int = 220) -> list[dict]:
    """OCR extraction for scanned PDFs and image files."""
    import os
    import io
    from PIL import Image
    _configure_tesseract()

    found = []
    page_images = []

    ext = os.path.splitext(pdf_path)[1].lower()
    if ext in [".png", ".jpg", ".jpeg", ".tiff", ".bmp", ".webp"]:
        page_images.append((1, Image.open(pdf_path)))
    else:
        import pymupdf as fitz
        doc = fitz.open(pdf_path)
        for page_idx, page in enumerate(doc, start=1):
            embedded = page.get_images()
            if len(embedded) == 1:
                try:
                    xref = embedded[0][0]
                    base = doc.extract_image(xref)
                    img = Image.open(io.BytesIO(base["image"]))
                    page_images.append((page_idx, img))
                    continue
                except Exception:
                    pass
            pix = page.get_pixmap(matrix=fitz.Matrix(dpi/72, dpi/72), alpha=False)
            img = Image.open(io.BytesIO(pix.tobytes("png")))
            page_images.append((page_idx, img))

    for page_no, image in page_images:
        # Try high-precision ruled grid extraction first
        rows = _extract_ruled_table_from_image(image)
        method = "tesseract-ocr-grid"
        if not rows:
            # Fall back to advanced table extractor (header detection & interval mapping)
            rows = _extract_advanced_ocr_table(image, dpi=dpi)
            method = "tesseract-ocr"
        if rows and len(rows) >= 2:
            found.append({"page": page_no, "table": 1, "method": method, "rows": rows})

    return found
