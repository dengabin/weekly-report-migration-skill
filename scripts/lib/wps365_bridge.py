"""wps365-read 桥接：路径发现、凭证加载、子进程调用。"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    yaml = None

from paths import CACHE, SKILL_ROOT

AUTH_CANDIDATES = [
    SKILL_ROOT / "assets" / "config" / "auth.yaml",
]


def find_wps365_read_root(cfg: dict | None = None) -> Path | None:
    cfg = cfg or {}
    wps_cfg = cfg.get("wps365_read") or {}
    explicit = (wps_cfg.get("root") or "").strip()
    if explicit:
        p = Path(explicit).expanduser()
        if (p / "skills" / "drive" / "run.py").exists():
            return p.resolve()

    candidates: list[Path] = []
    env_root = os.environ.get("WPS365_READ_ROOT", "").strip()
    if env_root:
        candidates.append(Path(env_root))

    candidates.extend(
        [
            SKILL_ROOT / "vendor" / "wps365-read",
            Path.home() / ".cursor" / "skills" / "wps365-read",
            Path.home() / ".agents" / "skills" / "wps365-read",
        ]
    )

    cwd = Path.cwd().resolve()
    for ancestor in [cwd, *cwd.parents]:
        candidates.append(ancestor / ".cursor" / "skills" / "wps365-read")
        if (ancestor / ".git").exists() and ancestor != cwd:
            break

    seen: set[str] = set()
    for base in candidates:
        key = str(base)
        if key in seen:
            continue
        seen.add(key)
        if (base / "skills" / "drive" / "run.py").exists():
            return base.resolve()
    return None


def discover_wps365_read_glob() -> Path | None:
    """在常见目录树中搜索 wps365-read，无需用户手填路径。"""
    search_roots: list[Path] = []
    for base in (SKILL_ROOT, SKILL_ROOT.parent, Path.home() / ".cursor" / "skills"):
        if base.exists():
            search_roots.append(base.resolve())

    seen: set[str] = set()
    for base in search_roots:
        try:
            for run_py in base.glob("**/wps365-read/skills/drive/run.py"):
                root = run_py.resolve().parent.parent.parent
                key = str(root)
                if key in seen:
                    continue
                seen.add(key)
                if root.name == "wps365-read":
                    return root
        except OSError:
            continue
    return None


def install_wps365_read(cfg: dict | None = None) -> tuple[Path | None, str]:
    """
    尝试为用户环境准备 wps365-read。
    返回 (root, message)。
    """
    cfg = cfg or {}
    wps_cfg = cfg.get("wps365_read") or {}
    target = SKILL_ROOT / "vendor" / "wps365-read"

    existing = find_wps365_read_root(cfg)
    if existing:
        return existing, f"已存在: {existing}"

    discovered = discover_wps365_read_glob()
    if discovered:
        # 优先落到本 Skill vendor/，避免依赖其它项目里的副本
        vendor = SKILL_ROOT / "vendor" / "wps365-read"
        if not (vendor / "skills" / "drive" / "run.py").exists():
            import shutil

            vendor.parent.mkdir(parents=True, exist_ok=True)
            if vendor.exists():
                shutil.rmtree(vendor, ignore_errors=True)
            shutil.copytree(
                discovered,
                vendor,
                ignore=shutil.ignore_patterns("auth.yaml", "__pycache__", ".git"),
            )
            return vendor.resolve(), f"已复制到 {vendor}"
        return vendor.resolve(), f"使用本 Skill vendor: {vendor}"

    repo_url = (os.environ.get("WPS365_READ_REPO_URL") or wps_cfg.get("repo_url") or "").strip()
    if repo_url:
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            import shutil

            shutil.rmtree(target, ignore_errors=True)
        proc = subprocess.run(
            ["git", "clone", "--depth", "1", repo_url, str(target)],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        if proc.returncode == 0 and (target / "skills" / "drive" / "run.py").exists():
            return target.resolve(), f"已从仓库安装到 {target}"
        err = (proc.stderr or proc.stdout or "clone failed")[:500]
        return None, f"git clone 失败: {err}"

    return (
        None,
        "未找到 wps365-read。Agent 应执行 setup_wps365_read.py；"
        "若仍失败，在 config.json 设置 wps365_read.repo_url 或环境变量 WPS365_READ_REPO_URL",
    )


def ensure_wps365_read(cfg: dict | None = None, *, write_config_root: Path | None = None) -> Path | None:
    """发现或安装 wps365-read；可选将 root 写回 config.json。"""
    cfg = cfg or {}
    if find_wps365_read_root(cfg):
        return find_wps365_read_root(cfg)

    auto = (cfg.get("wps365_read") or {}).get("auto_install", True)
    if not auto:
        return None

    root, _msg = install_wps365_read(cfg)
    if root and write_config_root and write_config_root.exists():
        data = json.loads(write_config_root.read_text(encoding="utf-8"))
        data.setdefault("wps365_read", {})["root"] = str(root)
        write_config_root.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return root


def _read_auth_yaml(path: Path) -> str | None:
    if not path.exists() or yaml is None:
        return None
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        sid = (data.get("wps") or {}).get("sid", "")
        if sid and sid != "<wps_sid>":
            return sid.strip()
    except Exception:
        return None
    return None


def resolve_wps_sid(cfg: dict | None = None) -> tuple[str | None, str]:
    """返回 (sid, source_description)。"""
    for path in AUTH_CANDIDATES:
        sid = _read_auth_yaml(path)
        if sid:
            os.environ["WPS_SID"] = sid
            return sid, str(path)

    env_sid = os.environ.get("WPS_SID", "").strip()
    if env_sid:
        return env_sid, "environment:WPS_SID"

    root = find_wps365_read_root(cfg)
    if root:
        sid = _read_auth_yaml(root / "assets" / "config" / "auth.yaml")
        if sid:
            os.environ["WPS_SID"] = sid
            return sid, str(root / "assets" / "config" / "auth.yaml")

    return None, "missing"


def write_skill_auth(sid: str) -> Path:
    auth_path = SKILL_ROOT / "assets" / "config" / "auth.yaml"
    auth_path.parent.mkdir(parents=True, exist_ok=True)
    if yaml is None:
        auth_path.write_text(
            f'wps:\n  sid: "{sid}"\n  api_base: "https://api.wps.cn"\n',
            encoding="utf-8",
        )
    else:
        data = {"wps": {"sid": sid, "api_base": "https://api.wps.cn"}}
        auth_path.write_text(yaml.dump(data, allow_unicode=True, default_flow_style=False), encoding="utf-8")
    os.environ["WPS_SID"] = sid
    return auth_path


def run_drive(
    wps_root: Path,
    args: list[str],
    *,
    timeout: int = 300,
) -> subprocess.CompletedProcess:
    cmd = [sys.executable, "skills/drive/run.py", *args]
    env = os.environ.copy()
    return subprocess.run(
        cmd,
        cwd=str(wps_root),
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
    )


def drive_json(wps_root: Path, args: list[str]) -> dict:
    proc = run_drive(wps_root, [*args, "--json"])
    if proc.returncode != 0:
        raise RuntimeError((proc.stderr or proc.stdout or "wps365-read failed").strip())
    text = proc.stdout.strip()
    # 输出可能含 Markdown 前缀，取 JSON 块
    if text.startswith("{"):
        return json.loads(text)
    idx = text.find("{")
    if idx >= 0:
        return json.loads(text[idx:])
    raise RuntimeError(f"非 JSON 输出: {text[:500]}")


def ensure_cache() -> Path:
    CACHE.mkdir(parents=True, exist_ok=True)
    return CACHE
