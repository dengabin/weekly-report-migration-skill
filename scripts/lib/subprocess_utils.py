"""子进程与标准流 UTF-8 配置（Windows 下避免中文乱码 / 解码错误）。"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


def configure_stdio() -> None:
    """主进程 stdout/stderr 统一 UTF-8。"""
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            try:
                stream.reconfigure(encoding="utf-8", errors="replace")
            except (OSError, ValueError):
                pass


def skill_subprocess_env() -> dict[str, str]:
    """子 Python 进程强制 UTF-8 模式。"""
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUTF8"] = "1"
    return env


def run_skill_cmd(cmd: list[str], *, cwd: Path | str) -> int:
    """执行 Skill 内脚本链，继承 UTF-8 环境。"""
    return subprocess.call(cmd, cwd=str(cwd), env=skill_subprocess_env())
