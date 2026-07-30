---
created: 2026-04-09
updated: 2026-04-15
tags: [ref, slang, utility, libraries, array, structure, string, tds]
status: dormant
relates:
  - slang/research.md
  - slang/best-practices.md
---

# Slang Utility Libraries

Commonly available library scripts with reusable functions:

## General (firm-wide)

- **_LIB Array Functions** — large collection of array functions
- **_LIB Array Utils** — large collection of array utility functions
- **_LIB Structure Functions** — large collection of structure functions
- **_LIB Functional** — functional programming helpers
- **_LIB String Functions** — string manipulation. Key: `String::Camelize( Str, Capitalize First Word := True )` for camelCase/PascalCase conversion. Prefer over custom converters.
- **_LIB TDS Utils** — TDS utility functions
- **_LIB Date Functions** — date formatting, parsing, holidays, business days (`@DateFns::`)
- **_LIB Time Functions** — time formatting and conversion (`@Time::`)
- **_LIB File Functions** — file IO, command output (`@File::`)
- **_LIB Log Fns** — logging helpers (`@Log::`)
- **_LIB Config Script** — config loading (`@Config::Load()`)
- **_LIB Book Functions** — book queries, book hierarchy traversal
- **_LIB Trade API** — trade creation, amendment, deletion (`@TradeAPI::`)
- **_LIB Statistics Functions** — `@Stats::Covariance`, `Variance`, `Standard Deviation`
- **_LIB Enumeration Functions** — portfolio/book enumeration
- **_LIB Container Functions** — SecDB container read/write
- **_LIB Database Fns** — database resolution (`@DatabaseFns::UnionDb`)
- **_LIB HTML Table Functions** — HTML table generation
- **_LIB SMTP Client** — email sending
- **_LIB GS Authentication** — GSSSO auth for CURL/REST
- **_LIB Procmon Fn Definitions** — Procmon status messages
- **_LIB Tsdb Functions** / **_LIB Tsdb Symbol Fns** — TSDB read/write/create

## Brazil Equities

These are GS internal Slang libraries (actual script names — not project-specific):

- **_LIB Eq Brazil Fns** (`Eq Brazil::`) — core utility: ETI enumeration, trade lifecycle, Kafka, S3, reporting
- **_LIB Eq1D Brazil Fns** (`Eq1D Brazil::`) — rate-to-price conversion, RMDS setup
- **_LIB Eq1D Brazil S3 Fns** (`Eq1D Latam S3::`) — universal S3/OBS storage (used by ~all modern scripts)
- **_LIB Eq Brazil Stats Fns** (`Eq Brazil Stats Fns::`) — Beta, EWMA statistics
- **_LIB Eq1D Brazil TDS Fns** (`Eq1D Brazil::`) — ~25 TDS directory factory functions
- **_LIB Eq1D Brazil Books** (`Eq1D Brazil Books::`) — book/portfolio mapping + allocation
- **_LIB Eq Brazil Inform Fns** (`Eq Brazil Inform::`) — Inform real-time notification client
- **_LIB Eq1D Brazil Tools** (`Eq1D Brazil::`) — strategy-to-book mapping, PETS mapping
