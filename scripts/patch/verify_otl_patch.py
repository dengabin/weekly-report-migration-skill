#!/usr/bin/env python3
"""校验 otl 补丁：非目标块行集合应与原文一致。"""
from __future__ import annotations

import argparse
import hashlib
import re


def blocks_by_heading(md: str, headings: list[str]) -> dict[str, tuple[int, int]]:
    lines = md.splitlines()
    positions = {}
    for h in headings:
        for i, line in enumerate(lines):
            if line.strip() == h.strip():
                level = len(line) - len(line.lstrip("#"))
                end = len(lines)
                prefix = "#" * level + " "
                for j in range(i + 1, len(lines)):
                    if lines[j].startswith(prefix):
                        end = j
                        break
                positions[h] = (i, end)
                break
    return positions


def non_target_hash(md: str, spans: list[tuple[int, int]]) -> str:
    lines = md.splitlines()
    keep = []
    skip = set()
    for start, end in spans:
        skip.update(range(start, end))
    for i, line in enumerate(lines):
        if i not in skip:
            keep.append(line)
    digest = hashlib.sha256("\n".join(keep).encode("utf-8")).hexdigest()
    return digest


def main() -> int:
    parser = argparse.ArgumentParser(description="校验 otl 局部补丁")
    parser.add_argument("--original", required=True)
    parser.add_argument("--patched", required=True)
    parser.add_argument("--headings", nargs="+", required=True, help="被替换的成员标题，如 '## 张三'")
    args = parser.parse_args()

    orig = open(args.original, encoding="utf-8").read()
    patched = open(args.patched, encoding="utf-8").read()

    spans = list(blocks_by_heading(orig, args.headings).values())
    h1 = non_target_hash(orig, spans)
    h2 = non_target_hash(patched, spans)

    if h1 == h2:
        print("OK: 非目标区域一致")
        return 0
    print("FAIL: 非目标区域发生变化，可能发生了全量重建")
    print(f"original_hash={h1}")
    print(f"patched_hash={h2}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
