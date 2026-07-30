---
created: 2026-04-13
updated: 2026-04-14
tags: [ref, slang, date, time, secexpr, construction, TimeFromDateNew]
status: dormant
relates:
  - slang/secexpr-gotchas.md
  - slang/utility-libs.md
---

# Slang Date & Time — Quick Reference

Key patterns for constructing dates and times in Slang. Full docs in `workspace/docs/slang/dates/` and `workspace/docs/slang/time/`.

## Date Construction

- **Inside scripts:** bare literals work: `D = 27Mar2026;`
- **In secexpr `-e` mode:** bare literals FAIL (parser sees `27` + symbol `Mar2026`). Always wrap: `Date( "27Mar2026" )`
- **Format:** `DDMmmYYYY` — 4-digit year preferred (`"27Mar2026"`), 2-digit also works in scripts (`"27Mar26"`)
- **Today:** `Today()` returns current date
- **Components:** `D.Day`, `D.Month`, `D.Year`, `D.DayOfWeek` (0=Sun..6=Sat)
- **Arithmetic:** `D + 1` (calendar days), `D + RDate( "3b" )` (business days), `D + RDate( "1m" )` (months)
- **Business day count:** `GsDateCountBusDays( "BRR", Date1, Date2 )`
- **Relative date:** `RDateAdd( "-1b", Today(), "SAOE" )` — business day arithmetic with exchange calendar

## Time Construction

- **From date:** `TimeFromDateNew( Date( "27Mar2026" ), "America/New_York", 14, 0, 0 )` — builds Time with timezone, hour, minute, second
- **Current time:** `Time()` returns current timestamp
- **Components:** `T.Date`, `T.Hour`, `T.Minute`, `T.Second`
- **Common timezones:** `"America/New_York"`, `"America/Sao_Paulo"`, `"Europe/London"`, `"Asia/Tokyo"`, `"GMT"`, `"UTC"`

## Libraries

- `_LIB Date Functions` — `@DateFns::YYYYMMDD( Date, Delimiter := "-" )`, formatting, holidays, business days
- `_LIB Time Functions` — `@Time::ToEpochMilli()`, timezone conversion, formatting
