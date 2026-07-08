#!/usr/bin/env python3
"""从 extracted.json 回填 config.json 的 week 与 members（不写入文档链接）。"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))
from paths import SKILL_ROOT  # noqa: E402


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def members_from_extracted(ext: dict, week: str, name_column: str = "B") -> list[dict]:
    members = []
    for m in ext.get("members", []):
        name = m["name"]
        members.append(
            {
                "name": name,
                "extract": {"type": "heading", "heading": f"## {name}", "level": 2},
                "target": {
                    "type": "sheet_cell",
                    "row_match": {"column": name_column, "contains": name},
                    "col_match": {"row": 1, "equals": week},
                },
            }
        )
    return members


def main() -> int:
    parser = argparse.ArgumentParser(description="从 extracted.json 更新 config.members")
    parser.add_argument("--config", type=Path, default=SKILL_ROOT / "config.json")
    parser.add_argument("--extracted", type=Path, default=SKILL_ROOT / ".cache" / "extracted.json")
    parser.add_argument("--template", type=Path, default=SKILL_ROOT / "config.template.json")
    parser.add_argument("--week", default=None, help="覆盖周次，默认用 extracted.week_section")
    args = parser.parse_args()

    if not args.extracted.exists():
        print(f"缺少 {args.extracted}，请先运行 extract_otl_weekly.py", file=sys.stderr)
        return 1

    ext = load_json(args.extracted)
    week = args.week or ext.get("week_section")
    if not week:
        print("extracted.json 中无 week_section", file=sys.stderr)
        return 1

    if args.config.exists():
        cfg = load_json(args.config)
    elif args.template.exists():
        cfg = load_json(args.template)
        print(f"从模板初始化 {args.config}", flush=True)
    else:
        print("缺少 config.json，请先由 Agent 根据用户提供的链接创建配置", file=sys.stderr)
        return 1

    team = cfg.get("team_report") or {}
    dept = cfg.get("dept_report") or {}
    if not team.get("link_id") or not dept.get("link_id"):
        print("config 缺少 team_report.link_id 或 dept_report.link_id", file=sys.stderr)
        return 1

    cfg["week"] = week
    opts = cfg.setdefault("options", {})
    name_col = opts.get("sheet_name_column", "B")
    cfg["members"] = members_from_extracted(ext, week, name_col)
    opts["otl_week_section"] = week

    args.config.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"wrote {args.config} week={week} members={len(cfg['members'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
