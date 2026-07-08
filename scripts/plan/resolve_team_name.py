#!/usr/bin/env python3
"""根据 otl 成员姓名在部门子表中解析组名；无法唯一确定时退出码 3 供 Agent 询问用户。"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))

from sheet_utils import (  # noqa: E402
    apply_team_name_to_config,
    find_cell_in_rows,
    find_sheet_in_kdc,
    kdc_sheet_to_rows,
    list_sheet_names_from_markdown,
    parse_sheet_table_from_markdown,
    resolve_dept_sheet,
    resolve_team_from_members,
)
from paths import SKILL_ROOT  # noqa: E402

PLACEHOLDER_TEAM_NAMES = frozenset({"你的组名", "示例小组名", ""})


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def is_team_name_set(cfg: dict) -> bool:
    name = (cfg.get("team_name") or "").strip()
    return bool(name) and name not in PLACEHOLDER_TEAM_NAMES


def validate_team_in_sheet(rows: list, member_names: list[str], cfg: dict) -> bool:
    """已有 team_name 时，验证全部成员均能在该组区块内定位。"""
    probe_cfg = json.loads(json.dumps(cfg))
    apply_team_name_to_config(probe_cfg, probe_cfg["team_name"])
    for name in member_names:
        member = {
            "name": name,
            "target": {
                "type": "sheet_cell",
                "row_match": {
                    "column": probe_cfg.get("options", {}).get("sheet_name_column", "B"),
                    "contains": name,
                },
            },
        }
        if find_cell_in_rows(rows, member, member["target"], probe_cfg) is None:
            return False
    return True


def rows_from_dept(cfg: dict, kdc_path: Path | None, md_path: Path | None) -> tuple[list, str | None, str]:
    if kdc_path and kdc_path.exists():
        raw = load_json(kdc_path).get("raw") or load_json(kdc_path)
        sheet_names = [s.get("name", "") for s in (raw.get("doc") or raw).get("sheets", [])]
        resolved, reason = resolve_dept_sheet([n for n in sheet_names if n], cfg)
        if not resolved:
            return [], None, reason
        sheet = find_sheet_in_kdc(raw, resolved)
        if not sheet:
            return [], resolved, f"KDC 中未找到子表: {resolved}"
        return kdc_sheet_to_rows(sheet), resolved, reason

    if md_path and md_path.exists():
        md = md_path.read_text(encoding="utf-8")
        sheet_names = list_sheet_names_from_markdown(md)
        resolved, reason = resolve_dept_sheet(sheet_names, cfg)
        if not resolved:
            return [], None, reason
        table = parse_sheet_table_from_markdown(md, resolved)
        if not table:
            return [], resolved, "部门 Markdown 中未解析到目标子表表格"
        return table, resolved, reason

    return [], None, "缺少部门表数据（dept-content.json 或 dept-report.md）"


def main() -> int:
    parser = argparse.ArgumentParser(description="从部门表姓名反推组名")
    parser.add_argument("--config", type=Path, default=SKILL_ROOT / "config.json")
    parser.add_argument("--extracted", type=Path, default=SKILL_ROOT / ".cache" / "extracted.json")
    parser.add_argument("--dept-kdc-json", type=Path, default=SKILL_ROOT / ".cache" / "dept-content.json")
    parser.add_argument("--dept-markdown", type=Path, default=SKILL_ROOT / ".cache" / "dept-report.md")
    parser.add_argument("--team-name", default=None, help="用户指定组名时写入 config")
    parser.add_argument("--output", type=Path, default=SKILL_ROOT / ".cache" / "team-resolve.json")
    args = parser.parse_args()

    if not args.extracted.exists():
        print(f"缺少 {args.extracted}", file=sys.stderr)
        return 1

    cfg = load_json(args.config) if args.config.exists() else {}
    extracted = load_json(args.extracted)
    member_names = [m["name"] for m in extracted.get("members", []) if m.get("name")]
    if not member_names:
        print("extracted.json 中无成员", file=sys.stderr)
        return 1

    if args.team_name:
        apply_team_name_to_config(cfg, args.team_name.strip())
        args.config.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"已写入 team_name={args.team_name!r}")

    rows, resolved_sheet, resolve_reason = rows_from_dept(cfg, args.dept_kdc_json, args.dept_markdown)
    if not rows:
        payload = {"status": "dept_unavailable", "reason": resolve_reason}
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 1

    if is_team_name_set(cfg) and validate_team_in_sheet(rows, member_names, cfg):
        payload = {
            "status": "already_set",
            "team_name": cfg["team_name"],
            "resolved_sheet": resolved_sheet,
            "reason": "config 中组名已有效，成员均可在该组区块定位",
        }
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0

    result = resolve_team_from_members(rows, member_names, cfg)
    result["resolved_sheet"] = resolved_sheet
    result["resolve_reason"] = resolve_reason

    if result["status"] == "resolved":
        apply_team_name_to_config(cfg, result["team_name"])
        args.config.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")
        result["applied"] = True

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))

    if result["status"] == "resolved":
        return 0
    if result["status"] in ("ambiguous", "need_team_name", "not_found"):
        return 3
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
