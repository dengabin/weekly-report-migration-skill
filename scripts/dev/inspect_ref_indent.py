#!/usr/bin/env python3
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))
from sheet_utils import find_sheet_in_kdc, kdc_sheet_to_rows

data = json.loads(Path(r"d:\branch\skills\report-migration\.cache\dept-content.json").read_text(encoding="utf-8"))
sheet = find_sheet_in_kdc(data.get("raw") or data, "应用研发-AI应用组")
rows = kdc_sheet_to_rows(sheet)
for row in rows:
    if len(row) > 1 and "张晋涛" in (row[1] or ""):
        for i, cell in enumerate(row):
            if i >= 4 and cell and "二级功能" in cell:
                print(f"col {i}:")
                print(repr(cell[:1200]))
        if len(row) > 4 and not any("二级功能" in (c or "") for c in row[4:]):
            print("E col preview:", repr((row[4] or "")[:400]))
