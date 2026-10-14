"""Weekly deterministic check of every scheme's source page.

What it does, without any AI:
- ukri.org/opportunity pages: reads "Opportunity status", "Opening date",
  "Closing date", "Award range", "Total fund" and "Maximum award".
- Innovation Funding Service pages: reads "Competition opens" and
  "Competition closes".
- Any other page: checks the link still works.

Date changes it can read with confidence are written into
data/schemes.json. Amount and status differences are only reported,
for a person to confirm. Results go to reports/weekly-YYYY-MM-DD.md, and
the run is logged in data/status.json.

Run: python3 scripts/check_sources.py            (updates the data files)
     python3 scripts/check_sources.py --dry-run  (report only; changes nothing)
"""
from __future__ import annotations

import datetime as dt
import sys
import time

from common import REPORTS, fetch, load, page_text, parse_ifs, parse_ukri, save, today


def days_until(d: str) -> int | None:
    try:
        return (dt.date.fromisoformat(d) - dt.date.today()).days
    except ValueError:
        return None


def main() -> int:
    dry = "--dry-run" in sys.argv
    data = load("schemes.json")
    schemes = data["schemes"]
    now = today()
    applied, review, broken, unparsed, soon = [], [], [], [], []

    for s in schemes:
        url = s["u"]
        code, body = fetch(url)
        time.sleep(1)  # be polite to funder sites
        if code != 200 or not body:
            broken.append(f"- **{s['n']}**: link returned {code or 'no response'} ({url})")
            continue
        text = page_text(body)

        if "ukri.org/opportunity/" in url:
            info = parse_ukri(text)
            new_dl = "always" if info["always_open"] else info["closing"]
            if new_dl and new_dl != s["dl"]:
                applied.append(f"- **{s['n']}**: deadline {s['dl']} → {new_dl} (page says “{info['closing_raw']}”)")
                s["dl"] = new_dl
            if info["opening"] and info["opening"] > now and info["opening"] != s.get("opens"):
                applied.append(f"- **{s['n']}**: opens {s.get('opens')} → {info['opening']}")
                s["opens"] = info["opening"]
            if info["status"] and info["status"].lower().startswith("closed") and s["dl"] not in ("always",) and (days_until(s["dl"]) or 0) > 0:
                review.append(f"- **{s['n']}**: page says status “{info['status']}” but our deadline is {s['dl']}")
            amounts = info["award_range"] or info["maximum"] or info["total_fund"]
            ours = [v for v in (s.get("min"), s.get("max")) if v]
            if amounts and ours and max(amounts) not in ours and max(amounts) != max(ours):
                review.append(f"- **{s['n']}**: page amounts {amounts} differ from ours {ours} (“{s['amt']}”)")
            if new_dl:
                s["checked"] = now
            elif info["status"]:
                review.append(f"- **{s['n']}**: status read (“{info['status']}”) but no closing date could be read; check the page")
            else:
                unparsed.append(f"- **{s['n']}**: page loaded but the key-details block wasn't found ({url})")
        elif "apply-for-innovation-funding.service.gov.uk" in url:
            info = parse_ifs(text)
            if info["closing"] and info["closing"] != s["dl"]:
                applied.append(f"- **{s['n']}**: deadline {s['dl']} → {info['closing']}")
                s["dl"] = info["closing"]
            if info["opening"] and info["opening"] != s.get("opens") and info["opening"] > now:
                applied.append(f"- **{s['n']}**: opens {s.get('opens')} → {info['opening']}")
                s["opens"] = info["opening"]
            if info["closing"]:
                s["checked"] = now
            else:
                unparsed.append(f"- **{s['n']}**: page loaded but no 'Competition closes' line was found ({url})")
        else:
            unparsed.append(f"- **{s['n']}**: link works; details on this site aren't machine-read, so check by hand ({url})")

    for s in schemes:
        d = days_until(s["dl"]) if len(s["dl"]) == 10 else None
        if d is not None and 0 <= d <= 30:
            soon.append(f"- **{s['n']}**: closes {s['dl']} ({d} days)")

    if len(broken) > len(schemes) / 2:
        print(f"Stopping: {len(broken)} of {len(schemes)} links failed, which looks like a network problem, "
              "not real changes. Nothing was saved.\n" + "\n".join(broken))
        return 1

    if dry:
        print("DRY RUN: nothing saved.\n")
    else:
        save("schemes.json", data)

    status = load("status.json")
    status["lastChecked"] = now
    summary = f"Automated check: {len(applied)} date change(s) applied, {len(review)} item(s) for review, {len(broken)} broken link(s)."
    status.setdefault("changes", []).append({"date": now, "text": summary})
    status["changes"] = status["changes"][-30:]
    if not dry:
        save("status.json", status)

    REPORTS.mkdir(exist_ok=True)
    sec = lambda title, items: f"## {title}\n\n" + ("\n".join(items) if items else "_None._") + "\n"
    report = "\n".join([
        f"# Weekly source check, {now}\n",
        summary + "\n",
        sec("Date changes applied (please confirm)", applied),
        sec("Needs a person to review", review),
        sec("Closing in the next 30 days", soon),
        sec("Broken or unreachable links", broken),
        sec("Not machine-checked", unparsed),
    ])
    if not dry:
        import json
        (REPORTS / "summary.json").write_text(json.dumps({
            "date_changes": len(applied), "review": len(review), "broken": len(broken),
            "not_machine_checked": len(unparsed), "closing_soon": len(soon)}, indent=1), encoding="utf-8")
        (REPORTS / f"weekly-{now}.md").write_text(report, encoding="utf-8")
        (REPORTS / "latest.md").write_text(report, encoding="utf-8")
    print(report)
    return 0


if __name__ == "__main__":
    sys.exit(main())
