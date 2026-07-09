#!/usr/bin/env python3
"""在 .ksheet 目标子表插入新周列（ZIP/XML），保留 customXml 超链接。"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
import zipfile
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))
from sheet_utils import week_matches  # noqa: E402

# 复用 patch_ksheet_zip 的 SST 与路径解析
sys.path.insert(0, str(Path(__file__).resolve().parent))
from patch_ksheet_zip import (  # noqa: E402
    HYPERSUBLINK_MARKER,
    append_shared_string,
    build_si,
    count_hypersublinks,
    get_cell_style_id,
    parse_si_blocks,
    read_cell_text_from_xml,
    resolve_sheet_path,
    text_from_si,
    verify_zip_bytes_preserved,
)


def col_letter_to_index(col: str) -> int:
    col = col.upper()
    n = 0
    for ch in col:
        n = n * 26 + (ord(ch) - ord("A") + 1)
    return n


def index_to_col(idx: int) -> str:
    s = ""
    n = idx
    while n:
        n, r = divmod(n - 1, 26)
        s = chr(ord("A") + r) + s
    return s


def split_cell_ref(ref: str) -> tuple[str, int]:
    m = re.match(r"^([A-Z]+)(\d+)$", ref)
    if not m:
        raise ValueError(f"非法单元格: {ref}")
    return m.group(1), int(m.group(2))


def shift_cell_ref(ref: str, col_delta: int) -> str:
    col, row = split_cell_ref(ref)
    return f"{index_to_col(col_letter_to_index(col) + col_delta)}{row}"


def workbook_sheet_stid(wb_xml: str, sheet_name: str) -> str | None:
    m = re.search(
        rf'<sheet[^>]+name="{re.escape(sheet_name)}"[^>]+sheetId="(\d+)"',
        wb_xml,
    )
    return m.group(1) if m else None


def format_week_header(week: str, aliases: list[str]) -> str:
    try:
        d = datetime.strptime(week[:10], "%Y-%m-%d").date()
        md = f"{d.month}月{d.day}日"
    except ValueError:
        return week
    period = None
    for a in aliases:
        if "周期" in a:
            period = a.replace("周期：", "").replace("周期:", "").strip()
            break
    if not period:
        for a in aliases:
            if re.search(r"\d", a) and "-" in a and "月" not in a:
                period = a
                break
    if period:
        return f"{md}\n周期：{period}"
    return md


def header_row_has_week(sheet_xml: str, sst_xml: str, week: str, aliases: list[str]) -> bool:
    for cm in re.finditer(r'<c r="[A-Z]+1"[^>]*>.*?</c>', sheet_xml, re.DOTALL):
        ref_m = re.search(r'r="([A-Z]+1)"', cm.group(0))
        if not ref_m:
            continue
        text = read_cell_text_from_xml(sheet_xml, sst_xml, ref_m.group(1))
        if text and week_matches(text, week, aliases):
            return True
    return False


def detect_link_col_in_xml(sheet_xml: str, sst_xml: str) -> int | None:
    """扫描前几行数据行，找到内容以 📄 开头的列（1-based）。"""
    for row in range(2, 8):
        for cm in re.finditer(rf'<c r="([A-Z]+){row}"[^>]*>.*?</c>', sheet_xml, re.DOTALL):
            ref = f"{cm.group(1)}{row}"
            text = read_cell_text_from_xml(sheet_xml, sst_xml, ref)
            if text and text.strip().startswith("📄"):
                return col_letter_to_index(cm.group(1))
    return None


def detect_name_col_in_xml(sheet_xml: str, sst_xml: str, cfg: dict) -> int:
    """从 config 或表头推断姓名列（1-based）。"""
    opts = cfg.get("options", {})
    if opts.get("sheet_name_column"):
        return col_letter_to_index(opts["sheet_name_column"])
    for cm in re.finditer(r'<c r="([A-Z]+)1"[^>]*>.*?</c>', sheet_xml, re.DOTALL):
        text = read_cell_text_from_xml(sheet_xml, sst_xml, f"{cm.group(1)}1")
        if text and ("姓名" in text or "名字" in text):
            return col_letter_to_index(cm.group(1))
    return 2  # B


def detect_insert_col_index(sheet_xml: str, sst_xml: str, cfg: dict, week: str) -> int:
    """根据表头日期顺序，找到新周列应插入的位置（1-based）。

    表头中日期列按降序排列（最新在左、最旧在右），新周插入到
    第一个比自己旧的日期列位置（把它及右侧全部右移）。
    若无日期列，回退到固定列之后。
    """
    name_col = detect_name_col_in_xml(sheet_xml, sst_xml, cfg)
    date_re = re.compile(r"(\d+)月(\d+)日")

    date_cols: list[tuple[int, int, int]] = []
    for cm in re.finditer(r'<c r="([A-Z]+)1"[^>]*>.*?</c>', sheet_xml, re.DOTALL):
        col_letter = cm.group(1)
        col_idx = col_letter_to_index(col_letter)
        if col_idx <= name_col:
            continue
        text = read_cell_text_from_xml(sheet_xml, sst_xml, f"{col_letter}1")
        if text:
            dm = date_re.search(text)
            if dm:
                date_cols.append((col_idx, int(dm.group(1)), int(dm.group(2))))

    if not date_cols:
        link_col = detect_link_col_in_xml(sheet_xml, sst_xml)
        if link_col is not None and link_col > name_col:
            return link_col + 1
        return name_col + 1

    date_cols.sort(key=lambda x: x[0])

    try:
        new_d = datetime.strptime(week[:10], "%Y-%m-%d").date()
        new_month, new_day = new_d.month, new_d.day
    except ValueError:
        return date_cols[0][0]

    for col_idx, month, day in date_cols:
        if (new_month, new_day) > (month, day):
            return col_idx

    return date_cols[-1][0] + 1


def shift_cell_refs_in_sheet(sheet_xml: str, min_col_index: int) -> str:
    cell_ref_re = re.compile(r'(<c r=")([A-Z]+)(\d+)(")')

    def repl(m: re.Match[str]) -> str:
        col = m.group(2)
        ci = col_letter_to_index(col)
        if ci >= min_col_index:
            col = index_to_col(ci + 1)
        return f"{m.group(1)}{col}{m.group(3)}{m.group(4)}"

    return cell_ref_re.sub(repl, sheet_xml)


def bump_dimension(sheet_xml: str) -> str:
    m = re.search(r'<dimension ref="([A-Z]+)(\d+):([A-Z]+)(\d+)"', sheet_xml)
    if not m:
        return sheet_xml
    c1, r1, c2, r2 = m.group(1), m.group(2), m.group(3), m.group(4)
    new_c2 = index_to_col(col_letter_to_index(c2) + 1)
    old = m.group(0)
    new = f'<dimension ref="{c1}{r1}:{new_c2}{r2}"'
    return sheet_xml.replace(old, new, 1)


def shift_cols_element(sheet_xml: str, insert_col: int, template_width: str) -> str:
    cols_m = re.search(r"<cols>(.*?)</cols>", sheet_xml, re.DOTALL)
    if not cols_m:
        return sheet_xml

    inner = cols_m.group(1)

    def shift_col_tag(m: re.Match[str]) -> str:
        tag = m.group(0)
        mi = re.search(r'min="(\d+)"', tag)
        ma = re.search(r'max="(\d+)"', tag)
        if not mi or not ma:
            return tag
        min_v, max_v = int(mi.group(1)), int(ma.group(1))
        if min_v >= insert_col:
            return (
                tag.replace(f'min="{min_v}"', f'min="{min_v + 1}"')
                .replace(f'max="{max_v}"', f'max="{max_v + 1}"')
            )
        return tag

    inner = re.sub(r"<col\b[^>]*/>", shift_col_tag, inner)
    new_col = f'<col min="{insert_col}" max="{insert_col}" width="{template_width}" customWidth="1"/>'
    inner = new_col + inner
    return sheet_xml.replace(cols_m.group(0), f"<cols>{inner}</cols>", 1)


def bump_row_spans(sheet_xml: str, insert_col: int) -> str:
    def repl(m: re.Match[str]) -> str:
        spans = m.group(1)
        parts = spans.split(":")
        if len(parts) != 2:
            return m.group(0)
        end = int(parts[1])
        if end >= insert_col:
            end += 1
        return f'spans="{parts[0]}:{end}"'

    return re.sub(r'spans="(\d+:\d+)"', repl, sheet_xml)


def list_row_numbers(sheet_xml: str) -> list[int]:
    return [int(m.group(1)) for m in re.finditer(r'<row r="(\d+)"', sheet_xml)]


def row_has_cell_in_col(row_xml: str, col_letter: str) -> bool:
    return bool(re.search(rf'<c r="{col_letter}\d+"', row_xml))


def insert_new_column_cells(
    sheet_xml: str,
    insert_col: int,
    header_idx: int,
    empty_idx: int,
    header_style: str,
    body_style: str,
    member_rows: set[int],
) -> str:
    col_letter = index_to_col(insert_col)

    def patch_row(m: re.Match[str]) -> str:
        row_xml = m.group(0)
        row_m = re.search(r'<row r="(\d+)"', row_xml)
        if not row_m:
            return row_xml
        row_num = int(row_m.group(1))
        if row_has_cell_in_col(row_xml, col_letter):
            return row_xml

        if row_num == 1:
            new_cell = f'<c r="{col_letter}1" s="{header_style}" t="s"><v>{header_idx}</v></c>'
        elif row_num in member_rows:
            new_cell = f'<c r="{col_letter}{row_num}" s="{body_style}" t="s"><v>{empty_idx}</v></c>'
        else:
            return row_xml

        # 插在第一个列号 >= insert_col 的 <c 之前，否则追加到 </row> 前
        insert_pos = None
        for cm in re.finditer(r'<c r="([A-Z]+)(\d+)"', row_xml):
            if col_letter_to_index(cm.group(1)) >= insert_col:
                insert_pos = cm.start()
                break
        if insert_pos is None:
            return row_xml.replace("</row>", new_cell + "</row>", 1)
        return row_xml[:insert_pos] + new_cell + row_xml[insert_pos:]

    return re.sub(r'<row r="\d+".*?</row>', patch_row, sheet_xml, flags=re.DOTALL)


def shift_custom_xml_refs(custom_xml: str, sheet_stid: str, min_col_index: int) -> str:
    pattern = re.compile(
        rf'(<woSheetProps sheetStid="{re.escape(sheet_stid)}"[^>]*>)(.*?)(</woSheetProps>)',
        re.DOTALL,
    )

    def shift_block(m: re.Match[str]) -> str:
        head, body, tail = m.group(1), m.group(2), m.group(3)

        def repl_ref(rm: re.Match[str]) -> str:
            ref = rm.group(1)
            if col_letter_to_index(split_cell_ref(ref)[0]) >= min_col_index:
                return f'ref="{shift_cell_ref(ref, 1)}"'
            return rm.group(0)

        body = re.sub(r'ref="([A-Z]+\d+)"', repl_ref, body)
        return head + body + tail

    return pattern.sub(shift_block, custom_xml)


def find_member_rows(sheet_xml: str, sst_xml: str, cfg: dict) -> set[int]:
    """扫描姓名列，返回所有包含人名（非表头、非链接）的行号。"""
    name_col_idx = detect_name_col_in_xml(sheet_xml, sst_xml, cfg)
    name_col_letter = index_to_col(name_col_idx)
    rows: set[int] = set()
    for cm in re.finditer(rf'<c r="{name_col_letter}(\d+)"[^>]*>.*?</c>', sheet_xml, re.DOTALL):
        row = int(cm.group(1))
        if row <= 1:
            continue
        text = read_cell_text_from_xml(sheet_xml, sst_xml, f"{name_col_letter}{row}")
        if text and text.strip() and not text.strip().startswith("📄"):
            rows.add(row)
    return rows


def col_width_from_sheet(sheet_xml: str, col_index: int) -> str:
    from column_width import col_width_at, DEFAULT_COL_WIDTH

    w = col_width_at(sheet_xml, col_index)
    if w is not None:
        return f"{w:.3f}"
    return f"{DEFAULT_COL_WIDTH:.3f}"


def list_week_content_col_indices(sheet_xml: str, sst_xml: str, cfg: dict) -> list[int]:
    """表头含「月日」的周内容列（1-based）。"""
    name_col = detect_name_col_in_xml(sheet_xml, sst_xml, cfg)
    date_re = re.compile(r"(\d+)月(\d+)日")
    indices: list[int] = []
    for cm in re.finditer(r'<c r="([A-Z]+)1"[^>]*>.*?</c>', sheet_xml, re.DOTALL):
        col_letter = cm.group(1)
        col_idx = col_letter_to_index(col_letter)
        if col_idx <= name_col:
            continue
        text = read_cell_text_from_xml(sheet_xml, sst_xml, f"{col_letter}1")
        if text and date_re.search(text):
            indices.append(col_idx)
    return indices


def choose_insert_column_width(
    sheet_xml: str,
    sst_xml: str,
    cfg: dict,
    content_texts: list[str] | None = None,
) -> str:
    """新周列宽度：优先按迁移内容，其次参考已有周列，不用窄的链接列。"""
    from column_width import (
        MIN_COL_WIDTH,
        MAX_COL_WIDTH,
        DEFAULT_COL_WIDTH,
        col_width_at,
        excel_col_width_from_texts,
    )

    candidates: list[float] = []
    for ci in list_week_content_col_indices(sheet_xml, sst_xml, cfg):
        w = col_width_at(sheet_xml, ci)
        if w is not None and w >= MIN_COL_WIDTH:
            candidates.append(min(w, MAX_COL_WIDTH))

    if content_texts:
        candidates.append(excel_col_width_from_texts(content_texts))

    if not candidates:
        return f"{DEFAULT_COL_WIDTH:.3f}"
    return f"{min(max(candidates), MAX_COL_WIDTH):.3f}"


def insert_week_column(
    input_path: Path,
    output_path: Path,
    sheet_name: str,
    week: str,
    aliases: list[str],
    cfg: dict | None = None,
    content_texts: list[str] | None = None,
) -> dict:
    cfg = cfg or {}
    same_file = input_path.resolve() == output_path.resolve()
    if not same_file:
        shutil.copy2(input_path, output_path)

    with zipfile.ZipFile(input_path) as zin:
        wb_xml = zin.read("xl/workbook.xml").decode("utf-8")
        sheet_path = resolve_sheet_path(zin, sheet_name)
        if not sheet_path:
            raise SystemExit(f"未找到子表: {sheet_name}")
        sheet_stid = workbook_sheet_stid(wb_xml, sheet_name)
        sst_xml = zin.read("xl/sharedStrings.xml").decode("utf-8")
        sheet_xml = zin.read(sheet_path).decode("utf-8")
        custom_xml = (
            zin.read("customXml/item2.xml").decode("utf-8")
            if "customXml/item2.xml" in zin.namelist()
            else ""
        )

    if header_row_has_week(sheet_xml, sst_xml, week, aliases):
        return {
            "status": "exists",
            "sheet": sheet_name,
            "week": week,
            "message": "周列已存在，跳过插入",
        }

    insert_col = detect_insert_col_index(sheet_xml, sst_xml, cfg, week)
    header_text = format_week_header(week, aliases)
    header_style = get_cell_style_id(sheet_xml, f"{index_to_col(insert_col)}1") or "3"
    # 插入后内容列样式参考原 insert_col 列（shift 前）
    body_template_col = index_to_col(insert_col)
    body_style = get_cell_style_id(sheet_xml, f"{body_template_col}2") or "6"
    template_width = choose_insert_column_width(sheet_xml, sst_xml, cfg, content_texts)

    member_rows = find_member_rows(sheet_xml, sst_xml, cfg)
    sst_xml, header_idx = append_shared_string(sst_xml, header_text)
    sst_xml, empty_idx = append_shared_string(sst_xml, "")

    sheet_xml = shift_cell_refs_in_sheet(sheet_xml, insert_col)
    sheet_xml = bump_dimension(sheet_xml)
    sheet_xml = bump_row_spans(sheet_xml, insert_col)
    sheet_xml = shift_cols_element(sheet_xml, insert_col, template_width)
    sheet_xml = insert_new_column_cells(
        sheet_xml,
        insert_col,
        header_idx,
        empty_idx,
        header_style,
        body_style,
        member_rows,
    )

    if custom_xml and sheet_stid:
        custom_xml = shift_custom_xml_refs(custom_xml, sheet_stid, insert_col)

    allowed = {"xl/sharedStrings.xml", sheet_path}
    if custom_xml:
        allowed.add("customXml/item2.xml")

    link_before = count_hypersublinks(input_path)

    tmp = output_path.with_suffix(".tmp.ksheet")
    shutil.copy2(input_path, tmp)
    with zipfile.ZipFile(tmp, "r") as zin, zipfile.ZipFile(output_path, "w") as zout:
        for item in zin.infolist():
            data = zin.read(item.filename)
            if item.filename == "xl/sharedStrings.xml":
                data = sst_xml.encode("utf-8")
            elif item.filename == sheet_path:
                data = sheet_xml.encode("utf-8")
            elif item.filename == "customXml/item2.xml" and custom_xml:
                data = custom_xml.encode("utf-8")
            zout.writestr(item, data)
    tmp.unlink(missing_ok=True)

    violations = verify_zip_bytes_preserved(input_path, output_path, allowed)
    link_after = count_hypersublinks(output_path)
    if violations:
        raise SystemExit(f"插入列时修改了非目标区域: {violations[:5]}")
    if link_before != link_after:
        raise SystemExit(f"hypersublink 数量变化: {link_before} -> {link_after}")

    return {
        "status": "inserted",
        "sheet": sheet_name,
        "week": week,
        "insert_col": index_to_col(insert_col),
        "header": header_text,
        "col_width": template_width,
        "member_rows": len(member_rows),
        "hypersublink_count": link_after,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="在 ksheet 子表插入周列")
    parser.add_argument("--config", type=Path, default=Path("config.json"))
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--sheet", default=None, help="子表名，默认从 preflight 或 config 解析")
    parser.add_argument("--week", default=None)
    parser.add_argument(
        "--extracted",
        type=Path,
        default=None,
        help="extracted.json；用于按迁移内容估算新列宽度",
    )
    args = parser.parse_args()

    cfg = json.loads(args.config.read_text(encoding="utf-8"))
    week = args.week or cfg.get("week")
    aliases = cfg.get("week_aliases") or []
    if not week:
        print("缺少 week", file=sys.stderr)
        return 1

    sheet = args.sheet
    if not sheet:
        pr = Path(".cache/preflight-report.json")
        if pr.exists():
            sheet = (
                (json.loads(pr.read_text(encoding="utf-8")).get("checks") or {})
                .get("dept_sheets", {})
                .get("resolved_sheet")
            )
    if not sheet:
        print("缺少 --sheet", file=sys.stderr)
        return 1

    out = args.output or args.input
    content_texts = None
    if args.extracted and args.extracted.exists():
        ext = json.loads(args.extracted.read_text(encoding="utf-8"))
        content_texts = [m.get("content", "") for m in ext.get("members", [])]

    result = insert_week_column(args.input, out, sheet, week, aliases, cfg, content_texts)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] in ("inserted", "exists") else 1


if __name__ == "__main__":
    raise SystemExit(main())
