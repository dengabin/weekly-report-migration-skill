#!/usr/bin/env python3
"""从小组周报 Markdown 中按 config 规则提取每位成员内容。"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


def load_config(path: Path) -> dict:
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def load_markdown(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def normalize_week(s: str) -> str:
    return s.strip().replace("／", "/").replace("－", "-")


def extract_by_heading(md: str, heading: str, level: int) -> str:
    lines = md.splitlines()
    start = None
    for i, line in enumerate(lines):
        if line.strip() == heading.strip():
            start = i + 1
            break
    if start is None:
        return ""
    prefix = "#" * level + " "
    end = len(lines)
    for j in range(start, len(lines)):
        if lines[j].startswith(prefix) and not lines[j].startswith("#" * (level + 1)):
            end = j
            break
    return "\n".join(lines[start:end]).strip()


def extract_by_regex(md: str, start_pat: str, end_pat: str, flags: str = "m") -> str:
    re_flags = 0
    if "m" in flags:
        re_flags |= re.MULTILINE
    if "i" in flags:
        re_flags |= re.IGNORECASE
    m = re.search(start_pat, md, re_flags)
    if not m:
        return ""
    rest = md[m.end() :]
    if end_pat:
        m2 = re.search(end_pat, rest, re_flags)
        if m2:
            rest = rest[: m2.start()]
    return rest.strip()


def extract_member(md: str, member: dict, options: dict) -> str:
    rule = member.get("extract", {})
    name = member["name"]
    t = rule.get("type", "heading")

    if t == "heading":
        heading = rule.get("heading", f"## {name}").replace("{name}", name)
        level = int(rule.get("level", heading.count("#", 0, heading.find(" ")) or 2))
        content = extract_by_heading(md, heading, level)
    elif t == "regex":
        content = extract_by_regex(
            md,
            rule.get("start", "").replace("{name}", re.escape(name)),
            rule.get("end", ""),
            rule.get("flags", "m"),
        )
    elif t == "table_row":
        content = _extract_table_row(md, member, rule)
    else:
        raise ValueError(f"未知 extract.type: {t}")

    if options.get("trim_content", True):
        content = content.strip()
    return content


def _extract_table_row(md: str, member: dict, rule: dict) -> str:
    name = member["name"]
    name_idx = int(rule.get("name_column_index", 0))
    content_idx = int(rule.get("content_column_index", 1))
    for line in md.splitlines():
        if not line.strip().startswith("|"):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) <= max(name_idx, content_idx):
            continue
        if name in cells[name_idx] or cells[name_idx] == name:
            return cells[content_idx]
    return ""


def main() -> int:
    parser = argparse.ArgumentParser(description="提取小组周报各成员内容")
    parser.add_argument("--config", type=Path, default=Path("config.json"))
    parser.add_argument("--markdown", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path(".cache/extracted.json"))
    args = parser.parse_args()

    cfg = load_config(args.config)
    md = load_markdown(args.markdown)
    options = cfg.get("options", {})

    results = []
    for member in cfg.get("members", []):
        content = extract_member(md, member, options)
        results.append(
            {
                "name": member["name"],
                "content": content,
                "char_count": len(content),
                "empty": not bool(content),
            }
        )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "week": cfg.get("week"),
        "team_name": cfg.get("team_name"),
        "members": results,
    }
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    empty = [r["name"] for r in results if r["empty"]]
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    if empty:
        print(f"\n警告: 以下成员内容为空: {', '.join(empty)}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
