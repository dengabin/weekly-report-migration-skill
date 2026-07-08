"""从本地 .ksheet（ZIP/XML）读取子表为二维字符串数组。"""
from __future__ import annotations

import re
import sys
import zipfile
from pathlib import Path

from sheet_utils import col_letter_to_index

_PATCH = Path(__file__).resolve().parents[1] / "patch"
if str(_PATCH) not in sys.path:
    sys.path.insert(0, str(_PATCH))
from patch_ksheet_zip import read_cell_text_from_xml, resolve_sheet_path  # noqa: E402


def ksheet_sheet_to_rows(ksheet_path: Path, sheet_name: str) -> list[list[str]]:
    with zipfile.ZipFile(ksheet_path) as zin:
        sheet_path = resolve_sheet_path(zin, sheet_name)
        if not sheet_path:
            raise ValueError(f"未找到子表: {sheet_name}")
        sheet_xml = zin.read(sheet_path).decode("utf-8")
        sst_xml = zin.read("xl/sharedStrings.xml").decode("utf-8")

    dim_m = re.search(r'<dimension ref="([A-Z]+)(\d+):([A-Z]+)(\d+)"', sheet_xml)
    if not dim_m:
        return []

    max_row = int(dim_m.group(4))
    max_col_idx = col_letter_to_index(dim_m.group(3))
    rows: list[list[str]] = [[""] * (max_col_idx + 1) for _ in range(max_row)]

    for cm in re.finditer(r'<c r="([A-Z]+)(\d+)"', sheet_xml):
        col_letter, row_num = cm.group(1), int(cm.group(2))
        if row_num < 1 or row_num > max_row:
            continue
        ref = f"{col_letter}{row_num}"
        text = read_cell_text_from_xml(sheet_xml, sst_xml, ref) or ""
        col_idx = col_letter_to_index(col_letter)
        row = rows[row_num - 1]
        if col_idx >= len(row):
            row.extend([""] * (col_idx - len(row) + 1))
        row[col_idx] = text
    return rows
