# -*- coding: utf-8 -*-
"""
导入时自动读取 auth.yaml，将配置注入 os.environ。

优先级策略：auth.yaml > 环境变量。
auth.yaml 是用户主动维护的本地配置文件，比可能残留在系统中的旧环境变量更可信。
当 auth.yaml 包含有效（非占位符）SID 时，始终覆盖环境变量。

多路径搜索策略：
1. __file__ 相对路径定位 auth.yaml
2. cwd 向上递归查找 .cursor/skills/wps365-read/assets/config/auth.yaml
3. 若 auth.yaml 不存在或无效，回退使用已有的 WPS_SID 环境变量
"""
import os
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    yaml = None


def _find_auth_yaml() -> "Path | None":
    """多路径搜索 auth.yaml，返回首个存在的路径。"""
    # 路径 1：基于 __file__ 的相对路径
    p1 = Path(__file__).resolve().parent.parent / "assets" / "config" / "auth.yaml"
    if p1.exists():
        return p1

    # 路径 2：从 cwd 向上查找 workspace root（含 .cursor/skills/wps365-read/）
    cwd = Path.cwd().resolve()
    for ancestor in [cwd, *cwd.parents]:
        p2 = ancestor / ".cursor" / "skills" / "wps365-read" / "assets" / "config" / "auth.yaml"
        if p2.exists():
            return p2
        if (ancestor / ".git").exists():
            break  # 到 git 根就停止向上

    return None


def _load_and_inject():
    """读取 auth.yaml 并注入环境变量。auth.yaml 优先于已有环境变量。"""
    config_path = _find_auth_yaml()

    if not config_path:
        if "WPS_SID" not in os.environ:
            print(
                "[wps365-read] 警告: 未找到 auth.yaml 且 WPS_SID 环境变量未设置。\n"
                "  解决方式: 设置环境变量 $env:WPS_SID = '<your_sid>' 或确认 "
                ".cursor/skills/wps365-read/assets/config/auth.yaml 存在。",
                file=sys.stderr,
            )
        return

    if yaml is None:
        print(
            "[wps365-read] 警告: pyyaml 未安装，无法读取 auth.yaml。\n"
            "  解决方式: pip install pyyaml 或设置环境变量 $env:WPS_SID",
            file=sys.stderr,
        )
        return

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            cfg = yaml.safe_load(f) or {}
    except Exception as e:
        print(f"[wps365-read] 警告: 读取 {config_path} 失败: {e}", file=sys.stderr)
        return

    wps = cfg.get("wps", {})

    sid = wps.get("sid", "")
    if sid and sid != "<wps_sid>":
        os.environ["WPS_SID"] = sid
    elif "WPS_SID" not in os.environ:
        print(
            "[wps365-read] 警告: auth.yaml 中 wps.sid 为空或为占位符。\n"
            "  解决方式: 设置环境变量 $env:WPS_SID = '<your_sid>'",
            file=sys.stderr,
        )

    api_base = wps.get("api_base", "")
    if api_base:
        os.environ["WPS_API_BASE"] = api_base


# 模块导入时自动执行
_load_and_inject()