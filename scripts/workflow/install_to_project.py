#!/usr/bin/env python3
"""Install weekly-report-migration pointer Rule into a business project (cross-platform)."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))
from paths import SKILL_ROOT, profile_id_from_project  # noqa: E402


def install(skill_root: Path, target_project: Path, rule_name: str = "weekly-report-migration.mdc") -> dict:
    skill_root = skill_root.resolve()
    target_project = target_project.resolve()

    if not (skill_root / "SKILL.md").is_file():
        raise FileNotFoundError(f"Invalid skill directory (missing SKILL.md): {skill_root}")
    if skill_root == target_project:
        raise ValueError("TargetProject must not equal SkillRoot; run from a business project root.")

    template = skill_root / "templates" / "report-migration-pointer.mdc"
    if not template.is_file():
        raise FileNotFoundError(f"Missing template: {template}")

    profile_id = profile_id_from_project(target_project)
    profile_dir = skill_root / "profiles" / profile_id
    profile_dir.mkdir(parents=True, exist_ok=True)
    (profile_dir / ".cache").mkdir(parents=True, exist_ok=True)

    skill_root_posix = skill_root.as_posix()
    content = template.read_text(encoding="utf-8")
    content = content.replace("{{SKILL_ROOT}}", skill_root_posix)
    content = content.replace("{{PROFILE_ID}}", profile_id)

    rules_dir = target_project / ".cursor" / "rules"
    rules_dir.mkdir(parents=True, exist_ok=True)
    dest = rules_dir / rule_name
    dest.write_text(content, encoding="utf-8")

    return {
        "status": "ok",
        "skill_root": skill_root_posix,
        "target_project": str(target_project),
        "rule_path": str(dest),
        "profile_id": profile_id,
        "profile_dir": str(profile_dir),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Install pointer Rule into a business project")
    parser.add_argument("--skill-root", type=Path, required=True)
    parser.add_argument("--target-project", type=Path, default=Path.cwd())
    parser.add_argument("--rule-name", default="weekly-report-migration.mdc")
    args = parser.parse_args()

    try:
        report = install(args.skill_root, args.target_project, args.rule_name)
    except (FileNotFoundError, ValueError) as exc:
        print(json.dumps({"status": "error", "message": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 1

    print(json.dumps(report, ensure_ascii=False, indent=2))
    print(f"Installed rule: {report['rule_path']}")
    print(f"Profile: {report['profile_id']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
