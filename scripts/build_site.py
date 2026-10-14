"""Build the publishable site from the data files.

Reads  src/index.html + data/*.json
Writes site/index.html  (one self-contained page with the data built in)
       site/data/*.json (the same data, for anyone who wants it raw)

Netlify publishes the site/ folder exactly as committed; it runs no build of
its own. GitHub Actions runs this script (see .github/workflows/), so you never
need to, but you can run it locally too:

    python3 scripts/build_site.py
"""
from __future__ import annotations

import json
import shutil
import sys

from common import DATA, SITE, SRC, load

NAMES = ["schemes", "personas", "gaps", "projects", "status", "config"]
PLACEHOLDER = "<!--BUILD:DATA-->"


def main() -> int:
    import validate  # same folder
    if validate.main() != 0:
        print("Build stopped: fix the data problems above first.")
        return 1
    d = {n: load(f"{n}.json") for n in NAMES}
    payload = {
        "schemes": d["schemes"]["schemes"], "personas": d["personas"]["personas"], "gaps": d["gaps"]["gaps"],
        "projects": d["projects"]["rows"], "status": d["status"], "config": d["config"],
    }
    blob = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).replace("<", "\\u003c")
    tpl = (SRC / "index.html").read_text(encoding="utf-8")
    if PLACEHOLDER not in tpl:
        print(f"Build stopped: {PLACEHOLDER} is missing from src/index.html")
        return 1
    page = tpl.replace(PLACEHOLDER, f"<script>window.__DATA={blob};</script>", 1)

    SITE.mkdir(exist_ok=True)
    (SITE / "index.html").write_text(page, encoding="utf-8")
    out = SITE / "data"
    if out.exists():
        shutil.rmtree(out)
    out.mkdir()
    for n in NAMES:
        shutil.copyfile(DATA / f"{n}.json", out / f"{n}.json")
    print(f"Built site/index.html ({len(page) // 1024} KB) and site/data/.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
