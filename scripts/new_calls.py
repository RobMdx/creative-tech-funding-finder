"""Find new UKRI opportunities that may belong in the Finder.

Reads UKRI's public opportunities feed (https://www.ukri.org/opportunity/feed/),
keeps items from AHRC and Innovate UK, plus items from other councils that
mention creative-tech keywords, and drops anything already tracked.
For each candidate it reads the opportunity page's dates and amounts.

Output: proposals/new-calls.json (for the optional AI step or a person),
plus a section appended to reports/latest.md.

This script never adds calls to the site by itself. Deciding relevance and
who can take part needs a person (or the optional AI draft step, which a
person still reviews).

Run: python3 scripts/new_calls.py
"""
from __future__ import annotations

import json
import re
import sys
import time
import xml.etree.ElementTree as ET

from common import REPORTS, ROOT, fetch, load, page_text, parse_ukri

FEED = "https://www.ukri.org/opportunity/feed/"
CORE_COUNCILS = {"AHRC", "Innovate UK"}
KEYWORDS = re.compile(
    r"\b(creative|createch|arts?|humanities|design|cultur\w*|heritage|museum|screen|film|"
    r"games?|music|immersive|xr|virtual production|media|craft|textiles?|fashion|"
    r"artificial intelligence|\bai\b|machine learning|robot\w*|fabricat\w*|digital manufactur\w*|"
    r"technician\w*|technical (?:staff|professional\w*))\b",
    re.I,
)


def main() -> int:
    code, body = fetch(FEED)
    if code != 200 or not body:
        msg = f"\n## New calls\n\n_The UKRI feed could not be read (status {code})._\n"
        _append(msg)
        print(msg)
        return 0
    tracked = {s["u"].rstrip("/") for s in load("schemes.json")["schemes"]}
    root = ET.fromstring(body)
    found = []
    for item in root.iter("item"):
        title = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()
        cat = (item.findtext("category") or "").strip()
        desc = re.sub(r"<[^>]+>", " ", item.findtext("description") or "")
        if not link or link.rstrip("/") in tracked:
            continue
        if cat not in CORE_COUNCILS and not KEYWORDS.search(f"{title} {desc}"):
            continue
        entry = {"title": title, "url": link, "council": cat, "published": item.findtext("pubDate"),
                 "summary": re.sub(r"\s+", " ", desc).strip()[:600]}
        c2, page = fetch(link)
        time.sleep(1)
        if c2 == 200 and page:
            info = parse_ukri(page_text(page))
            entry.update({"status": info["status"], "opening": info["opening"],
                          "closing": "always" if info["always_open"] else info["closing"],
                          "amounts": info["award_range"] or info["maximum"] or info["total_fund"]})
        found.append(entry)

    out = ROOT / "proposals"
    out.mkdir(exist_ok=True)
    (out / "new-calls.json").write_text(json.dumps(found, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    lines = [f"- [{f['title']}]({f['url']}) · {f['council']} · closes {f.get('closing') or '?'}"
             + (f" · {', '.join('£{:,}'.format(a) for a in f['amounts'])}" if f.get("amounts") else "")
             for f in found]
    msg = "\n## Possible new calls from the UKRI feed\n\n" + ("\n".join(lines) if lines else "_None this week._") + \
          "\n\nThe feed only lists recent posts, so also skim the AHRC opportunity list and the Innovation Funding Service now and then.\n"
    _append(msg)
    print(msg)
    return 0


def _append(text: str) -> None:
    REPORTS.mkdir(exist_ok=True)
    p = REPORTS / "latest.md"
    p.write_text((p.read_text(encoding="utf-8") if p.exists() else "") + text, encoding="utf-8")


if __name__ == "__main__":
    sys.exit(main())
