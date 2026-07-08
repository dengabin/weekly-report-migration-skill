#!/usr/bin/env python3
"""列出部门周报 workbook 全部子表，并标出 config 会选中的目标子表。"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))

try:
    from openpyxl import load_workbook
except ImportError as e:
    raise SystemExit("请安装 openpyxl: pip install openpyxl") from e

from sheet_utils import resolve_dept_sheet


def load_config(path: Path) -> dict:
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def main() -> int:
    parser = argparse.ArgumentParser(description="列出部门周报表格子表")
    parser.add_argument("--config", type=Path, default=Path("config.json"))
    parser.add_argument("--input", type=Path, required=True, help="部门周报 xlsx/et 本地路径")
    args = parser.parse_args()

    cfg = load_config(args.config)
    wb = load_workbook(args.input, read_only=True, data_only=True)
    names = list(wb.sheetnames)
    resolved, reason = resolve_dept_sheet(names, cfg)

    sheets = []
    for sn in names:
        ws = wb[sn]
        sheets.append({"name": sn, "max_row": ws.max_row, "max_column": ws.max_column})

    payload = {
        "workbook": str(args.input),
        "sheet_count": len(names),
        "sheets": sheets,
        "resolved_sheet": resolved,
        "resolve_reason": reason,
        "team_name": cfg.get("team_name"),
        "fourth_dept_name": (cfg.get("dept_sheet") or {}).get("fourth_dept_name"),
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if resolved else 1


if __name__ == "__main__":
    raise SystemExit(main())
