#!/usr/bin/env python3
"""将 otl Markdown 列表转为部门 ksheet 排版（按每人历史周列参考）。"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Literal

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))
from paths import SKILL_ROOT  # noqa: E402

StyleKind = Literal["plain_project", "bullet_topic", "circle_topic"]

SECTION_RE = re.compile(
    r"^(\s*)- (本周工作总结|下周工作计划|需要协助的内容|本周工作|下周工作)(.*)$"
)
DASH_ITEM_RE = re.compile(r"^(\s*)- (.*)$")
NUMBER_ITEM_RE = re.compile(r"^(\s*)(\d+)[.、]\s*(.*)$")


def infer_style(reference: str | None) -> StyleKind:
    """从同行历史周列推断列表风格。"""
    if not reference or len(reference.strip()) < 30:
        return "circle_topic"
    lines = reference.split("\n")
    in_summary = False
    for line in lines:
        if "本周工作总结" in line:
            in_summary = True
            continue
        if not in_summary or not line.strip():
            continue
        if line.startswith("    • "):
            return "bullet_topic"
        if line.startswith("    ◦ "):
            return "circle_topic"
        if line.strip().startswith("【"):
            return "plain_project"
        if line.startswith("• 下周") or line.startswith("• 需要"):
            break
    if "    • " in reference:
        return "bullet_topic"
    if "    ◦ " in reference:
        return "circle_topic"
    return "plain_project"


def _section_line(line: str) -> str:
    m = SECTION_RE.match(line)
    if not m:
        return line
    lead, title, tail = m.group(1), m.group(2), m.group(3)
    return f"{lead}• {title}{tail}"


def _pad(level: int) -> str:
    return " " * (4 * level)

def _format_dash_item(indent: int, body: str, style: StyleKind) -> str:
    if style == "plain_project":
        if indent == 0 and body.startswith("【"):
            return body
        if indent <= 4:
            return f"    ◦ {body}"
        if indent <= 8:
            return f"        ▪ {body}"
        return f"{' ' * indent}▪ {body}"

    if style == "bullet_topic":
        if indent == 0:
            return f"    • {body}"
        if indent <= 4:
            return f"        ◦ {body}"
        if indent <= 8:
            return f"            ▪ {body}"
        return f"{' ' * indent}▪ {body}"

    # circle_topic
    if indent == 0 and body.startswith("【"):
        return f"    ◦ {body}"
    if indent <= 4:
        return f"    ◦ {body}"
    if indent <= 8:
        return f"        ▪ {body}"
    return f"{' ' * indent}▪ {body}"


def format_line(line: str, style: StyleKind) -> str:
    if not line.strip():
        return line

    if SECTION_RE.match(line):
        return _section_line(line)

    m = DASH_ITEM_RE.match(line)
    if m:
        return _format_dash_item(len(m.group(1)), m.group(2), style)

    m = NUMBER_ITEM_RE.match(line)
    if m:
        indent, body = len(m.group(1)), m.group(3)
        if style == "bullet_topic":
            if indent <= 4:
                return f"        {body}"
            return f"{' ' * (indent + 4)}{body}"
        if indent <= 4:
            return f"    {body}"
        return f"{' ' * indent}{body}"

    stripped = line.lstrip()
    if stripped.startswith("【"):
        return stripped
    return line


def _is_table_line(line: str) -> bool:
    stripped = line.strip()
    return stripped.startswith("|") or stripped.startswith("|---")


def _is_continuation_line(line: str) -> bool:
    if not line.strip():
        return False
    if SECTION_RE.match(line):
        return False
    if DASH_ITEM_RE.match(line):
        return False
    if NUMBER_ITEM_RE.match(line):
        return False
    if _is_table_line(line):
        return False
    if line.lstrip().startswith("##"):
        return False
    return True


def _continuation_indent(last_raw_indent: int, line: str) -> str:
    """otl 中嵌套列表下的无 `-` 续行（如二级功能表格行）保留层级缩进。"""
    raw_lead = len(line) - len(line.lstrip())
    body = line.strip()
    if raw_lead > 0:
        return line
    pad = last_raw_indent + 4
    return f"{' ' * pad}{body}"


def format_otl_content(text: str, reference: str | None = None) -> str:
    style = infer_style(reference)
    out: list[str] = []
    last_raw_indent = 0

    for line in text.split("\n"):
        if not line.strip():
            out.append(line)
            continue

        if SECTION_RE.match(line):
            last_raw_indent = 0
            out.append(_section_line(line))
            continue

        m = DASH_ITEM_RE.match(line)
        if m:
            last_raw_indent = len(m.group(1))
            out.append(_format_dash_item(last_raw_indent, m.group(2), style))
            continue

        if _is_continuation_line(line) and last_raw_indent > 0:
            out.append(_continuation_indent(last_raw_indent, line))
            continue

        out.append(format_line(line, style))

    return "\n".join(out)


def _detect_name_col_from_rows(rows: list) -> int:
    """从表头推断姓名列（0-based）。"""
    if not rows:
        return 1
    for j, cell in enumerate(rows[0]):
        text = str(cell or "").strip()
        if "姓名" in text or "名字" in text or "name" in text.lower():
            return j
    return 1


def _detect_first_content_col(rows: list, name_col: int) -> int:
    """找到姓名列之后第一个含实际内容（非链接、非空）的列索引。"""
    for i in range(1, min(6, len(rows))):
        row = rows[i]
        for j in range(name_col + 1, len(row)):
            text = str(row[j] or "").strip()
            if text and not text.startswith("📄"):
                return j
    return name_col + 1


def load_reference_by_name(kdc_path: Path, sheet_name: str, ref_col_index: int | None = None) -> dict[str, str]:
    """从 KDC JSON 读取每人历史周列文本作为格式参考。"""
    from sheet_utils import find_sheet_in_kdc, kdc_sheet_to_rows

    data = json.loads(kdc_path.read_text(encoding="utf-8"))
    raw = data.get("raw") or data
    sheet = find_sheet_in_kdc(raw, sheet_name)
    if not sheet:
        return {}
    rows = kdc_sheet_to_rows(sheet)
    name_col = _detect_name_col_from_rows(rows)
    if ref_col_index is None:
        ref_col_index = _detect_first_content_col(rows, name_col)
    refs: dict[str, str] = {}
    for row in rows[1:]:
        if len(row) <= name_col:
            continue
        name = (row[name_col] or "").strip()
        if not name or name in ("部门周报",):
            continue
        ref = row[ref_col_index] if len(row) > ref_col_index else ""
        if ref and not str(ref).strip().startswith("📄"):
            refs[name] = ref
    return refs


def format_extracted_file(
    extracted_path: Path,
    *,
    references: dict[str, str] | None = None,
    ref_col_index: int | None = None,
    kdc_path: Path | None = None,
    sheet_name: str | None = None,
) -> None:
    data = json.loads(extracted_path.read_text(encoding="utf-8"))
    refs = references or {}
    if kdc_path and sheet_name:
        refs = {**load_reference_by_name(kdc_path, sheet_name, ref_col_index), **refs}

    for m in data.get("members", []):
        raw = m.get("content_raw") or m.get("content", "")
        if "content_raw" not in m:
            m["content_raw"] = raw
        ref = refs.get(m["name"])
        m["content"] = format_otl_content(raw, ref)
        m["char_count"] = len(m["content"])
        m["format_style"] = infer_style(ref)

    extracted_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="格式化 extracted.json 供 ksheet 写入")
    parser.add_argument("--input", type=Path, default=Path(".cache/extracted.json"))
    parser.add_argument("--kdc-json", type=Path, default=Path(".cache/dept-content.json"))
    parser.add_argument("--sheet-name", default=None, help="部门子表名，默认从 config.json 读取")
    parser.add_argument("--ref-col-index", type=int, default=None, help="历史周列 0-based 索引；默认按表结构自动检测")
    parser.add_argument("--in-place", action="store_true")
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()

    sheet_name = args.sheet_name
    if not sheet_name:
        for cfg_path in (Path("config.json"), SKILL_ROOT / "config.json"):
            if cfg_path.exists():
                cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
                sheet_name = (cfg.get("dept_sheet") or {}).get("sheet_name")
                if sheet_name:
                    break
        if not sheet_name:
            preflight = Path(".cache/preflight-report.json")
            if preflight.exists():
                pr = json.loads(preflight.read_text(encoding="utf-8"))
                sheet_name = ((pr.get("checks") or {}).get("dept_sheets") or {}).get("resolved_sheet")

    out = args.input if args.in_place else (args.output or args.input)
    kdc = args.kdc_json if args.kdc_json.exists() else None
    format_extracted_file(
        args.input,
        kdc_path=kdc,
        sheet_name=sheet_name,
        ref_col_index=args.ref_col_index,
    )
    if not args.in_place and args.output:
        data = json.loads(args.input.read_text(encoding="utf-8"))
        args.output.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    print(json.dumps({"output": str(out), "kdc": str(kdc) if kdc else None}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
