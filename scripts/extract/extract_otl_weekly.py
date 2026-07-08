#!/usr/bin/env python3
"""从 AI应用组式 otl 周报按日期区块 + ## 姓名 提取成员内容。"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date, datetime
from pathlib import Path


def parse_sections(md: str) -> list[tuple[str, str]]:
    """返回 [(date_label, body), ...] 按文档顺序。"""
    parts = re.split(r"^# (.+)$", md, flags=re.MULTILINE)
    sections: list[tuple[str, str]] = []
    # parts[0] is preamble; then date, body, date, body...
    i = 1
    while i < len(parts) - 1:
        label = parts[i].strip()
        body = parts[i + 1]
        sections.append((label, body))
        i += 2
    return sections


def pick_week_section(sections: list[tuple[str, str]], week: str | None) -> tuple[str, str]:
    if week:
        for label, body in sections:
            if week in label or label in week:
                return label, body
        raise SystemExit(f"未找到周次区块: {week}")

    dated: list[tuple[date, str, str]] = []
    for label, body in sections:
        m = re.search(r"(\d{4}-\d{2}-\d{2})", label)
        if m:
            dated.append((datetime.strptime(m.group(1), "%Y-%m-%d").date(), label, body))
    if not dated:
        raise SystemExit("文档中无 # YYYY-MM-DD 日期区块")

    today = date.today()
    # 文档通常最新周次在最上方：取 <= 今天 的最近一个日期区块
    eligible = [t for t in dated if t[0] <= today]
    if eligible:
        eligible.sort(key=lambda x: x[0], reverse=True)
        _, label, body = eligible[0]
        return label, body
    dated.sort(key=lambda x: x[0], reverse=True)
    _, label, body = dated[0]
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
    parser.add_argument("--week", default=None, help="日期标签，如 2026-07-02；默认取最新")
    parser.add_argument("--output", type=Path, default=Path(".cache/extracted.json"))
    args = parser.parse_args()

    md = args.markdown.read_text(encoding="utf-8")
    label, body = pick_week_section(parse_sections(md), args.week)
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
