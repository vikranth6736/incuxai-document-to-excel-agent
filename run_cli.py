import argparse
from src.agent import run_agent

parser = argparse.ArgumentParser(description="Convert PDF tables to Excel.")
parser.add_argument("pdf", help="Input PDF path")
parser.add_argument("xlsx", help="Output Excel path")
parser.add_argument("--no-ocr", action="store_true", help="Disable OCR fallback")
args = parser.parse_args()
result = run_agent(args.pdf, args.xlsx, use_ocr=not args.no_ocr)
print(f"Input: {result['input']}")
print(f"Tables: {result['tables']} | Rows: {result['rows']}")
print(f"Output: {result['output']}")
print(f"Validation findings: {result['validation_issues']}")
for issue in result["warnings"]:
    print(f"[{issue['severity']}] {issue['check']}: {issue['message']}")
