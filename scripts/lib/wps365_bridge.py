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
            SKILL_ROOT.parent / "testcase" / "ai-testcase-generate" / ".cursor" / "skills" / "wps365-read",
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
