---
name: DIRGET
description: Look up employee details (name, office, title, department, manager) from the GS directory by kerberos ID or name search
---

# DIRGET — Employee Directory Lookup

> **Purpose:** Query the EPSSP DirGet service to retrieve employee details — name, office location, title, department, manager, and contact info — given a kerberos ID **or a name search term**.

**Out of scope:** Modifying directory records, bulk org-chart traversal, or photo retrieval.

## Skill Identity

| Field | Value |
|-------|-------|
| **Name** | `DIRGET` |
| **Scope** | Read-only employee directory lookup |
| **Inputs** | One or more kerberos IDs, or a name search term |
| **Outputs** | Console summary + JSON in `workspace/tmp/` |
| **Authority** | Read-only (GSSSO auth) |

## When to Use

- Look up an employee's **office location** (city, country, region).
- Find a person's **department**, **title**, **manager**, or **division**.
- Resolve a kerberos to a full name.
- **Search by name** when you don't know the kerberos (e.g., from an `orderedFor` field).
- Determine whether someone is in a specific geography (e.g., Brazil vs US).

Do **not** use for:
- Bulk org-chart queries → use dedicated HR/org APIs.
- System account lookups → use **APPDIR_API**.

## Connection

| Field | Value |
|-------|-------|
| **DirGet URL** | `https://www.epssp.site.gs.com/ssps/ProdSource/Dirget?K={kerberos}` |
| **Search URL** | `https://www.epssp.site.gs.com/ssps/ProdSource/Dirget?ajax=true&action=HeaderSearch&term={term}` |
| **Auth** | GSSSO cookie |
| **DirGet Response** | HTML page with structured employee fields |
| **Search Response** | JSON array of `"LastName, FirstName [Division] {kerberos}"` strings |

## Usage

```bash
# Single kerberos
uv run python skills/DIRGET/src/dirget.py jdoe

# Multiple kerberos IDs
uv run python skills/DIRGET/src/dirget.py jdoe jdoe1 jdoe2

# JSON output
uv run python skills/DIRGET/src/dirget.py --json jdoe jdoe1

# Filter by country (case-insensitive substring match)
uv run python skills/DIRGET/src/dirget.py --country brazil jdoe jdoe1 jdoe2 jdoe3

# Search by name (returns matching entries)
uv run python skills/DIRGET/src/dirget.py --search "john doe"

# Search by name + resolve full details for each match
uv run python skills/DIRGET/src/dirget.py --search "Doe, John" --resolve

# Search + resolve + JSON + country filter
uv run python skills/DIRGET/src/dirget.py --search "doe" --resolve --json --country brazil
```

## Output Fields

| Field | Example |
|-------|---------|
| `name` | Doe, John |
| `title` | Vice President |
| `location` | Example City, 000/000, 000A00 (Country, Region) |
| `city` | Example City |
| `country` | Country |
| `region` | Region |
| `cityCode` | 000 (Example City) |
| `department` | Example Strats |
| `division` | GBM Public |
| `manager` | (manager kerberos if available) |

## Troubleshooting

| Problem | Fix |
|---------|-----|
| 401 Unauthorized | GSSSO cookie expired — script auto-obtains it |
| Empty location | Kerberos may be inactive/terminated — check HTML manually |
| Wrong person | Verify kerberos spelling (case-insensitive) |

## Key Lesson

**Department name does NOT indicate office location.** For example, a department labelled "US" may still have members in another country. Always use this skill to determine a person's actual office city/country.

## Task-Based Execution

**Task label:** `dirget` | **Args file:** `workspace/tmp/dirget_args.json`

Preferred. Write args JSON, then `run_task("dirget")`. CLI args pass through via `%*`.

## Links

- memory/_dormant/ref/gssso-auth.md — GSSSO authentication (used for directory API)
TEST_LINE_1785360309
