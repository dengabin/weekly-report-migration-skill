"""Skill 根路径、按业务项目 profile 隔离的 config/.cache。"""
from __future__ import annotations

import hashlib
import os
import re
import sys
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_ROOT = SKILL_ROOT / "scripts"
PROFILES_DIR = SKILL_ROOT / "profiles"

DEPT_KSHEET_EXCLUDE = frozenset(
    {
        "dept-report-patched.ksheet",
        "dept-report-patched-zip.ksheet",
        "test-patch.ksheet",
    }
)


def profile_id_from_project(project_path: str | Path) -> str:
    """由业务项目绝对路径生成稳定 profile id（安装指针 Rule 时用）。"""
    resolved = str(Path(project_path).resolve())
    digest = hashlib.sha256(resolved.encode("utf-8")).hexdigest()[:10]
    base = Path(resolved).name
    slug = re.sub(r"[^a-zA-Z0-9_-]+", "-", base).strip("-").lower()[:24] or "project"
    return f"{slug}-{digest}"


def get_profile_id() -> str | None:
    env = os.environ.get("REPORT_MIGRATION_PROFILE", "").strip()
    if env:
        return env
    active = SKILL_ROOT / ".active-profile"
    if active.exists():
        text = active.read_text(encoding="utf-8").strip()
        return text or None
    return None


def set_active_profile(profile_id: str) -> Path:
    """写入当前会话使用的 profile（Agent 从指针 Rule 读取 PROFILE 后调用）。"""
    profile_id = profile_id.strip()
    if not profile_id:
        raise ValueError("profile_id 不能为空")
    (SKILL_ROOT / ".active-profile").write_text(profile_id + "\n", encoding="utf-8")
    workspace_root()  # ensure dirs
    return workspace_root()


def workspace_root() -> Path:
    """config.json 与 .cache 所在目录；无 profile 时兼容旧版 SKILL_ROOT 根目录。"""
    pid = get_profile_id()
    if pid:
        d = PROFILES_DIR / pid
        d.mkdir(parents=True, exist_ok=True)
        return d
    return SKILL_ROOT


def default_config_path() -> Path:
    wr = workspace_root()
    cfg = wr / "config.json"
    if cfg.exists():
        return cfg
    root_cfg = SKILL_ROOT / "config.json"
    if wr != SKILL_ROOT and root_cfg.exists():
        return root_cfg
    return cfg


def resolve_config_path(arg: str | Path | None = None) -> Path:
    if arg is None or str(arg) in ("", "config.json"):
        return default_config_path()
    p = Path(arg)
    return p if p.is_absolute() else workspace_root() / p


def cache_dir() -> Path:
    d = workspace_root() / ".cache"
    d.mkdir(parents=True, exist_ok=True)
    return d


# 兼容旧 import；新代码请用 cache_dir()
CACHE = cache_dir()


def find_dept_ksheet(cache: Path | None = None, cfg: dict | None = None) -> Path | None:
    """在 .cache 中选取用于 patch 的部门 ksheet（优先含 hypersublink 的原始下载件）。"""
    cache = cache or cache_dir()
    exclude = set(DEPT_KSHEET_EXCLUDE)
    if cache.exists():
        exclude.update(p.name for p in cache.glob("dept-report-patched*.ksheet"))
    candidates = [
        p
        for p in cache.glob("*.ksheet")
        if p.name not in exclude and not p.name.startswith("test")
    ]
    title = ((cfg or {}).get("dept_report") or {}).get("title", "")
    titled = [p for p in candidates if title and title in p.name]
    if titled:
        candidates = titled
    if not candidates:
        return None

    def quality(path: Path) -> tuple[int, int]:
        try:
            import zipfile

            with zipfile.ZipFile(path) as z:
                if "customXml/item2.xml" not in z.namelist():
                    return (0, path.stat().st_size)
                links = z.read("customXml/item2.xml").count(b"hypersublink")
                return (links, path.stat().st_size)
        except OSError:
            return (0, 0)

    return max(candidates, key=quality)


def setup_sys_path(*subpackages: str) -> None:
    """将 scripts/lib 及指定子包加入 sys.path。"""
    for name in ("lib", *subpackages):
        p = SCRIPTS_ROOT / name
        s = str(p)
        if s not in sys.path:
            sys.path.insert(0, s)
