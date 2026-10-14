"""OPTIONAL: draft Finder entries for new calls with the Claude API.

Only runs when both of these are set (in GitHub: Settings → Secrets and
variables → Actions):
  ANTHROPIC_API_KEY  (a secret)
  ANTHROPIC_MODEL    (a variable; pick a current model id from
                      https://docs.claude.com/en/docs/about-claude/models)

For each candidate in proposals/new-calls.json it reads the call page, asks
the model to fill in the scheme fields and the role for each of the eight
personas, and adds the result to data/schemes.json with
"review": "ai-draft". The site shows these with a "roles drafted
automatically" label. Everything lands in the weekly pull request, so a
person approves or edits it before it goes live.

Never put the API key in the website. This script runs only inside GitHub.

Run: python3 scripts/ai_draft.py
"""
from __future__ import annotations

import json
import os
import re
import sys
import urllib.request

from common import FACILITIES, FUNDERS, LEVELS, PERSONAS, PURPOSES, REPORTS, ROOT, fetch, load, page_text, save, today

MAX_DRAFTS = 8

SYSTEM = f"""You add entries to a UK funding finder for creative AI and creative technology,
used by staff in a university creative industries faculty (film/TV, photography, AI, digital
manufacture, motion capture, electronics/robotics, print, darkroom, textiles, fine art).

Return ONE JSON object and nothing else, with these fields:
id (lower-case-hyphenated), n (call name), f (one of {FUNDERS}), amt (short text as the page states it),
min and max (numbers in pounds or null), dl (closing date yyyy-mm-dd, or "always", or "tbc"),
opens (yyyy-mm-dd or null), purpose (list from {PURPOSES}), fac (list from {FACILITIES}; ["all"] if any),
note (two plain sentences on what it funds and any key condition), u (the page url),
relevant (true or false: is this plausibly useful to creative-tech staff?),
roles: an object with exactly these keys {PERSONAS}. Each value is {{"lvl": one of {LEVELS}, "txt": one sentence}}.
Personas: tech = technician / research technical professional; practitioner = practitioner, curator or archivist
employed by the university; ecr = early career researcher; academic = academic not yet a project lead;
pi = experienced project lead; pgr = doctoral student; ps = research office or professional staff;
partner = external business or cultural organisation.

Rules: use ONLY what the page says. If the page doesn't settle a persona's eligibility, use "check" and say
what to check. Never invent amounts, dates or eligibility. Plain English, UK spelling."""


def call_model(key: str, model: str, page: str, url: str) -> dict | None:
    body = json.dumps({
        "model": model, "max_tokens": 2000, "system": SYSTEM,
        "messages": [{"role": "user", "content": f"Call page URL: {url}\n\nPage text:\n{page[:15000]}"}],
    }).encode()
    req = urllib.request.Request("https://api.anthropic.com/v1/messages", data=body, headers={
        "x-api-key": key, "anthropic-version": "2023-06-01", "content-type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            out = json.loads(r.read())
    except Exception as e:  # noqa: BLE001
        print(f"API call failed for {url}: {e}")
        return None
    text = "".join(b.get("text", "") for b in out.get("content", []) if b.get("type") == "text")
    m = re.search(r"\{.*\}", text, re.S)
    try:
        return json.loads(m.group(0)) if m else None
    except json.JSONDecodeError:
        return None


def ok(d: dict) -> bool:
    try:
        return (d["f"] in FUNDERS and all(p in PURPOSES for p in d["purpose"])
                and all(f in FACILITIES for f in d["fac"])
                and all(d["roles"][p]["lvl"] in LEVELS and d["roles"][p]["txt"] for p in PERSONAS)
                and re.match(r"^(always|tbc|\d{4}-\d{2}-\d{2})$", d["dl"]))
    except (KeyError, TypeError):
        return False


def main() -> int:
    key, model = os.environ.get("ANTHROPIC_API_KEY"), os.environ.get("ANTHROPIC_MODEL")
    if not key or not model:
        print("AI draft step skipped (ANTHROPIC_API_KEY or ANTHROPIC_MODEL not set).")
        return 0
    path = ROOT / "proposals" / "new-calls.json"
    if not path.exists():
        print("No proposals/new-calls.json; nothing to draft.")
        return 0
    cands = json.loads(path.read_text(encoding="utf-8"))[:MAX_DRAFTS]
    data = load("schemes.json")
    ids = {s["id"] for s in data["schemes"]}
    added, skipped = [], []
    for c in cands:
        code, body = fetch(c["url"])
        if code != 200:
            skipped.append(f"- {c['title']}: page unreachable")
            continue
        d = call_model(key, model, page_text(body), c["url"])
        if not d or not ok(d):
            skipped.append(f"- {c['title']}: draft didn't pass checks; add by hand if relevant")
            continue
        if not d.pop("relevant", True):
            skipped.append(f"- {c['title']}: judged not relevant")
            continue
        base, n = d["id"], 2
        while d["id"] in ids:
            d["id"], n = f"{base}-{n}", n + 1
        d.update({"u": c["url"], "checked": today(), "review": "ai-draft"})
        d.setdefault("opens", None)
        data["schemes"].append(d)
        ids.add(d["id"])
        added.append(f"- **{d['n']}** ({d['id']}): drafted; check every role before approving")
    save("schemes.json", data)
    msg = "\n## AI-drafted entries\n\n" + ("\n".join(added) if added else "_None added._") + \
          ("\n\nSkipped:\n" + "\n".join(skipped) if skipped else "") + "\n"
    REPORTS.mkdir(exist_ok=True)
    p = REPORTS / "latest.md"
    p.write_text((p.read_text(encoding="utf-8") if p.exists() else "") + msg, encoding="utf-8")
    print(msg)
    return 0


if __name__ == "__main__":
    sys.exit(main())
