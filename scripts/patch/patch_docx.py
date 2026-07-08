#!/usr/bin/env python3
"""对 docx 表格单元格做局部写入。"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

try:
    from docx import Document
except ImportError as e:
    raise SystemExit("请安装 python-docx: pip install python-docx") from e


def load_json(path: Path) -> dict:
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    plan = load_json(args.plan)
    doc = Document(args.input)
    applied = []

    for patch in plan.get("patches", []):
        if patch.get("status") != "ready":
            continue
        table = doc.tables[patch["table_index"]]
        cell = table.rows[patch["row"]].cells[patch["col"]]
        cell.text = patch.get("content", "")
        applied.append(patch["name"])

    args.output.parent.mkdir(parents=True, exist_ok=True)
    doc.save(args.output)
    print(json.dumps({"applied": applied, "output": str(args.output)}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
