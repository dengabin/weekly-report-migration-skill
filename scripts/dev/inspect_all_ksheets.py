#!/usr/bin/env python3
import zipfile
from pathlib import Path

cache = Path(r"d:\branch\skills\report-migration\.cache")
for p in sorted(cache.glob("*.ksheet")):
    with zipfile.ZipFile(p) as z:
        if "customXml/item2.xml" in z.namelist():
            d = z.read("customXml/item2.xml")
            print(p.name, p.stat().st_size, "item2", len(d), "hypersublink", d.count(b"hypersublink"))
        else:
            print(p.name, p.stat().st_size, "NO item2")
