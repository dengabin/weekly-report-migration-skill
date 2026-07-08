#!/usr/bin/env python3
"""写入本 Skill 的 WPS_SID（Agent 向用户收集后调用）。"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))
from wps365_bridge import write_skill_auth  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("sid", help="浏览器 Cookie 中的 wps_sid 值")
    args = parser.parse_args()
    sid = args.sid.strip()
    if len(sid) < 8:
        print("WPS_SID 过短，请检查是否完整复制", file=sys.stderr)
        return 1
    path = write_skill_auth(sid)
    print(f"已写入 {path}")
    print("请重新运行: python scripts/workflow/preflight.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
