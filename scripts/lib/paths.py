"""Skill 根路径与 import 路径引导。"""
from __future__ import annotations

import sys
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parents[2]
CACHE = SKILL_ROOT / ".cache"
SCRIPTS_ROOT = SKILL_ROOT / "scripts"

DEPT_KSHEET_EXCLUDE = frozenset(
    {
        "dept-report-patched.ksheet",
        "dept-report-patched-zip.ksheet",
        "test-patch.ksheet",
    }
)


def find_dept_ksheet(cache: Path, cfg: dict | None = None) -> Path | None:
    """在 .cache 中选取用于 patch 的部门 ksheet（优先含 hypersublink 的原始下载件）。"""
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
