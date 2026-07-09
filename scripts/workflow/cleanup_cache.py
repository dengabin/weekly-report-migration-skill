#!/usr/bin/env python3
"""清理当前 profile 的 .cache 中间产物；可选删除其 config.json。不触碰 wps365-read 凭证。"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))
from paths import cache_dir, default_config_path, workspace_root  # noqa: E402


def cleanup_cache(cache_dir_path: Path | None = None, *, dry_run: bool = False) -> dict:
    """删除 cache 目录下全部文件与子目录，保留空 .cache 文件夹。"""
    cache_dir_path = cache_dir_path or cache_dir()
    report: dict = {
        "cache_dir": str(cache_dir_path),
        "workspace_root": str(workspace_root()),
        "removed": [],
        "errors": [],
        "dry_run": dry_run,
    }

    if not cache_dir_path.exists():
        report["status"] = "no_cache_dir"
        report["count"] = 0
        return report

    for item in sorted(cache_dir_path.iterdir(), key=lambda p: p.name):
        rel = item.relative_to(cache_dir_path).as_posix()
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


def _maybe_remove_config(report: dict, *, dry_run: bool) -> None:
    config_path = default_config_path()
    if not config_path.exists():
        return
    rel = config_path.relative_to(workspace_root()).as_posix()
    try:
        if dry_run:
            report["removed"].append(rel)
        else:
            config_path.unlink()
            report["removed"].append(rel)
        report["count"] = len(report["removed"])
    except OSError as exc:
        report["errors"].append({"path": rel, "error": str(exc)})
        report["status"] = "partial"


def main() -> int:
    parser = argparse.ArgumentParser(description="清理周报迁移 .cache 中间产物")
    parser.add_argument("--cache-dir", type=Path, default=None, help="缓存目录，默认当前 profile 的 .cache")
    parser.add_argument(
        "--include-config",
        action="store_true",
        help=argparse.SUPPRESS,
    )
    parser.add_argument("--dry-run", action="store_true", help="仅列出将删除项，不实际删除")
    args = parser.parse_args()

    result = cleanup_cache(args.cache_dir, dry_run=args.dry_run)
    if args.include_config:
        _maybe_remove_config(result, dry_run=args.dry_run)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 1 if result.get("errors") else 0


if __name__ == "__main__":
    raise SystemExit(main())
