#!/usr/bin/env python3
"""检查部门表是否有目标周列；无则调用 insert_week_column 并刷新 dept KDC。"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))
from paths import CACHE, SCRIPTS_ROOT, SKILL_ROOT, find_dept_ksheet  # noqa: E402
from subprocess_utils import configure_stdio, run_skill_cmd, skill_subprocess_env  # noqa: E402

configure_stdio()

PATCH = SCRIPTS_ROOT / "patch"
WORKFLOW = SCRIPTS_ROOT / "workflow"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="config.json")
    parser.add_argument("--week", default=None)
    args = parser.parse_args()

    cfg = json.loads((SKILL_ROOT / args.config).read_text(encoding="utf-8"))
    week = args.week or cfg.get("week")
    if not week:
        print("缺少 week", file=sys.stderr)
        return 1

    ksheet = find_dept_ksheet(CACHE)
    if not ksheet:
        print("未找到 .cache/*.ksheet，请先 preflight", file=sys.stderr)
        return 1

    pr_path = CACHE / "preflight-report.json"
    sheet = None
    if pr_path.exists():
        sheet = (
            (json.loads(pr_path.read_text(encoding="utf-8")).get("checks") or {})
            .get("dept_sheets", {})
            .get("resolved_sheet")
        )
    if not sheet:
        print("未解析 resolved_sheet", file=sys.stderr)
        return 1

    cmd = [
        sys.executable,
        str(PATCH / "insert_week_column.py"),
        "--config",
        args.config,
        "--input",
        str(ksheet),
        "--output",
        str(ksheet),
        "--sheet",
        sheet,
        "--week",
        week,
    ]
    print(f">>> {' '.join(cmd)}", flush=True)
    proc = subprocess.run(
        cmd, cwd=str(SKILL_ROOT), capture_output=True, text=True,
        encoding="utf-8", errors="replace", env=skill_subprocess_env(),
    )
    if proc.stdout:
        print(proc.stdout, end="" if proc.stdout.endswith("\n") else "\n", flush=True)
    if proc.stderr:
        print(proc.stderr, file=sys.stderr, end="" if proc.stderr.endswith("\n") else "\n", flush=True)
    code = proc.returncode
    if code != 0:
        return code

    report_path = CACHE / "week-column-report.json"
    try:
        text = proc.stdout.strip()
        start = text.find("{")
        end = text.rfind("}")
        if start >= 0 and end > start:
            report = json.loads(text[start : end + 1])
            report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    except (json.JSONDecodeError, ValueError):
        pass

    if report_path.exists():
        status = json.loads(report_path.read_text(encoding="utf-8")).get("status")
        if status == "exists":
            return 0

    pf = [sys.executable, str(WORKFLOW / "preflight.py"), "--config", args.config, "--skip-download"]
    print(f">>> {' '.join(pf)}", flush=True)
    return run_skill_cmd(pf, cwd=SKILL_ROOT)


if __name__ == "__main__":
    raise SystemExit(main())
