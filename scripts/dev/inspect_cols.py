#!/usr/bin/env python3
import re
import zipfile
from pathlib import Path

z = zipfile.ZipFile(Path(r"d:\branch\skills\report-migration\.cache\2026版式产研部-周报(副本).ksheet"))
sheet = z.read("xl/worksheets/sheet9.xml").decode("utf-8")
sst = z.read("xl/sharedStrings.xml").decode("utf-8")
items = re.findall(r"<si>.*?</si>", sst, re.DOTALL)
for ref in ["C2", "D2", "E2", "F2", "G2"]:
    m = re.search(rf'<c r="{ref}"[^>]*>.*?</c>', sheet, re.DOTALL)
    if m:
        c = m.group()
        s = re.search(r's="(\d+)"', c)
        v = re.search(r"<v>(\d+)</v>", c)
        si = items[int(v.group(1))] if v else ""
        print(ref, "s=" + s.group(1), "nl=" + str(si.count("&#10;")))
        print("  ", si[:150])
