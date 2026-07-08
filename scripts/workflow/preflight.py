#!/usr/bin/env python3
"""Skill 加载时自动预检：依赖、WPS_SID、wps365-read、部门表可读性、子表解析。"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))

from wps365_bridge import (  # noqa: E402
    ensure_cache,
    ensure_wps365_read,
    find_wps365_read_root,
    resolve_wps_sid,
    run_drive,
)
from paths import SKILL_ROOT  # noqa: E402

NEED_SID = 2
FAIL = 1
OK = 0


def load_config(path: Path) -> dict:
    if not path.exists():
        raise FileNotFoundError(f"缺少配置文件: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def check_python_deps() -> dict:
    missing = []
    for pkg in ("openpyxl", "yaml"):
        try:
            __import__("yaml" if pkg == "yaml" else pkg)
        except ImportError:
            missing.append("pyyaml" if pkg == "yaml" else pkg)
    return {"ok": not missing, "missing": missing}


def extract_sheet_names_from_content_json(data: dict) -> list[str]:
    names: list[str] = []
    raw = data.get("raw") or {}
    sheets = raw.get("sheets") or raw.get("doc", {}).get("sheets") or []
    for s in sheets:
        n = s.get("name")
        if n:
            names.append(n)
    # 部分 ksheet 导出仅在 content markdown 中以 ## sheet名 呈现
    content = data.get("content") or ""
    for line in content.splitlines():
        if line.startswith("## ") and not line.startswith("### "):
            names.append(line[3:].strip())
    return list(dict.fromkeys(names))


def resolve_sheet_name(sheet_names: list[str], cfg: dict) -> tuple[str | None, str]:
    from sheet_utils import resolve_dept_sheet

    return resolve_dept_sheet(sheet_names, cfg)


def main() -> int:
    parser = argparse.ArgumentParser(description="周报迁移 Skill 预检")
    parser.add_argument("--config", type=Path, default=SKILL_ROOT / "config.json")
    parser.add_argument("--output", type=Path, default=SKILL_ROOT / ".cache" / "preflight-report.json")
    parser.add_argument("--skip-download", action="store_true")
    args = parser.parse_args()

    report: dict = {
        "skill_root": str(SKILL_ROOT),
        "status": "running",
        "checks": {},
    }

    try:
        cfg = load_config(args.config)
    except FileNotFoundError as e:
        report["status"] = "need_config"
        report["error"] = str(e)
        report["hint"] = "复制 config.template.json 为 config.json 并填写链接"
        _write_report(args.output, report)
        return FAIL

    report["team_name"] = cfg.get("team_name")
    report["week"] = cfg.get("week")

    deps = check_python_deps()
    report["checks"]["python_deps"] = deps
    if not deps["ok"]:
        report["status"] = "need_deps"
        report["hint"] = f"pip install -r requirements.txt  # 另需: {', '.join(deps['missing'])}"
        _write_report(args.output, report)
        return FAIL

    wps_root = find_wps365_read_root(cfg)
    if not wps_root:
        wps_root = ensure_wps365_read(cfg, write_config_root=args.config)
    report["checks"]["wps365_read"] = {
        "ok": wps_root is not None,
        "root": str(wps_root) if wps_root else None,
    }
    if not wps_root:
        report["status"] = "need_wps365_read"
        report["hint"] = (
            "Agent 应执行 python scripts/workflow/setup_wps365_read.py 自动发现或安装；"
            "仍失败时在 config.json 设置 wps365_read.repo_url 或环境变量 WPS365_READ_REPO_URL。"
            "禁止让用户手动找目录。"
        )
        _write_report(args.output, report)
        return FAIL

    sid, sid_source = resolve_wps_sid(cfg)
    report["checks"]["wps_sid"] = {
        "ok": bool(sid),
        "source": sid_source,
        "masked": f"{sid[:6]}...{sid[-4:]}" if sid and len(sid) > 12 else None,
    }
    if not sid:
        report["status"] = "need_wps_sid"
        report["hint"] = (
            "将浏览器 Cookie wps_sid 写入 assets/config/auth.yaml，"
            "或设置环境变量 WPS_SID。获取方式见 references/ksheet-mcp-limitation.md"
        )
        report["auth_template"] = str(SKILL_ROOT / "assets" / "config" / "auth.yaml.template")
        _write_report(args.output, report)
        return NEED_SID

    dept = cfg.get("dept_report") or {}
    link_id = dept.get("link_id") or dept.get("url", "").rstrip("/").split("/")[-1]
    dept_format = (dept.get("format") or "").lower()

    cache = ensure_cache()
    content_path = cache / "dept-content.json"
    markdown_path = cache / "dept-report.md"

    if dept_format in ("ksheet", "xlsx", "xls", "et", "csv", "") or link_id:
        proc = run_drive(wps_root, ["get-file-content", link_id, "--json"])
        read_ok = proc.returncode == 0
        report["checks"]["dept_read"] = {
            "ok": read_ok,
            "link_id": link_id,
            "format": dept_format or "unknown",
        }
        if not read_ok:
            report["status"] = "dept_read_failed"
            report["error"] = (proc.stderr or proc.stdout or "")[:2000]
            report["hint"] = "WPS_SID 可能已过期，请从浏览器重新复制 wps_sid"
            _write_report(args.output, report)
            return FAIL

        try:
            text = proc.stdout.strip()
            idx = text.find("{")
            data = json.loads(text[idx:] if idx >= 0 else text)
        except json.JSONDecodeError as e:
            report["status"] = "dept_parse_failed"
            report["error"] = str(e)
            _write_report(args.output, report)
            return FAIL

        content_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        if data.get("content"):
            markdown_path.write_text(data["content"], encoding="utf-8")

        sheet_names = extract_sheet_names_from_content_json(data)
        resolved, reason = resolve_sheet_name(sheet_names, cfg)
        report["checks"]["dept_sheets"] = {
            "ok": bool(resolved),
            "all_sheets": sheet_names,
            "resolved_sheet": resolved,
            "resolve_reason": reason,
        }

        if not args.skip_download:
            dl = run_drive(wps_root, ["download", link_id, "--dir", str(cache)])
            report["checks"]["dept_download"] = {
                "ok": dl.returncode == 0,
                "dir": str(cache),
                "message": (dl.stdout or dl.stderr or "")[:500],
            }

    team = cfg.get("team_report") or {}
    team_link = team.get("link_id") or ""
    if team_link:
        proc = run_drive(wps_root, ["get-file-content", team_link, "--raw"])
        team_ok = proc.returncode == 0
        report["checks"]["team_read_via_wps365"] = {"ok": team_ok, "link_id": team_link}
        if team_ok and proc.stdout:
            (cache / "team-report.md").write_text(proc.stdout, encoding="utf-8")

    all_ok = all(
        c.get("ok")
        for k, c in report["checks"].items()
        if k in ("python_deps", "wps365_read", "wps_sid", "dept_read", "dept_sheets")
    )
    report["status"] = "ready" if all_ok else "partial"
    report["next_steps"] = []
    if all_ok:
        report["next_steps"] = [
            "python scripts/extract/extract_otl_weekly.py --markdown .cache/team-report.md",
            "python scripts/plan/plan_sheet_patches.py --config config.json --dept-kdc-json .cache/dept-content.json --extracted .cache/extracted.json",
        ]
    _write_report(args.output, report)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return OK if all_ok else FAIL


def _write_report(path: Path, report: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
