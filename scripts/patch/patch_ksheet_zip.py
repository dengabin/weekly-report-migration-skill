#!/usr/bin/env python3
"""对 .ksheet 做 ZIP/XML 级单元格补丁，保留 customXml 超链接。"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
import zipfile
from collections import defaultdict
from pathlib import Path
from xml.sax.saxutils import escape

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))

SST_NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
SI_RE = re.compile(r"<si>.*?</si>", re.DOTALL)
HYPERSUBLINK_MARKER = "hypersublink"


def _cell_attr_re(cell_ref: str) -> str:
    return rf'<c\b(?=[^>]*\br="{re.escape(cell_ref)}")'


def _cell_open_re(cell_ref: str) -> str:
    return _cell_attr_re(cell_ref) + r"([^>]*)>"


def _cell_self_close_re(cell_ref: str) -> str:
    return _cell_attr_re(cell_ref) + r"([^>]*)/>"


def _cell_full_re(cell_ref: str) -> str:
    return rf"({_cell_attr_re(cell_ref)}[^>]*>)(.*?)(</c>)"


def load_json(path: Path) -> dict:
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def resolve_sheet_path(z: zipfile.ZipFile, sheet_name: str) -> str | None:
    wb = z.read("xl/workbook.xml").decode("utf-8")
    rels = z.read("xl/_rels/workbook.xml.rels").decode("utf-8")
    rid = None
    for m in re.finditer(r'<sheet[^>]+name="([^"]+)"[^>]+r:id="([^"]+)"', wb):
        if m.group(1) == sheet_name:
            rid = m.group(2)
            break
    if not rid:
        return None
    m = re.search(rf'Id="{re.escape(rid)}"[^>]+Target="([^"]+)"', rels)
    if not m:
        return None
    target = m.group(1).lstrip("/")
    if not target.startswith("xl/"):
        target = "xl/" + target
    return target


def parse_si_blocks(sst_xml: str) -> list[str]:
    return SI_RE.findall(sst_xml)


def text_from_si(si_xml: str) -> str:
    parts: list[str] = []
    for m in re.finditer(r"<t(?:\s[^>]*)?>(.*?)</t>", si_xml, re.DOTALL):
        t = m.group(1)
        t = t.replace("&#10;", "\n").replace("&#13;", "\r").replace("&amp;", "&")
        t = t.replace("&lt;", "<").replace("&gt;", ">").replace("&quot;", '"')
        parts.append(t)
    return "".join(parts)


def build_si(text: str) -> str:
    escaped = escape(text, entities={"'": "&apos;", '"': "&quot;"})
    escaped = escaped.replace("\r\n", "\n").replace("\r", "\n")
    escaped = escaped.replace("\n", "&#10;")
    # 与同行历史周列一致：不用 xml:space="preserve"
    return f"<si><t>{escaped}</t></si>"


def append_shared_string(sst_xml: str, text: str) -> tuple[str, int]:
    blocks = parse_si_blocks(sst_xml)
    new_index = len(blocks)
    new_si = build_si(text)
    sst_xml = re.sub(r"</sst>", new_si + "</sst>", sst_xml, count=1)

    def bump_header(m: re.Match[str]) -> str:
        tag = m.group(0)
        for attr in ("uniqueCount", "count"):
            am = re.search(rf'{attr}="(\d+)"', tag)
            if am:
                old = int(am.group(1))
                tag = tag.replace(f'{attr}="{old}"', f'{attr}="{old + 1}"')
        return tag

    sst_xml = re.sub(r"<sst\b[^>]*>", bump_header, sst_xml, count=1)
    return sst_xml, new_index


def read_cell_text_from_xml(sheet_xml: str, sst_xml: str, cell_ref: str) -> str | None:
    if re.search(_cell_self_close_re(cell_ref), sheet_xml):
        return ""
    m = re.search(_cell_full_re(cell_ref), sheet_xml, re.DOTALL)
    if not m:
        return None
    body = m.group(2)
    vm = re.search(r"<v>(\d+)</v>", body)
    if not vm:
        return None
    blocks = parse_si_blocks(sst_xml)
    idx = int(vm.group(1))
    if idx >= len(blocks):
        return None
    return text_from_si(blocks[idx])


def get_cell_style_id(sheet_xml: str, cell_ref: str) -> str | None:
    m = re.search(_cell_open_re(cell_ref), sheet_xml)
    if not m:
        m = re.search(_cell_self_close_re(cell_ref), sheet_xml)
    if not m:
        return None
    sm = re.search(r'\ss="(\d+)"', m.group(1))
    return sm.group(1) if sm else None


def resolve_template_ref(sheet_xml: str, sst_xml: str, row: int, content_col: int) -> str:
    """参考同行历史周列复制单元格样式；跳过链接列和空列。"""
    for offset in range(1, 5):
        ref = f"{_col_letter(content_col + offset)}{row}"
        text = read_cell_text_from_xml(sheet_xml, sst_xml, ref)
        if not text or (text.strip().startswith("📄")):
            continue
        if get_cell_style_id(sheet_xml, ref):
            return ref
    return f"{_col_letter(content_col + 1)}{row}"


def copy_cell_style(sheet_xml: str, target_ref: str, template_ref: str) -> str:
    style_id = get_cell_style_id(sheet_xml, template_ref)
    if not style_id:
        return sheet_xml

    pattern = re.compile(
        rf"({_cell_attr_re(target_ref)})([^>]*)(>)",
        re.DOTALL,
    )

    def repl(m: re.Match[str]) -> str:
        prefix, attrs, close = m.group(1), m.group(2), m.group(3)
        if re.search(r'\ss="', attrs):
            attrs = re.sub(r'\ss="\d+"', f' s="{style_id}"', attrs)
        else:
            attrs = f' s="{style_id}"' + attrs
        return prefix + attrs + close

    new_xml, n = pattern.subn(repl, sheet_xml, count=1)
    return new_xml if n else sheet_xml


def _ensure_t_s_attr(open_tag: str) -> str:
    if 't="inlineStr"' in open_tag:
        open_tag = re.sub(r'\s*t="inlineStr"', ' t="s"', open_tag)
    if 't="s"' not in open_tag:
        open_tag = open_tag.replace("<c ", '<c t="s" ')
    return open_tag


def patch_sheet_cell(sheet_xml: str, cell_ref: str, string_index: int) -> str:
    sc_pattern = re.compile(_cell_self_close_re(cell_ref))

    def sc_repl(m: re.Match[str]) -> str:
        attrs = m.group(1)
        open_tag = _ensure_t_s_attr(f'<c r="{cell_ref}"{attrs}>')
        return f"{open_tag}<v>{string_index}</v></c>"

    new_xml, n = sc_pattern.subn(sc_repl, sheet_xml, count=1)
    if n:
        return new_xml

    pattern = re.compile(_cell_full_re(cell_ref), re.DOTALL)

    def repl(m: re.Match[str]) -> str:
        open_tag, body, close_tag = m.group(1), m.group(2), m.group(3)
        open_tag = _ensure_t_s_attr(open_tag)
        body = re.sub(r"<v>\d+</v>", f"<v>{string_index}</v>", body)
        if "<v>" not in body:
            body = f"<v>{string_index}</v>"
        body = re.sub(r"<is>.*?</is>", "", body, flags=re.DOTALL)
        return open_tag + body + close_tag

    new_xml, n = pattern.subn(repl, sheet_xml, count=1)
    if n == 0:
        raise ValueError(f"未找到单元格 {cell_ref}")
    return new_xml


def count_hypersublinks(ksheet_path: Path) -> int:
    with zipfile.ZipFile(ksheet_path) as z:
        if "customXml/item2.xml" not in z.namelist():
            return 0
        data = z.read("customXml/item2.xml").decode("utf-8", errors="replace")
        return data.count(HYPERSUBLINK_MARKER)


def verify_zip_bytes_preserved(
    source: Path,
    output: Path,
    allowed_changed: set[str],
) -> list[str]:
    errors: list[str] = []
    with zipfile.ZipFile(source) as zin, zipfile.ZipFile(output) as zout:
        src_names = set(zin.namelist())
        out_names = set(zout.namelist())
        if src_names != out_names:
            only_src = src_names - out_names
            only_out = out_names - src_names
            if only_src:
                errors.append(f"输出缺少条目: {sorted(only_src)[:5]}")
            if only_out:
                errors.append(f"输出多出条目: {sorted(only_out)[:5]}")
        for name in src_names & out_names:
            if name in allowed_changed:
                continue
            if zin.read(name) != zout.read(name):
                errors.append(f"非目标文件被修改: {name}")
    return errors


def read_cell_text(ksheet_path: Path, sheet_path: str, cell_ref: str) -> str | None:
    with zipfile.ZipFile(ksheet_path) as z:
        sheet = z.read(sheet_path).decode("utf-8")
        sst = z.read("xl/sharedStrings.xml").decode("utf-8")
    return read_cell_text_from_xml(sheet, sst, cell_ref)


def apply_patches_zip(
    input_path: Path,
    output_path: Path,
    plan: dict,
    extracted: dict,
    *,
    strict_verbatim: bool = True,
) -> tuple[list[dict], list[dict]]:
    by_name = {m["name"]: m.get("content", "") for m in extracted.get("members", [])}
    applied: list[dict] = []
    skipped: list[dict] = []
    col_contents: dict[str, dict[int, list[str]]] = defaultdict(lambda: defaultdict(list))

    shutil.copy2(input_path, output_path)

    with zipfile.ZipFile(input_path) as zin:
        sheet_paths: dict[str, str] = {}
        for patch in plan.get("patches", []):
            sn = patch.get("sheet") or patch.get("target", {}).get("sheet")
            if sn and sn not in sheet_paths:
                sp = resolve_sheet_path(zin, sn)
                if not sp:
                    skipped.append({"name": patch.get("name"), "reason": f"sheet 不存在: {sn}"})
                else:
                    sheet_paths[sn] = sp

        sst_xml = zin.read("xl/sharedStrings.xml").decode("utf-8")
        sheet_xmls: dict[str, str] = {}
        for sn, sp in sheet_paths.items():
            sheet_xmls[sp] = zin.read(sp).decode("utf-8")

    changed_entries = {"xl/sharedStrings.xml"}
    changed_entries.update(sheet_xmls.keys())

    for patch in plan.get("patches", []):
        if patch.get("status") != "ready":
            skipped.append({"name": patch.get("name"), "reason": patch.get("status")})
            continue

        name = patch["name"]
        source = by_name.get(name)
        if source is None:
            skipped.append({"name": name, "reason": "extracted.json 中无该成员"})
            continue
        if strict_verbatim and patch.get("content") != source:
            skipped.append({"name": name, "reason": "patch-plan 与 extracted 内容不一致，拒绝写入"})
            continue

        sheet_name = patch.get("sheet") or patch.get("target", {}).get("sheet")
        sheet_path = sheet_paths.get(sheet_name or "")
        if not sheet_path:
            skipped.append({"name": name, "reason": f"未解析 sheet: {sheet_name}"})
            continue

        cell_ref = patch.get("cell") or f"{_col_letter(patch['col'])}{patch['row']}"
        row = int(patch["row"])
        col = int(patch["col"])
        old_text = read_cell_text(input_path, sheet_path, cell_ref)
        sst_xml, new_idx = append_shared_string(sst_xml, source)
        sheet_xml = sheet_xmls[sheet_path]
        template_ref = resolve_template_ref(sheet_xml, sst_xml, row, col)
        sheet_xml = patch_sheet_cell(sheet_xml, cell_ref, new_idx)
        sheet_xml = copy_cell_style(sheet_xml, cell_ref, template_ref)
        sheet_xmls[sheet_path] = sheet_xml
        col_contents[sheet_path][col].append(source)
        applied.append(
            {
                "name": name,
                "cell": cell_ref,
                "sheet": sheet_name,
                "row": row,
                "col": col,
                "style_from": template_ref,
                "old_len": len(old_text or ""),
                "new_len": len(source),
            }
        )

    if skipped:
        return applied, skipped

    if col_contents:
        from column_width import excel_col_width_from_texts, upsert_col_width_in_sheet_xml

        for sheet_path, xml in list(sheet_xmls.items()):
            per_sheet = col_contents.get(sheet_path)
            if not per_sheet:
                continue
            for col_idx, texts in per_sheet.items():
                needed = excel_col_width_from_texts(texts)
                xml = upsert_col_width_in_sheet_xml(xml, col_idx, needed)
            sheet_xmls[sheet_path] = xml

    # 写回 zip：仅替换 sharedStrings 与目标 sheet
    tmp = output_path.with_suffix(".ksheet.tmp")
    if tmp.exists():
        tmp.unlink()
    shutil.copy2(input_path, tmp)

    with zipfile.ZipFile(tmp, "r") as zin, zipfile.ZipFile(output_path, "w") as zout:
        for item in zin.infolist():
            data = zin.read(item.filename)
            if item.filename == "xl/sharedStrings.xml":
                data = sst_xml.encode("utf-8")
            elif item.filename in sheet_xmls:
                data = sheet_xmls[item.filename].encode("utf-8")
            zout.writestr(item, data)

    tmp.unlink(missing_ok=True)
    return applied, skipped


def _col_letter(col: int) -> str:
    s = ""
    n = int(col)
    while n:
        n, r = divmod(n - 1, 26)
        s = chr(ord("A") + r) + s
    return s


def main() -> int:
    parser = argparse.ArgumentParser(description="ZIP/XML 级补丁写入 .ksheet（保留超链接）")
    parser.add_argument("--config", type=Path, default=Path("config.json"))
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--extracted", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--no-strict-verbatim", action="store_true")
    args = parser.parse_args()

    if args.input.suffix.lower() != ".ksheet":
        print("本脚本仅用于 .ksheet；xlsx 请用 patch_sheet.py", file=sys.stderr)
        return 1

    cfg = load_json(args.config)
    plan = load_json(args.plan)
    extracted = load_json(args.extracted)

    link_before = count_hypersublinks(args.input)
    applied, skipped = apply_patches_zip(
        args.input,
        args.output,
        plan,
        extracted,
        strict_verbatim=not args.no_strict_verbatim,
    )
    if skipped:
        print(json.dumps({"applied": applied, "skipped": skipped}, ensure_ascii=False, indent=2), file=sys.stderr)
        return 1

    allowed = {"xl/sharedStrings.xml"}
    with zipfile.ZipFile(args.input) as zin:
        for patch in applied:
            sn = patch["sheet"]
            sp = resolve_sheet_path(zin, sn)
            if sp:
                allowed.add(sp)

    violations = verify_zip_bytes_preserved(args.input, args.output, allowed)
    link_after = count_hypersublinks(args.output)

    if violations:
        print(json.dumps({"error": "非目标区域被修改", "violations": violations[:20]}, ensure_ascii=False, indent=2), file=sys.stderr)
        return 2

    if link_before != link_after:
        print(
            json.dumps(
                {
                    "error": "customXml 超链接数量变化",
                    "before": link_before,
                    "after": link_after,
                },
                ensure_ascii=False,
                indent=2,
            ),
            file=sys.stderr,
        )
        return 3

    summary = {
        "week": cfg.get("week"),
        "method": "zip_xml_patch",
        "input": str(args.input),
        "output": str(args.output),
        "patch_count": len(applied),
        "hypersublink_count": link_after,
        "applied": applied,
        "skipped": skipped,
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
