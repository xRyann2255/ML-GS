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
uv run python skills/DIRGET/src/dirget.py silfel

# Multiple kerberos IDs
uv run python skills/DIRGET/src/dirget.py silfel heldtp tadesa

# JSON output
uv run python skills/DIRGET/src/dirget.py --json silfel heldtp

# Filter by country (case-insensitive substring match)
uv run python skills/DIRGET/src/dirget.py --country brazil silfel heldtp tadesa drisry

# Search by name (returns matching entries)
uv run python skills/DIRGET/src/dirget.py --search "andre souza"

# Search by name + resolve full details for each match
uv run python skills/DIRGET/src/dirget.py --search "Guo, Yifei" --resolve

# Search + resolve + JSON + country filter
uv run python skills/DIRGET/src/dirget.py --search "souza" --resolve --json --country brazil
```

## Output Fields

| Field | Example |
|-------|---------|
| `name` | Silva, Felipe T |
| `title` | Vice President |
| `location` | Sao Paulo, 700M/017, 314A02 (Brazil, Americas) |
| `city` | Sao Paulo |
| `country` | Brazil |
| `region` | Americas |
| `cityCode` | 063 (Sao Paulo) |
| `department` | Eqs Securitised Deriv Strats |
| `division` | GBM Public |
| `manager` | (manager kerberos if available) |

## Troubleshooting

| Problem | Fix |
|---------|-----|
| 401 Unauthorized | GSSSO cookie expired — script auto-obtains it |
| Empty location | Kerberos may be inactive/terminated — check HTML manually |
| Wrong person | Verify kerberos spelling (case-insensitive) |

## Key Lesson

**Department name does NOT indicate office location.** For example, "EQ Flow Vol Eng - US" or "Eqs Securitised Deriv Strats" may have members in São Paulo. Always use this skill to determine a person's actual office city/country.

## Task-Based Execution

**Task label:** `dirget` | **Args file:** `workspace/tmp/dirget_args.json`

Preferred. Write args JSON, then `run_task("dirget")`. CLI args pass through via `%*`.

## Links

- memory/ref/gssso-auth.md — GSSSO authentication (used for directory API)
