#!/usr/bin/env python3
import re
import zipfile
from pathlib import Path

ks = Path(r"d:\branch\skills\report-migration\.cache\2026版式产研部-周报(副本).ksheet")
patched = Path(r"d:\branch\skills\report-migration\.cache\dept-report-patched.ksheet")

def cell_info(zpath, ref):
    with zipfile.ZipFile(zpath) as z:
        sheet = z.read("xl/worksheets/sheet9.xml").decode("utf-8")
        styles = z.read("xl/styles.xml").decode("utf-8")
        sst = z.read("xl/sharedStrings.xml").decode("utf-8")
    m = re.search(rf'<c r="{ref}"[^>]*>.*?</c>', sheet, re.DOTALL)
    if not m:
        return
    cell = m.group()
    sm = re.search(r'\ss="(\d+)"', cell)
    s_idx = sm.group(1) if sm else "?"
    print(f"\n{zpath.name} {ref}: {cell}")
    # find xfs for this style
    cell_xfs = re.findall(r"<xf[^/]*/>", styles)
    if s_idx != "?" and int(s_idx) < len(cell_xfs):
        print("  xfs:", cell_xfs[int(s_idx)][:200])
    vm = re.search(r"<v>(\d+)</v>", cell)
    if vm:
        items = re.findall(r"<si>.*?</si>", sst, re.DOTALL)
        si = items[int(vm.group(1))]
        print("  si has preserve:", "preserve" in si)
        print("  si &#10;:", si.count("&#10;"))
        print("  si <r> runs:", si.count("<r>"))

for p in [ks, patched]:
    for ref in ["C2", "E2", "E18"]:
        cell_info(p, ref)

# row heights in sheet9
with zipfile.ZipFile(patched) as z:
    sheet = z.read("xl/worksheets/sheet9.xml").decode("utf-8")
    for m in re.finditer(r'<row r="(\d+)"[^>]*>', sheet):
        if m.group(1) in ("1", "2", "18"):
            print("row tag:", m.group())
