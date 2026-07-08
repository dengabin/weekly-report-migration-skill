#!/usr/bin/env python3
import re
import zipfile
from pathlib import Path

ks = Path(r"d:\branch\skills\report-migration\.cache\dept-report.ksheet")
with zipfile.ZipFile(ks) as z:
    sheet = z.read("xl/worksheets/sheet9.xml").decode("utf-8")
    for ref in ["C2", "C17", "C18", "D2", "D18", "E18"]:
        m = re.search(rf'<c r="{ref}"[^/]*/>|<c r="{ref}"[^>]*>.*?</c>', sheet)
        print(ref, m.group() if m else "NOT FOUND")
