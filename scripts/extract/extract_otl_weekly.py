#!/usr/bin/env python3
"""从 otl 周报按日期区块 + ## 姓名 提取成员内容。"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))
from week_resolve import (  # noqa: E402
    parse_dated_sections,
    parse_relative_week_phrase,
    pick_latest_section_on_or_before,
    pick_section_for_calendar_week,
)


def parse_sections(md: str) -> list[tuple[str, str]]:
    """返回 [(date_label, body), ...] 按文档顺序。"""
    parts = re.split(r"^# (.+)$", md, flags=re.MULTILINE)
    sections: list[tuple[str, str]] = []
    i = 1
    while i < len(parts) - 1:
        label = parts[i].strip()
        body = parts[i + 1]
        sections.append((label, body))
        i += 2
    return sections


def pick_week_section(
    sections: list[tuple[str, str]],
    week: str | None = None,
    relative_weeks_ago: int | None = None,
    today: date | None = None,
) -> tuple[str, str]:
    dated = parse_dated_sections(sections)
    if not dated:
        raise SystemExit("文档中无 # YYYY-MM-DD 日期区块")

    if week:
        for label, body in sections:
            if week in label or label in week:
                return label, body
        raise SystemExit(f"未找到周次区块: {week}")

    if relative_weeks_ago is not None:
        label, body, _ = pick_section_for_calendar_week(dated, relative_weeks_ago, today)
        return label, body

    label, body, _ = pick_latest_section_on_or_before(dated, today)
    return label, body


def extract_members_from_body(body: str) -> dict[str, str]:
    members: dict[str, str] = {}
    chunks = re.split(r"^## (.+)$", body, flags=re.MULTILINE)
    i = 1
    while i < len(chunks) - 1:
        raw_name = chunks[i].strip()
        name = re.sub(r"@\S+", "", raw_name).strip()
        content = chunks[i + 1].strip()
        if name:
            members[name] = content
        i += 2
    return members


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--markdown", type=Path, required=True)
    parser.add_argument("--week", default=None, help="绝对日期标签，如 2026-07-02")
    parser.add_argument(
        "--relative-week",
        default=None,
        help="相对系统日历周次：0=本周，1=上周，2=上上周；或中文「上周」",
    )
    parser.add_argument("--output", type=Path, default=Path(".cache/extracted.json"))
    args = parser.parse_args()

    relative_weeks_ago: int | None = None
    if args.relative_week is not None:
        raw = str(args.relative_week).strip()
        if raw.isdigit():
            relative_weeks_ago = int(raw)
        else:
            relative_weeks_ago = parse_relative_week_phrase(raw)
            if relative_weeks_ago is None:
                raise SystemExit(f"无法解析相对周次: {raw!r}")

    md = args.markdown.read_text(encoding="utf-8")
    label, body = pick_week_section(
        parse_sections(md),
        week=args.week,
        relative_weeks_ago=relative_weeks_ago,
    )
    members = extract_members_from_body(body)

    payload = {
        "week_section": label,
        "member_count": len(members),
        "members": [{"name": n, "content": c, "char_count": len(c)} for n, c in members.items()],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    sys.stdout.reconfigure(encoding="utf-8") if hasattr(sys.stdout, "reconfigure") else None
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
