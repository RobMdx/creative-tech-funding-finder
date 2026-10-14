"""Decide whether this week's check can publish itself.

A week is "quiet" when the only changes are dates read from the funder
pages and nothing needs a person: no items for review, no broken links,
no possible new calls, no AI drafts, no unread feed, and no open visitor
reports. Quiet weeks are committed straight to main and Netlify publishes
them. Anything else becomes a pull request for a person to check.

Set AUTO_PUBLISH=false in the workflow to always open a pull request.

Writes quiet=true|false to $GITHUB_OUTPUT (and prints the reason).
"""
from __future__ import annotations

import json
import os
import sys

from common import REPORTS


def main() -> int:
    s = json.loads((REPORTS / "summary.json").read_text(encoding="utf-8")) if (REPORTS / "summary.json").exists() else {}
    reports = int(os.environ.get("OPEN_REPORTS", "0") or 0)
    reasons = []
    for key, label in [("review", "items need review"), ("broken", "broken links"), ("new_calls", "possible new calls"),
                       ("ai_drafts", "AI-drafted entries"), ("feed_error", "the UKRI feed couldn't be read")]:
        if s.get(key):
            reasons.append(f"{s[key]} {label}")
    if reports:
        reasons.append(f"{reports} open visitor report(s)")
    if not s:
        reasons.append("no summary was produced")
    if os.environ.get("AUTO_PUBLISH", "true").lower() != "true":
        reasons.append("auto-publish is switched off")
    quiet = not reasons
    print("Quiet week: publishing automatically." if quiet else "Needs a person: " + "; ".join(reasons))
    out = os.environ.get("GITHUB_OUTPUT")
    if out:
        with open(out, "a", encoding="utf-8") as f:
            f.write(f"quiet={'true' if quiet else 'false'}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
