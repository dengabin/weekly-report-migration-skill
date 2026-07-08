#!/usr/bin/env python3
"""根据 extracted.json 生成 AI应用组 config.json。"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ext = json.loads((ROOT / ".cache/extracted.json").read_text(encoding="utf-8"))
week = ext["week_section"]

members = []
for m in ext["members"]:
    members.append(
        {
            "name": m["name"],
            "extract": {"type": "heading", "heading": f"## {m['name']}", "level": 2},
            "target": {
                "type": "sheet_cell",
                "row_match": {"column": "A", "contains": m["name"]},
                "col_match": {"row": 1, "equals": week},
            },
        }
    )

cfg = {
    "team_name": "AI应用组",
    "week": week,
    "week_aliases": ["7.2", "7/2", "7.7-7.11"],
    "team_report": {
        "url": "https://365.kdocs.cn/l/cpqRAGyILoLO",
        "link_id": "cpqRAGyILoLO",
        "file_id": "bM5JJavnmxMHrKKdNb9b1xs5RN4LsoaqU",
        "drive_id": "WkEmxx6",
        "format": "otl",
        "title": "版式AI应用组26年周报",
    },
    "dept_report": {
        "url": "https://365.kdocs.cn/l/cqGvaEAyY8lG",
        "link_id": "cqGvaEAyY8lG",
        "file_id": "bPujDtEBY1Ma8Vqg3Ea11x4vrcJhEpRHx",
        "drive_id": "WkEmxx6",
        "format": "ksheet",
        "title": "2026版式产研部-周报",
    },
    "dept_sheet": {
        "fourth_dept_name": "AI应用组",
        "aliases": ["版式AI应用组", "AI应用"],
        "match": "contains",
        "fallback_scan": True,
    },
    "members": members,
    "options": {
        "trim_content": True,
        "sheet_header_row": 1,
        "sheet_name_column": "A",
        "team_row_marker": "AI应用组",
        "otl_week_section": week,
    },
}

out = ROOT / "config.json"
out.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"wrote {out} week={week} members={len(members)}")
