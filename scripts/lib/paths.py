"""Skill 根路径与 import 路径引导。"""
from __future__ import annotations

import sys
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parents[2]
CACHE = SKILL_ROOT / ".cache"
SCRIPTS_ROOT = SKILL_ROOT / "scripts"


def setup_sys_path(*subpackages: str) -> None:
    """将 scripts/lib 及指定子包加入 sys.path。"""
    for name in ("lib", *subpackages):
        p = SCRIPTS_ROOT / name
        s = str(p)
        if s not in sys.path:
            sys.path.insert(0, s)
