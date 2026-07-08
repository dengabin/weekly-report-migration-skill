#!/usr/bin/env python3
"""自动发现或安装 wps365-read，用户无需手动配置路径。"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))
from paths import SKILL_ROOT  # noqa: E402
from wps365_bridge import ensure_wps365_read, find_wps365_read_root, install_wps365_read  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="准备 wps365-read 运行环境")
    parser.add_argument("--config", type=Path, default=SKILL_ROOT / "config.json")
    parser.add_argument("--repo-url", default=None, help="覆盖 config / 环境变量的 git 仓库地址")
    args = parser.parse_args()

    cfg: dict = {}
    if args.config.exists():
        cfg = json.loads(args.config.read_text(encoding="utf-8"))
    if args.repo_url:
        cfg.setdefault("wps365_read", {})["repo_url"] = args.repo_url

    root = find_wps365_read_root(cfg)
    if root:
        print(json.dumps({"status": "ok", "root": str(root), "source": "existing"}, ensure_ascii=False, indent=2))
        return 0

    root = ensure_wps365_read(cfg, write_config_root=args.config if args.config.exists() else None)
    if root:
        print(json.dumps({"status": "ok", "root": str(root), "source": "installed"}, ensure_ascii=False, indent=2))
        return 0

    _, msg = install_wps365_read(cfg)
    print(json.dumps({"status": "need_wps365_read", "error": msg}, ensure_ascii=False, indent=2), file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
