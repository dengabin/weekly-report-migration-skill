#!/usr/bin/env python3
"""一键编排：预检 → 提取小组周报 → 生成迁移计划（预览，不写回）。"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))
from paths import CACHE, SCRIPTS_ROOT, SKILL_ROOT, find_dept_ksheet  # noqa: E402
from subprocess_utils import configure_stdio, run_skill_cmd  # noqa: E402

configure_stdio()

WORKFLOW = SCRIPTS_ROOT / "workflow"
EXTRACT = SCRIPTS_ROOT / "extract"
PLAN = SCRIPTS_ROOT / "plan"


def run(cmd: list[str]) -> int:
    print(f"\n>>> {' '.join(cmd)}", flush=True)
    return run_skill_cmd(cmd, cwd=SKILL_ROOT)


def main() -> int:
    parser = argparse.ArgumentParser(description="周报迁移一键预览")
    parser.add_argument("--config", default="config.json")
    parser.add_argument("--week", default=None, help="绝对日期，如 2026-07-02")
    parser.add_argument(
        "--relative-week",
        default=None,
        help="相对系统日历：0/本周、1/上周、2/上上周（优先于 --week）",
    )
    args = parser.parse_args()

    CACHE.mkdir(parents=True, exist_ok=True)

    code = run([sys.executable, str(WORKFLOW / "preflight.py"), "--config", args.config])
    if code == 2:
        print("\n需要 WPS_SID：请运行 python scripts/workflow/setup_wps_sid.py <你的wps_sid>", file=sys.stderr)
        return code
    if code != 0:
        report_path = CACHE / "preflight-report.json"
        if report_path.exists():
            print(report_path.read_text(encoding="utf-8"))
        return code

    team_md = CACHE / "team-report.md"
    if not team_md.exists():
        print("预检未生成 team-report.md", file=sys.stderr)
        return 1

    extract_cmd = [
        sys.executable,
        str(EXTRACT / "extract_otl_weekly.py"),
        "--markdown",
        str(team_md),
        "--output",
        str(CACHE / "extracted.json"),
    ]
    if args.relative_week is not None:
        extract_cmd.extend(["--relative-week", str(args.relative_week)])
    elif args.week:
        extract_cmd.extend(["--week", args.week])
    if run(extract_cmd) != 0:
        return 1

    build_cmd = [
        sys.executable,
        str(PLAN / "build_config_from_extracted.py"),
        "--config",
        args.config,
        "--extracted",
        str(CACHE / "extracted.json"),
    ]
    if args.week:
        build_cmd.extend(["--week", args.week])
    if run(build_cmd) != 0:
        return 1

    resolve_cmd = [
        sys.executable,
        str(PLAN / "resolve_team_name.py"),
        "--config",
        args.config,
        "--extracted",
        str(CACHE / "extracted.json"),
        "--dept-kdc-json",
        str(CACHE / "dept-content.json"),
        "--dept-markdown",
        str(CACHE / "dept-report.md"),
    ]
    code = run(resolve_cmd)
    if code == 3:
        report = CACHE / "team-resolve.json"
        if report.exists():
            print(report.read_text(encoding="utf-8"), file=sys.stderr)
        print("\n需要用户指定组名：见 references/team-name-resolution.md", file=sys.stderr)
        return code
    if code != 0:
        return code

    ensure_col_cmd = [
        sys.executable,
        str(WORKFLOW / "ensure_week_column.py"),
        "--config",
        args.config,
    ]
    if args.week:
        ensure_col_cmd.extend(["--week", args.week])
    if run(ensure_col_cmd) != 0:
        return 1

    format_cmd = [
        sys.executable,
        str(EXTRACT / "format_otl_for_ksheet.py"),
        "--input",
        str(CACHE / "extracted.json"),
        "--kdc-json",
        str(CACHE / "dept-content.json"),
        "--in-place",
    ]
    if run(format_cmd) != 0:
        return 1

    dept_md = CACHE / "dept-report.md"
    if not dept_md.exists():
        print("预检未生成 dept-report.md", file=sys.stderr)
        return 1

    plan_cmd = [
        sys.executable,
        str(PLAN / "plan_sheet_patches.py"),
        "--config",
        args.config,
        "--extracted",
        str(CACHE / "extracted.json"),
        "--output",
        str(CACHE / "patch-plan.json"),
    ]
    dept_ksheet = find_dept_ksheet(CACHE)
    if dept_ksheet:
        plan_cmd.extend(["--dept-ksheet", str(dept_ksheet)])
    else:
        plan_cmd.extend(["--dept-kdc-json", str(CACHE / "dept-content.json")])
    code = run(plan_cmd)
    if code == 0:
        plan = json.loads((CACHE / "patch-plan.json").read_text(encoding="utf-8"))
        print("\n=== 迁移预览摘要 ===")
        print(f"子表: {plan.get('resolved_sheet')}")
        for p in plan.get("patches", []):
            status = p.get("status")
            cell = p.get("cell", "-")
            name = p.get("name")
            preview = (p.get("content") or "")[:60].replace("\n", " ")
            print(f"  {name}: {cell} [{status}] {preview}...")
    return code


if __name__ == "__main__":
    raise SystemExit(main())
