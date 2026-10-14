# Data files: what each field means

All content lives in `data/` at the top of the repository. Edit these files, never `site/`. GitHub checks them with `scripts/validate.py` and rebuilds `site/` automatically. If the check fails, nothing is rebuilt and the live site stays as it was.

## `schemes.json` → `{"schemes": [ … ]}`

One object per funding route.

| Field | Required | Meaning | Allowed values |
|---|---|---|---|
| `id` | yes | Stable identifier, never reused | lower-case letters, digits, hyphens |
| `n` | yes | Name as the funder writes it | text |
| `f` | yes | Funder group | `AHRC`, `Innovate UK`, `UKRI-wide / joint`, `Research England` |
| `amt` | yes | Amount, in the funder's words | text, e.g. `£100k–£300k fEC` |
| `min`, `max` | no | Amount range in pounds, used by the size filter | number or `null` (`null` both = non-cash or varies) |
| `dl` | yes | Closing date | `yyyy-mm-dd`, `always` (no deadline), `yyyy-mm` or `yyyy` (expected), `tbc` |
| `opens` | no | Opening date, when it's in the future | `yyyy-mm-dd` or `null` |
| `purpose` | yes | What it's for (filter) | any of `research`, `ke`, `commercial`, `infrastructure`, `fellowship`, `compute`, `training`, `network` |
| `fac` | yes | Faculty facilities it fits (filter) | `["all"]`, or any of `film`, `photo`, `ai`, `fab`, `mocap`, `elec`, `print`, `dark`, `tex`, `fine` |
| `note` | yes | Two plain sentences: what it funds and the key condition | text |
| `u` | yes | The funder's own page for this call. **Every fact must come from here.** | `https://…` |
| `checked` | yes | Date a person or the weekly check last confirmed the facts | `yyyy-mm-dd` |
| `roles` | yes | What each persona can do (see below) | object with all 8 persona keys |
| `review` | no | `ai-draft` marks an entry drafted by the AI step; the site labels it. Delete the field once a person has checked it. | `ai-draft` |

### `roles`

There are exactly eight keys: `tech`, `practitioner`, `ecr`, `academic`, `pi`, `pgr`, `ps`, `partner`. Each value is `{"lvl": …, "txt": …}`:

| `lvl` | Shown as | Use when the call page says… |
|---|---|---|
| `lead` | Can lead | this person can be the project lead |
| `colead` | Co-lead | they can be a co-lead but not the lead |
| `team` | Named team role | they can be a named, costed team member (Specialist, Technician, Professional Enabling Staff…) |
| `partner` | Partner | they take part as a partner organisation |
| `check` | Check eligibility | **the page doesn't settle it.** Say what to check. |
| `info` | Useful to know | it's support or context rather than a role |
| `no` | Not eligible | the page rules them out |

`txt` is one sentence, in plain English, drawn from the call page. If in doubt, use `check`. Never guess.

## `personas.json` → `{"personas": [ … ]}`

The eight "Who are you?" buttons: `id`, `name`, `tip` (the "Start here" text), `order`. The ids must match the role keys above.

## `gaps.json` → `{"gaps": [ … ]}`

The "Ideas & white space" rows: `id`, `t` (intersection), `h` (`sparse`, `growing` or `crowded`), `fac` (facility keys), `ev` (evidence), `idea` (a starter idea, labelled on the site as a suggestion), `s` (first scheme), `order`.

## `projects.json` → `{"rows": [ … ], "source": "…"}`

Past awards from Gateway to Research. Each row is `[title, funder group, funder detail, grant ref, lead organisation, start year, value in £ or null, topic codes separated by ";", GtR url]`.

## `config.json`

| Field | Meaning |
|---|---|
| `contactName` | Shown as "Maintained by…" and in snapshots as "Contact … for info." |
| `repo` | `owner/name` of this GitHub repository. Turns on the "Report on GitHub" button. |
| `reportEmail` | Optional. Turns on the "Email the maintainer" button. Leave it as `""` to keep an address off the public site. |
| `siteUrl` | The public address, e.g. `https://creative-tech-funding.netlify.app`. Used as the "live version" link in snapshots. |

## `status.json`

`lastChecked` (`yyyy-mm-dd`), `cadence`, `checkedBy`, `note`, and `changes` (a list of `{date, text}` entries; the newest 12 show on the Updates tab, and only the last 30 are kept).
