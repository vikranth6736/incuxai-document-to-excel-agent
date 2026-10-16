"""Data-quality checks that generate actionable warnings, not silent corrections."""
from __future__ import annotations
import re
import pandas as pd

def validate_dataframe(df: pd.DataFrame, source: str = "") -> list[dict]:
    issues = []
    if df.empty:
        return [{"severity":"ERROR","check":"empty_table","message":"No rows were extracted.","source":source}]
    if len(df.columns) < 2:
        issues.append({"severity":"WARNING","check":"few_columns","message":"Only one column detected; table structure may be incomplete.","source":source})
    blank_cols = [str(c) for c in df.columns if df[c].astype(str).str.strip().eq("").all()]
    if blank_cols:
        issues.append({"severity":"WARNING","check":"empty_columns","message":"Entirely empty column(s): " + ", ".join(blank_cols),"source":source})
    duplicate_headers = pd.Index(df.columns).duplicated().any()
    if duplicate_headers:
        issues.append({"severity":"WARNING","check":"duplicate_headers","message":"Duplicate column names detected.","source":source})
    for col in df.columns:
        series = df[col].astype(str).str.strip()
        if len(series) and (series.eq("").mean() > 0.25):
            issues.append({"severity":"WARNING","check":"many_missing_values",
                           "message":f"Column '{col}' has {series.eq('').mean():.0%} blank cells.","source":source})
    # Generic total reconciliation: when subtotal/tax/grand-total labels exist in a single column,
    # report them for manual verification rather than assuming a universal accounting rule.
    text = " ".join(df.astype(str).fillna("").values.flatten().tolist()).lower()
    if "grand total" in text or "subtotal" in text:
        issues.append({"severity":"INFO","check":"totals_present",
                       "message":"Total-related labels found. Verify arithmetic against line items; document formats vary.","source":source})
    # Flag suspicious numeric cells, but never auto-correct them.
    for col in df.columns:
        vals = df[col].astype(str).str.strip()
        nonempty = vals[vals.ne("")]
        if len(nonempty) >= 3:
            numeric_like = nonempty.str.match(r"^[₹$€£]?\s*-?[\d,]+(\.\d+)?%?$")
            ratio = numeric_like.mean()
            if 0.35 <= ratio < 0.75:
                issues.append({"severity":"WARNING","check":"mixed_numeric_text",
                               "message":f"Column '{col}' mixes numeric-looking and text values; inspect alignment or data types.","source":source})
    return issues

def normalize_header(value, idx):
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    return text if text else f"Unnamed_{idx+1}"
