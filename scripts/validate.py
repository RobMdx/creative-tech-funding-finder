"""Check the site data files before anything is deployed.

Run: python3 scripts/validate.py
Exits with status 1 and a list of problems if any file is malformed.
GitHub runs this before building the site, so bad data never reaches the published page.
"""
from __future__ import annotations

import re
import sys

from common import FACILITIES, FUNDERS, LEVELS, PERSONAS, PURPOSES, load

DL = re.compile(r"^(always|tbc|\d{4}|\d{4}-\d{2}|\d{4}-\d{2}-\d{2})$")
DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
ID = re.compile(r"^[a-z0-9][a-z0-9-]{1,60}$")


def main() -> int:
    errs: list[str] = []
    schemes = load("schemes.json").get("schemes", [])
    personas = load("personas.json").get("personas", [])
    gaps = load("gaps.json").get("gaps", [])
    status = load("status.json")
    projects = load("projects.json").get("rows", [])
    config = load("config.json")

    seen = set()
    for i, s in enumerate(schemes):
        where = f"schemes[{i}] {s.get('id', '?')}"
        for k in ("id", "n", "f", "amt", "dl", "purpose", "fac", "note", "u", "checked", "roles"):
            if k not in s:
                errs.append(f"{where}: missing '{k}'")
        if not ID.match(str(s.get("id", ""))):
            errs.append(f"{where}: id must be lower-case letters, digits and hyphens")
        if s.get("id") in seen:
            errs.append(f"{where}: duplicate id")
        seen.add(s.get("id"))
        if s.get("f") not in FUNDERS:
            errs.append(f"{where}: funder 'f' must be one of {FUNDERS}")
        if not DL.match(str(s.get("dl", ""))):
            errs.append(f"{where}: dl must be always, tbc, yyyy, yyyy-mm or yyyy-mm-dd")
        if s.get("opens") and not DATE.match(str(s["opens"])):
            errs.append(f"{where}: opens must be yyyy-mm-dd or null")
        if not DATE.match(str(s.get("checked", ""))):
            errs.append(f"{where}: checked must be yyyy-mm-dd")
        if not str(s.get("u", "")).startswith("https://"):
            errs.append(f"{where}: source url 'u' must start with https://")
        for p in s.get("purpose", []):
            if p not in PURPOSES:
                errs.append(f"{where}: unknown purpose '{p}'")
        for f in s.get("fac", []):
            if f not in FACILITIES:
                errs.append(f"{where}: unknown facility '{f}'")
        for k in ("min", "max"):
            if s.get(k) is not None and not isinstance(s[k], (int, float)):
                errs.append(f"{where}: {k} must be a number or null")
        roles = s.get("roles", {})
        for p in PERSONAS:
            r = roles.get(p)
            if not r:
                errs.append(f"{where}: roles missing persona '{p}'")
            elif r.get("lvl") not in LEVELS or not r.get("txt"):
                errs.append(f"{where}: roles.{p} needs lvl in {LEVELS} and txt")

    ids = {p.get("id") for p in personas}
    if ids != set(PERSONAS):
        errs.append(f"personas.json: ids must be exactly {PERSONAS}")
    for g in gaps:
        for k in ("id", "t", "h", "fac", "ev", "idea", "s", "order"):
            if k not in g:
                errs.append(f"gaps {g.get('id', '?')}: missing '{k}'")
    if not DATE.match(str(status.get("lastChecked", ""))):
        errs.append("status.json: lastChecked must be yyyy-mm-dd")
    for j, row in enumerate(projects):
        if not isinstance(row, list) or len(row) != 9:
            errs.append(f"projects.json rows[{j}]: expected 9 columns")
            break

    for k in ("contactName", "contactEmail", "repo", "siteUrl"):
        if k not in config:
            errs.append(f"config.json: missing '{k}'")
    if config.get("repo") and not re.match(r"^[\w.-]+/[\w.-]+$", config["repo"]):
        errs.append("config.json: repo must look like owner/name")
    if config.get("siteUrl") and not config["siteUrl"].startswith("https://"):
        errs.append("config.json: siteUrl must start with https://")

    if errs:
        print("Data check failed:\n- " + "\n- ".join(errs))
        return 1
    print(f"Data check passed: {len(schemes)} schemes, {len(personas)} roles, {len(gaps)} ideas, {len(projects)} past awards.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
