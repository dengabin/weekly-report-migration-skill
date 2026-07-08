#!/usr/bin/env python3
"""Inspect ksheet customXml hypersublink structure."""
import re
import zipfile
from pathlib import Path

ks = [p for p in Path(r"d:\branch\skills\report-migration\.cache").glob("*.ksheet") if "patch" not in p.name][0]
with zipfile.ZipFile(ks) as z:
    item2 = z.read("customXml/item2.xml").decode("utf-8")
    print("hypersublink count", item2.count("hypersublink"))
    print("filelink count", item2.count("filelink"))
    print("bytes", len(item2))

    # workbook sheets
    wb = z.read("xl/workbook.xml").decode("utf-8")
    for m in re.finditer(r'<sheet[^>]+name="([^"]+)"[^>]+r:id="([^"]+)"', wb):
        print("sheet", m.group(1), m.group(2))

    rels = z.read("xl/_rels/workbook.xml.rels").decode("utf-8")
    for m in re.finditer(r'Id="([^"]+)"[^>]+Target="([^"]+)"', rels):
        if "sheet" in m.group(2):
            print(" rel", m.group(1), m.group(2))

    # D2 in item2
    for pat in ["D2", "C2", "sheet9", "r=\"D2\""]:
        print(pat, item2.count(pat))

    # sample filelink block
    m = re.search(r"<filelink.{0,800}", item2, re.DOTALL)
    if m:
        print("filelink block:\n", m.group()[:800])

    # find cell anchor pattern
    for m in re.finditer(r"<anchor[^>]{0,300}", item2):
        print("anchor sample:", m.group()[:200])
        break
