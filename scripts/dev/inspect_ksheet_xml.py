#!/usr/bin/env python3
import re
import zipfile
from pathlib import Path

ks = [p for p in Path(r"d:\branch\skills\report-migration\.cache").glob("*.ksheet") if "patch" not in p.name][0]
with zipfile.ZipFile(ks) as z:
    ss = z.read("xl/sharedStrings.xml").decode("utf-8")
    items = re.findall(r"<si>.*?</si>", ss, re.DOTALL)
    print("998 len", len(items[998]))
    print(items[998][:400])
    item2 = z.read("customXml/item2.xml").decode("utf-8")
    # find block for sheet9 E2 or string 998
    for pat in ["E2", "sheet9", "rId"]:
        pass
    # count link types
    print("filelink", item2.count("filelink"))
    print("http", item2.count("http://") + item2.count("https://"))
    # sample http link
    m = re.search(r'hypersublink[^>]+address="(https://[^"]+)"', item2)
    if m:
        print("sample url link", m.group()[:200])
