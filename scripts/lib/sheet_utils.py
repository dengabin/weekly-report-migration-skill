"""部门周报表格：子表解析与单元格定位。"""
from __future__ import annotations

import re
from typing import Any


def normalize(s: str) -> str:
    return (s or "").strip().replace("／", "/").replace("－", "-")


def week_matches(header: str, week: str, aliases: list[str]) -> bool:
    h = normalize(header)
    candidates = [normalize(week)] + [normalize(a) for a in aliases]
    return any(c and (c == h or c in h or h in c) for c in candidates)


def col_letter_to_index(col: str | int) -> int:
    if isinstance(col, int):
        return col
    col = col.upper()
    n = 0
    for ch in col:
        n = n * 26 + (ord(ch) - ord("A") + 1)
    return n - 1


def index_to_col(idx: int) -> str:
    s = ""
    n = idx + 1
    while n:
        n, r = divmod(n - 1, 26)
        s = chr(ord("A") + r) + s
    return s


def sheet_name_matches(name: str, pattern: str, mode: str = "contains") -> bool:
    name_n = normalize(name)
    pat_n = normalize(pattern)
    if mode == "equals":
        return name_n == pat_n
    if mode == "regex":
        return bool(re.search(pattern, name))
    return pat_n in name_n or name_n in pat_n


def resolve_dept_sheet(sheet_names: list[str], cfg: dict) -> tuple[str | None, str]:
    """根据 config.dept_sheet 在 workbook 子表列表中定位目标 sheet。

    仅当**唯一**命中时自动返回；多个候选时返回 None，由 Agent AskQuestion 让用户指定，禁止猜第一个。
    """
    dept_sheet = cfg.get("dept_sheet") or {}
    if dept_sheet.get("sheet_name"):
        exact = dept_sheet["sheet_name"]
        if exact in sheet_names:
            return exact, "config.dept_sheet.sheet_name"
        return None, f"配置的 sheet_name 不存在: {exact}"

    candidates: list[str] = []
    for key in ("fourth_dept_name", "value", "team_name"):
        v = dept_sheet.get(key) or (cfg.get(key) if key == "team_name" else None)
        if v:
            candidates.append(v)
    candidates.extend(dept_sheet.get("aliases", []))
    if cfg.get("team_name") and cfg["team_name"] not in candidates:
        candidates.append(cfg["team_name"])

    mode = dept_sheet.get("match", "contains")
    matched: set[str] = set()
    for pat in candidates:
        for sn in sheet_names:
            if sheet_name_matches(sn, pat, mode):
                matched.add(sn)

    if dept_sheet.get("fallback_scan", True):
        team = cfg.get("team_name", "")
        if team:
            for sn in sheet_names:
                if team in sn:
                    matched.add(sn)

    if len(matched) == 1:
        sn = next(iter(matched))
        return sn, f"子表唯一匹配: {sn!r}"
    if len(matched) > 1:
        return None, f"多个子表匹配，须用户指定 sheet_name: {sorted(matched)}"

    return None, f"未匹配到子表，候选: {candidates}，现有: {sheet_names}"


def find_cell_in_rows(
    rows: list[list[Any]],
    member: dict,
    target: dict,
    cfg: dict,
) -> tuple[int, int] | None:
    options = cfg.get("options", {})
    header_row = int(target.get("col_match", {}).get("row", options.get("sheet_header_row", 1))) - 1
    if header_row < 0 or header_row >= len(rows):
        return None

    col_match = target.get("col_match", {})
    col_idx = col_match.get("col_index")
    if col_idx is None:
        col_idx = options.get("dept_content_col_index")

    if col_idx is not None:
        col_idx = int(col_idx)
    else:
        week = cfg.get("week", "")
        aliases = cfg.get("week_aliases", [])
        header_contains = col_match.get("header_contains") or options.get("dept_week_header_contains")
        header_cells = rows[header_row]
        col_idx = None
        for j, cell in enumerate(header_cells):
            text = str(cell or "")
            if header_contains and header_contains in text:
                col_idx = j
                break
            if week_matches(text, week, aliases):
                col_idx = j
                break
        if col_idx is None:
            return None

    row_match = target.get("row_match", {})
    col_letter = row_match.get("column", options.get("sheet_name_column", "B"))
    name_col = col_letter_to_index(col_letter)

    name = member["name"]
    contains = row_match.get("contains", name)
    equals = row_match.get("equals")

    team_marker = target.get("team_row_marker")
    if team_marker is None:
        if "team_row_marker" in options:
            team_marker = options.get("team_row_marker") or None
        elif options.get("use_team_name_as_marker"):
            team_marker = cfg.get("team_name")
        else:
            team_marker = None
    if team_marker == "":
        team_marker = None
    in_team_section = team_marker is None

    for i, row in enumerate(rows):
        if i <= header_row:
            continue
        if len(row) <= name_col:
            continue
        cell_name = str(row[name_col] or "").strip()
        if not cell_name or cell_name in ("部门周报",):
            continue
        if team_marker and team_marker in cell_name and name not in cell_name:
            in_team_section = True
            continue
        if team_marker and in_team_section and team_marker in cell_name and name not in cell_name:
            in_team_section = False
        if not in_team_section and team_marker:
            continue
        if equals and cell_name == equals:
            return i, col_idx
        if contains and contains in cell_name:
            return i, col_idx
        if not equals and not contains and name in cell_name:
            return i, col_idx
    return None


def is_member_name_cell(cell: str, member_names: list[str]) -> bool:
    cell = (cell or "").strip()
    if not cell:
        return False
    if cell in member_names:
        return True
    return any(m in cell for m in member_names)


def nearest_group_above(
    rows: list[list[Any]],
    row_idx: int,
    member_names: list[str],
    header_row: int,
    name_col: int,
) -> str | None:
    """从成员行向上找最近的组标题行（姓名列不含任何 otl 成员名的行）。"""
    for i in range(row_idx - 1, header_row, -1):
        if i < 0 or len(rows[i]) <= name_col:
            continue
        cell = str(rows[i][name_col] or "").strip()
        if not cell or cell in ("部门周报",):
            continue
        if not is_member_name_cell(cell, member_names):
            return cell
        if "-" in cell:
            prefix = cell.split("-", 1)[0].strip()
            if prefix and not is_member_name_cell(prefix, member_names):
                return prefix
    return None


def resolve_team_from_members(
    rows: list[list[Any]],
    member_names: list[str],
    cfg: dict,
) -> dict:
    """
    根据 otl 成员姓名在部门子表中反推组名。
    全部成员落在同一组 → resolved；跨组/重名/找不到 → 需用户指定组名。
    """
    options = cfg.get("options", {})
    header_row = int(options.get("sheet_header_row", 1)) - 1
    name_col = col_letter_to_index(options.get("sheet_name_column", "B"))

    member_groups: dict[str, str] = {}
    ambiguous: list[str] = []
    not_found: list[str] = []

    for member in member_names:
        found_rows: list[int] = []
        for i in range(header_row + 1, len(rows)):
            if len(rows[i]) <= name_col:
                continue
            cell = str(rows[i][name_col] or "").strip()
            if not cell or cell in ("部门周报",):
                continue
            if member in cell or cell == member:
                found_rows.append(i)

        if not found_rows:
            not_found.append(member)
            continue

        groups: set[str] = set()
        for ri in found_rows:
            g = nearest_group_above(rows, ri, member_names, header_row, name_col)
            if g:
                groups.add(g)

        if len(groups) == 1:
            member_groups[member] = next(iter(groups))
        elif len(groups) > 1:
            ambiguous.append(member)
        else:
            ambiguous.append(member)

    unique_groups = set(member_groups.values())
    if len(unique_groups) == 1 and not ambiguous:
        team = next(iter(unique_groups))
        return {
            "status": "resolved",
            "team_name": team,
            "member_groups": member_groups,
            "not_found": not_found,
            "reason": f"全部可匹配成员均落在组 {team!r}",
        }
    if len(unique_groups) > 1 or ambiguous:
        return {
            "status": "ambiguous",
            "member_groups": member_groups,
            "ambiguous_members": ambiguous,
            "not_found": not_found,
            "candidates": sorted(unique_groups),
            "reason": "成员对应多个组或存在重名行，无法自动确定组名",
        }
    if not_found and not member_groups:
        return {
            "status": "not_found",
            "not_found": not_found,
            "reason": "部门表中未找到任何 otl 成员姓名",
        }
    return {
        "status": "need_team_name",
        "member_groups": member_groups,
        "not_found": not_found,
        "reason": "无法从姓名唯一确定组名，需用户提供组名",
    }


def apply_team_name_to_config(cfg: dict, team_name: str) -> None:
    cfg["team_name"] = team_name
    opts = cfg.setdefault("options", {})
    opts["team_row_marker"] = team_name
    opts["use_team_name_as_marker"] = True


def kdc_sheet_to_rows(sheet: dict) -> list[list[str]]:
    """将 KDC JSON 中单个子表的 data 转为二维字符串数组。"""
    rows: list[list[str]] = []
    for row_data in sheet.get("data", []):
        max_idx = max((c.get("index", 0) for c in row_data.get("cells", [])), default=0)
        row = [""] * (max_idx + 1)
        for cell in row_data.get("cells", []):
            idx = int(cell.get("index", 0))
            if idx >= len(row):
                row.extend([""] * (idx - len(row) + 1))
            row[idx] = str(cell.get("display_text") or "")
        rows.append(row)
    return rows


def find_sheet_in_kdc(raw: dict, sheet_name: str) -> dict | None:
    doc = raw.get("doc") or raw
    for sheet in doc.get("sheets", []):
        if sheet.get("name") == sheet_name:
            return sheet
    return None


def parse_sheet_table_from_markdown(md: str, sheet_name: str) -> list[list[str]] | None:
    """从 ksheet 导出的 Markdown 中截取 `### {sheet_name}` 下的第一个表格。"""
    pattern = rf"^###\s+{re.escape(sheet_name)}\s*$"
    lines = md.splitlines()
    start = None
    for i, line in enumerate(lines):
        if re.match(pattern, line.strip()):
            start = i + 1
            break
    if start is None:
        for i, line in enumerate(lines):
            if line.startswith("### ") and sheet_name in line:
                start = i + 1
                break
    if start is None:
        return None

    table: list[list[str]] = []
    for line in lines[start:]:
        if line.startswith("### "):
            break
        if line.strip().startswith("|"):
            cells = [c.strip() for c in line.strip("|").split("|")]
            if all(set(c) <= set("-: ") for c in cells):
                continue
            table.append(cells)
        elif table:
            break
    return table or None


def list_sheet_names_from_markdown(md: str) -> list[str]:
    return [ln.strip()[4:].strip() for ln in md.splitlines() if ln.startswith("### ")]


def worksheet_to_rows(ws, max_row: int | None = None, max_col: int | None = None) -> list[list[Any]]:
    mr = max_row or ws.max_row or 1
    mc = max_col or ws.max_column or 1
    rows = []
    for r in range(1, mr + 1):
        rows.append([ws.cell(row=r, column=c).value for c in range(1, mc + 1)])
    return rows
