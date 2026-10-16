"""Orchestrates extraction, table continuation, validation, and export."""
from __future__ import annotations
import os
import re
import tempfile
import pandas as pd
from .extractors import extract_digital_tables, extract_ocr_tables
from .validator import validate_dataframe, normalize_header
from .excel_writer import write_workbook

def _looks_like_header(row):
    vals = [str(x).strip() for x in row]
    nonempty = [x for x in vals if x]
    if len(nonempty) < 2:
        return False
    alpha = sum(any(ch.isalpha() for ch in x) for x in nonempty)
    return alpha / len(nonempty) >= 0.5

def _rows_to_frame(rows):
    rows = [list(r) for r in rows if any(str(c).strip() for c in r)]
    if len(rows) < 2:
        return pd.DataFrame()
    width = max(len(r) for r in rows)
    rows = [r + [""] * (width-len(r)) for r in rows]
    if _looks_like_header(rows[0]):
        header = [normalize_header(v,i) for i,v in enumerate(rows[0])]
        body = rows[1:]
    else:
        header = [f"Column_{i+1}" for i in range(width)]
        body = rows
    # If a repeated header occurs within a page/table, remove it.
    body = [r for r in body if [str(x).strip().lower() for x in r] != [h.lower() for h in header]]
    df = pd.DataFrame(body, columns=header)
    return df.fillna("")

def _same_schema(a, b):
    if len(a.columns) != len(b.columns):
        return False
    norm = lambda s: re.sub(r"[^a-z0-9]", "", str(s).lower())
    return [norm(c) for c in a.columns] == [norm(c) for c in b.columns]

def run_agent(pdf_path: str, output_path: str, use_ocr: bool = True, ocr_dpi: int = 220):
    """Run extraction pipeline and return a summary dictionary."""
    if not os.path.isfile(pdf_path):
        raise FileNotFoundError(pdf_path)
    tables = extract_digital_tables(pdf_path)
    methods = {"pdfplumber": len(tables), "tesseract-ocr": 0}
    if not tables and use_ocr:
        try:
            tables = extract_ocr_tables(pdf_path, dpi=ocr_dpi)
            methods["tesseract-ocr"] = len(tables)
        except Exception as exc:
            methods["ocr_error"] = str(exc)
    frames = []
    logs = []
    for t in tables:
        df = _rows_to_frame(t["rows"])
        if df.empty:
            continue
        df["__source_page"] = t["page"]
        df["__source_table"] = t["table"]
        df["__extraction_method"] = t["method"]
        frames.append(df)
        logs.append({"page":t["page"],"table":t["table"],"method":t["method"],"rows":len(df),"columns":len(df.columns)-3})
    # Merge continued tables with matching schema; keep provenance in hidden columns.
    merged = []
    for frame in frames:
        matched = False
        for i, old in enumerate(merged):
            if _same_schema(old.drop(columns=["__source_page","__source_table","__extraction_method"], errors="ignore"),
                            frame.drop(columns=["__source_page","__source_table","__extraction_method"], errors="ignore")):
                merged[i] = pd.concat([old, frame], ignore_index=True)
                matched = True
                break
        if not matched:
            merged.append(frame)
    validation = []
    for i, df in enumerate(merged, start=1):
        user_df = df.drop(columns=["__source_page","__source_table","__extraction_method"], errors="ignore")
        validation.extend(validate_dataframe(user_df, source=f"Table {i}"))
        if user_df.empty:
            validation.append({"severity":"ERROR","check":"empty_table","message":f"Table {i} is empty.","source":pdf_path})
    clean_frames = [df.drop(columns=["__source_page","__source_table","__extraction_method"], errors="ignore") for df in merged]
    write_workbook(clean_frames, validation, logs, output_path)
    total_rows = sum(max(0,len(df)) for df in clean_frames)
    return {"input":os.path.basename(pdf_path),"output":output_path,"tables":len(merged),"rows":total_rows,
            "methods":methods,"validation_issues":len(validation),"warnings":validation,"logs":logs}
