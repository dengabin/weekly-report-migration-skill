"""Excel/ksheet 列宽估算（OpenXML <col width> 字符单位）。"""
from __future__ import annotations

import re

MIN_COL_WIDTH = 14.0
# 周内容列上限：单元格已自动换行，不必按最长行撑满；对齐部门表 F 列量级（~49）
MAX_COL_WIDTH = 55.0
DEFAULT_COL_WIDTH = 49.375


def text_display_width(s: str) -> int:
    """估算一行文本在表格中的显示宽度（CJK 计 2，ASCII 计 1）。"""
    w = 0
    for ch in s:
        if ch == "\t":
            w += 4
        elif ord(ch) > 127:
            w += 2
        else:
            w += 1
    return w


def excel_col_width_from_text(
    text: str,
    *,
    min_width: float = MIN_COL_WIDTH,
    max_width: float = MAX_COL_WIDTH,
) -> float:
    if not text or not str(text).strip():
        return min_width
    normalized = str(text).replace("\r\n", "\n").replace("\r", "\n")
    lines = normalized.split("\n")
    max_line = max(text_display_width(line) for line in lines)
    # 经验系数：对齐部门表里既有周列的视觉宽度
    width = max_line * 0.88 + 2.5
    return max(min_width, min(max_width, width))


def excel_col_width_from_texts(
    texts: list[str],
    *,
    min_width: float = MIN_COL_WIDTH,
    max_width: float = MAX_COL_WIDTH,
) -> float:
    if not texts:
        return DEFAULT_COL_WIDTH
    return max(
        excel_col_width_from_text(t, min_width=min_width, max_width=max_width)
        for t in texts
        if t is not None
    )


def parse_excel_width(width: str | float | None) -> float | None:
    if width is None:
        return None
    try:
        return float(width)
    except (TypeError, ValueError):
        return None


def col_width_at(sheet_xml: str, col_index: int) -> float | None:
    """读取 sheet.xml 中某列（1-based）的 width，支持 <col min max> 区间。"""
    cols_m = re.search(r"<cols>(.*?)</cols>", sheet_xml, re.DOTALL)
    if not cols_m:
        return None
    best: float | None = None
    best_span = 10**9
    for m in re.finditer(r"<col\b[^>]*/>", cols_m.group(1)):
        tag = m.group(0)
        mi = re.search(r'min="(\d+)"', tag)
        ma = re.search(r'max="(\d+)"', tag)
        wm = re.search(r'width="([^"]+)"', tag)
        if not mi or not ma or not wm:
            continue
        min_v, max_v = int(mi.group(1)), int(ma.group(1))
        if min_v <= col_index <= max_v:
            w = parse_excel_width(wm.group(1))
            if w is None:
                continue
            span = max_v - min_v
            if span < best_span:
                best_span = span
                best = w
    return best


def upsert_col_width_in_sheet_xml(sheet_xml: str, col_index: int, width: float) -> str:
    """设置单列宽度；仅加宽至目标，或把已超过上限的列压回 MAX_COL_WIDTH。"""
    width = max(MIN_COL_WIDTH, min(MAX_COL_WIDTH, width))
    current = col_width_at(sheet_xml, col_index)
    if current is not None:
        if current > MAX_COL_WIDTH:
            width = MAX_COL_WIDTH
        elif current >= width - 0.05:
            return sheet_xml

    width_str = f"{width:.3f}"
    cols_m = re.search(r"<cols>(.*?)</cols>", sheet_xml, re.DOTALL)
    if not cols_m:
        return sheet_xml

    inner = cols_m.group(1)
    exact_pat = rf'(<col\b[^>]*\bmin="{col_index}"[^>]*\bmax="{col_index}"[^>]*width=")([^"]+)(")'
    m = re.search(exact_pat, inner)
    if m:
        new_inner = inner[: m.start(2)] + width_str + inner[m.end(2) :]
        return sheet_xml.replace(cols_m.group(0), f"<cols>{new_inner}</cols>", 1)

    new_col = f'<col min="{col_index}" max="{col_index}" width="{width_str}" customWidth="1"/>'
    new_inner = new_col + inner
    return sheet_xml.replace(cols_m.group(0), f"<cols>{new_inner}</cols>", 1)
