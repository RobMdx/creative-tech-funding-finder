"""Shared helpers for the Funding Finder scripts. Standard library only."""
from __future__ import annotations

import datetime as dt
import html
import json
import re
import urllib.error
import urllib.request
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"          # source of truth: edit these
SRC = ROOT / "src"            # page template
SITE = ROOT / "site"          # built output that Netlify publishes (generated, do not edit)
REPORTS = ROOT / "reports"

PERSONAS = ["tech", "practitioner", "ecr", "academic", "pi", "pgr", "ps", "partner"]
LEVELS = ["lead", "colead", "team", "partner", "check", "info", "no"]
FUNDERS = ["AHRC", "Innovate UK", "UKRI-wide / joint", "Research England"]
PURPOSES = ["research", "ke", "commercial", "infrastructure", "fellowship", "compute", "training", "network"]
FACILITIES = ["all", "film", "photo", "ai", "fab", "mocap", "elec", "print", "dark", "tex", "fine"]

USER_AGENT = "CreativeTechFundingFinder/1.0 (+weekly link and date check)"
MONTHS = {m: i for i, m in enumerate(
    ["january", "february", "march", "april", "may", "june", "july",
     "august", "september", "october", "november", "december"], start=1)}


def today() -> str:
    return dt.date.today().isoformat()


def load(name: str) -> dict:
    return json.loads((DATA / name).read_text(encoding="utf-8"))


def save(name: str, obj: dict) -> None:
    (DATA / name).write_text(json.dumps(obj, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


def fetch(url: str, timeout: int = 30) -> tuple[int, str]:
    """Return (http_status, body). Status 0 means a network error."""
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "text/html,application/xml"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        return e.code, ""
    except Exception:  # noqa: BLE001 - any network failure is reported, never fatal
        return 0, ""


class _Text(HTMLParser):
    BLOCK = {"p", "div", "li", "dt", "dd", "tr", "td", "th", "h1", "h2", "h3", "h4", "br", "section", "span", "strong", "b"}

    def __init__(self) -> None:
        super().__init__()
        self.out: list[str] = []
        self.skip = 0

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style", "noscript"):
            self.skip += 1
        if tag in self.BLOCK:
            self.out.append("\n")

    def handle_endtag(self, tag):
        if tag in ("script", "style", "noscript") and self.skip:
            self.skip -= 1
        if tag in self.BLOCK:
            self.out.append("\n")

    def handle_data(self, data):
        if not self.skip:
            self.out.append(data)


def page_text(body: str) -> str:
    """HTML to plain text, one block per line, whitespace collapsed."""
    p = _Text()
    p.feed(body)
    text = html.unescape("".join(p.out))
    lines = [re.sub(r"[ \t ]+", " ", ln).strip() for ln in text.splitlines()]
    return "\n".join(ln for ln in lines if ln)


def field(text: str, label: str) -> str | None:
    """Value after 'Label:' on the same line, or on the next non-empty line."""
    m = re.search(rf"(?im)^{re.escape(label)}\s*:?\s*(.*)$", text)
    if not m:
        return None
    val = m.group(1).strip()
    if val:
        return val
    rest = text[m.end():].lstrip("\n")
    return rest.split("\n", 1)[0].strip() or None


def parse_date(s: str | None) -> str | None:
    """'29 October 2026 4:00pm UK time' or 'Tuesday 8 December 2026 11:00am' -> '2026-10-29'."""
    if not s:
        return None
    m = re.search(r"(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})", s)
    if not m or m.group(2).lower() not in MONTHS:
        return None
    return dt.date(int(m.group(3)), MONTHS[m.group(2).lower()], int(m.group(1))).isoformat()


def money(s: str | None) -> list[int]:
    """All £ amounts in a string, as integers."""
    if not s:
        return []
    out = []
    for num, unit in re.findall(r"£\s?([\d,.]+)\s*(million|m|k|bn)?", s, flags=re.I):
        try:
            v = float(num.replace(",", ""))
        except ValueError:
            continue
        mult = {"million": 1e6, "m": 1e6, "k": 1e3, "bn": 1e9}.get((unit or "").lower(), 1)
        out.append(int(v * mult))
    return out


def parse_ukri(text: str) -> dict:
    """Read the key-details block of a ukri.org/opportunity page."""
    closing = field(text, "Closing date")
    info = {
        "status": field(text, "Opportunity status"),
        "opening": parse_date(field(text, "Opening date")),
        "closing_raw": closing,
        "closing": parse_date(closing),
        "always_open": bool(closing and re.search(r"no closing date", closing, re.I)),
        "total_fund": money(field(text, "Total fund")),
        "award_range": money(field(text, "Award range")),
        "maximum": money(field(text, "Maximum award")),
    }
    return info


def parse_ifs(text: str) -> dict:
    """Read an Innovation Funding Service competition overview page."""
    return {
        "opening": parse_date(field(text, "Competition opens")),
        "closing": parse_date(field(text, "Competition closes")),
        "not_open_yet": "has not yet opened" in text.lower(),
        "closed": bool(re.search(r"competition (?:has )?closed", text, re.I)),
    }
