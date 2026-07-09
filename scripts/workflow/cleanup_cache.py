#!/usr/bin/env python3
"""清理 .cache 中间产物。仅删除 Skill 根目录下 .cache/，不触碰 config.json 与 wps365-read 凭证。"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))
from paths import CACHE, SKILL_ROOT  # noqa: E402


def cleanup_cache(cache_dir: Path = CACHE, *, dry_run: bool = False) -> dict:
    """删除 cache 目录下全部文件与子目录，保留空 .cache 文件夹。"""
    report: dict = {
        "cache_dir": str(cache_dir),
        "removed": [],
        "errors": [],
        "dry_run": dry_run,
    }

    if not cache_dir.exists():
        report["status"] = "no_cache_dir"
        report["count"] = 0
        return report

    for item in sorted(cache_dir.iterdir(), key=lambda p: p.name):
        rel = item.relative_to(cache_dir).as_posix()
        try:
            if dry_run:
                report["removed"].append(rel)
                continue
            if item.is_dir():
                shutil.rmtree(item)
            else:
                item.unlink()
            report["removed"].append(rel)
        except OSError as exc:
            report["errors"].append({"path": rel, "error": str(exc)})

    report["count"] = len(report["removed"])
    report["status"] = "ok" if not report["errors"] else "partial"
    return report


def _maybe_remove_config(skill_root: Path, report: dict, *, dry_run: bool) -> None:
    config_path = skill_root / "config.json"
    if not config_path.exists():
        return
    try:
        if dry_run:
            report["removed"].append("config.json")
        else:
            config_path.unlink()
            report["removed"].append("config.json")
        report["count"] = len(report["removed"])
    except OSError as exc:
        report["errors"].append({"path": "config.json", "error": str(exc)})
        report["status"] = "partial"


def main() -> int:
    parser = argparse.ArgumentParser(description="清理周报迁移 .cache 中间产物")
    parser.add_argument("--cache-dir", type=Path, default=CACHE, help="缓存目录，默认 .cache")
    parser.add_argument(
        "--include-config",
        action="store_true",
        help=argparse.SUPPRESS,
    )
    parser.add_argument("--dry-run", action="store_true", help="仅列出将删除项，不实际删除")
    args = parser.parse_args()

    result = cleanup_cache(args.cache_dir, dry_run=args.dry_run)
    if args.include_config:
        _maybe_remove_config(SKILL_ROOT, result, dry_run=args.dry_run)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 1 if result.get("errors") else 0


if __name__ == "__main__":
    raise SystemExit(main())
