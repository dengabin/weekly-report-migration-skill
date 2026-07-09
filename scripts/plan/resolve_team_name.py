#!/usr/bin/env python3
"""根据 otl 成员姓名在部门子表中解析组名；无法唯一确定时退出码 3 供 Agent 询问用户。"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))

from ksheet_rows import ksheet_sheet_to_rows  # noqa: E402
from paths import CACHE, SKILL_ROOT, find_dept_ksheet  # noqa: E402
from sheet_utils import (  # noqa: E402
    apply_flat_sheet_layout_to_config,
    apply_team_name_to_config,
    detect_link_column_in_rows,
    find_cell_in_rows,
    find_sheet_in_kdc,
    format_team_resolve_agent_message,
    is_flat_dept_sheet,
    kdc_sheet_to_rows,
    list_sheet_names_from_markdown,
    list_ksheet_sheet_names,
    members_missing_in_flat_sheet,
    parse_sheet_table_from_markdown,
    persist_resolved_sheet_name,
    resolve_dept_sheet,
    resolve_team_from_members,
)

PLACEHOLDER_TEAM_NAMES = frozenset({"你的组名", "示例小组名", ""})


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def is_team_name_set(cfg: dict) -> bool:
    name = (cfg.get("team_name") or "").strip()
    return bool(name) and name not in PLACEHOLDER_TEAM_NAMES


def validate_team_in_sheet(
    rows: list,
    member_names: list[str],
    cfg: dict,
    members_by_name: dict[str, dict],
) -> bool:
    """已有 team_name 时，验证全部成员均能在该组区块内定位。"""
    probe_cfg = json.loads(json.dumps(cfg))
    apply_team_name_to_config(probe_cfg, probe_cfg["team_name"])
    for name in member_names:
        member = members_by_name.get(name, {"name": name})
        target = dict(member.get("target") or {})
        target.setdefault("type", "sheet_cell")
        target.setdefault(
            "row_match",
            {
                "column": probe_cfg.get("options", {}).get("sheet_name_column", "B"),
                "contains": name,
            },
        )
        if find_cell_in_rows(rows, member, target, probe_cfg) is None:
            return False
    return True


def rows_from_dept(
    cfg: dict,
    ksheet_path: Path | None,
    kdc_path: Path | None,
    md_path: Path | None,
) -> tuple[list, str | None, str, str]:
    """优先已下载 ksheet（与 plan/写回同源），其次 KDC，最后 Markdown。"""
    if ksheet_path and ksheet_path.exists():
        sheet_names = list_ksheet_sheet_names(ksheet_path)
        resolved, reason = resolve_dept_sheet(sheet_names, cfg)
        if resolved:
            try:
                rows = ksheet_sheet_to_rows(ksheet_path, resolved)
                if rows:
                    return rows, resolved, reason, "ksheet_zip"
            except ValueError:
                pass

    if kdc_path and kdc_path.exists():
        raw = load_json(kdc_path).get("raw") or load_json(kdc_path)
        sheet_names = [s.get("name", "") for s in (raw.get("doc") or raw).get("sheets", [])]
        resolved, reason = resolve_dept_sheet([n for n in sheet_names if n], cfg)
        if not resolved:
            return [], None, reason, "kdc"
        sheet = find_sheet_in_kdc(raw, resolved)
        if not sheet:
            return [], resolved, f"KDC 中未找到子表: {resolved}", "kdc"
        return kdc_sheet_to_rows(sheet), resolved, reason, "kdc"

    if md_path and md_path.exists():
        md = md_path.read_text(encoding="utf-8")
        sheet_names = list_sheet_names_from_markdown(md)
        resolved, reason = resolve_dept_sheet(sheet_names, cfg)
        if not resolved:
            return [], None, reason, "markdown"
        table = parse_sheet_table_from_markdown(md, resolved)
        if not table:
            return [], resolved, "部门 Markdown 中未解析到目标子表表格", "markdown"
        return table, resolved, reason, "markdown"

    return [], None, "缺少部门表（请先 preflight 下载 ksheet）", "none"


def resolve_flat_sheet(
    *,
    cfg: dict,
    rows: list,
    member_names: list[str],
    members_by_name: dict[str, dict],
    resolved_sheet: str | None,
    resolve_reason: str,
    config_path: Path,
    output_path: Path,
) -> int:
    missing, name_hints = members_missing_in_flat_sheet(
        rows, member_names, cfg, members_by_name
    )
    if not missing:
        apply_flat_sheet_layout_to_config(cfg, rows)
        persist_resolved_sheet_name(cfg, resolved_sheet)
        config_path.write_text(
            json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        link_col = detect_link_column_in_rows(rows, cfg)
        payload = {
            "status": "flat_sheet",
            "team_name": (cfg.get("team_name") or "").strip(),
            "resolved_sheet": resolved_sheet,
            "reason": "平铺布局（工号|姓名|链接列|周列），无组标题行分区"
            + (f"，链接列={link_col}" if link_col is not None else ""),
            "applied": True,
        }
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0

    payload = {
        "status": "not_found",
        "layout": "flat_sheet",
        "not_found": missing,
        "name_hints": name_hints,
        "resolved_sheet": resolved_sheet,
        "resolve_reason": resolve_reason,
        "reason": (
            "平铺子表：otl 中的姓名与部门表 B 列不一致，无法自动匹配。"
            "可能是组内周报 ## 姓名 标题写错（如多字、少字）。"
        ),
        "agent_action": "AskQuestion",
        "agent_hint": format_team_resolve_agent_message(
            {"status": "not_found", "layout": "flat_sheet", "not_found": missing, "name_hints": name_hints}
        ),
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 3


def main() -> int:
    parser = argparse.ArgumentParser(description="从部门表姓名反推组名")
    parser.add_argument("--config", type=Path, default=SKILL_ROOT / "config.json")
    parser.add_argument(
        "--extracted",
        type=Path,
        default=SKILL_ROOT / ".cache" / "extracted.json",
    )
    parser.add_argument(
        "--dept-ksheet",
        type=Path,
        default=None,
        help="已下载部门 ksheet，默认 .cache 中最新",
    )
    parser.add_argument(
        "--dept-kdc-json",
        type=Path,
        default=SKILL_ROOT / ".cache" / "dept-content.json",
    )
    parser.add_argument(
        "--dept-markdown",
        type=Path,
        default=SKILL_ROOT / ".cache" / "dept-report.md",
    )
    parser.add_argument("--team-name", default=None, help="用户指定组名时写入 config")
    parser.add_argument(
        "--output",
        type=Path,
        default=SKILL_ROOT / ".cache" / "team-resolve.json",
    )
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

    ksheet_path = args.dept_ksheet or find_dept_ksheet(CACHE, cfg)
    rows, resolved_sheet, resolve_reason, row_source = rows_from_dept(
        cfg, ksheet_path, args.dept_kdc_json, args.dept_markdown
    )
    if not rows:
        payload = {
            "status": "dept_unavailable",
            "reason": resolve_reason,
            "row_source": row_source,
        }
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 1

    previous_team = (cfg.get("team_name") or "").strip()
    if previous_team in PLACEHOLDER_TEAM_NAMES:
        previous_team = ""

    members_by_name = {
        m["name"]: m for m in extracted.get("members", []) if m.get("name")
    }

    # 平铺子表：不按组标题反推（启发式或 layout=flat）
    if is_flat_dept_sheet(rows, cfg):
        return resolve_flat_sheet(
            cfg=cfg,
            rows=rows,
            member_names=member_names,
            members_by_name=members_by_name,
            resolved_sheet=resolved_sheet,
            resolve_reason=resolve_reason,
            config_path=args.config,
            output_path=args.output,
        )

    result = resolve_team_from_members(rows, member_names, cfg, members_by_name)
    result["resolved_sheet"] = resolved_sheet
    result["resolve_reason"] = resolve_reason
    result["row_source"] = row_source

    if result["status"] == "resolved":
        new_team = result["team_name"]
        apply_team_name_to_config(cfg, new_team)
        persist_resolved_sheet_name(cfg, resolved_sheet)
        args.config.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")
        result["applied"] = True
        if previous_team and previous_team != new_team:
            result["team_name_changed"] = True
            result["previous_team_name"] = previous_team
            result["reason"] = (
                f"部门表组名已变更：{previous_team!r} → {new_team!r}，已按最新表头自动更新 config"
            )
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0

    if is_team_name_set(cfg) and validate_team_in_sheet(
        rows, member_names, cfg, members_by_name
    ):
        payload = {
            "status": "already_set",
            "team_name": cfg["team_name"],
            "resolved_sheet": resolved_sheet,
            "reason": "无法从姓名唯一反推，但 config 组名仍能在本次部门表定位全部成员",
        }
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0

    result["agent_hint"] = format_team_resolve_agent_message(result)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))

    if result["status"] in ("ambiguous", "need_team_name", "not_found"):
        return 3
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
