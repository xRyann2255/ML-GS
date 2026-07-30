# Skills Index

All available skills in this repository, grouped by domain.

---

## ML Volatility Forecasting

| Skill | Path | Description |
|-------|------|-------------|
| **DATA_AUDIT** | [DATA_AUDIT/SKILL.md](DATA_AUDIT/SKILL.md) | Comprehensive data integrity audit: validate parquets, detect NaN/gaps/schema drift, assess layer readiness, update `data/manifest.json`. |
| **DATA_INGEST** | [DATA_INGEST/SKILL.md](DATA_INGEST/SKILL.md) | Fetch tick data (Chunk Store), daily data (TSDB), IV surface (Marquee ERDVOL). Bulk ingestion to Parquet/CSV. |
| **FEATURE_BUILD** | [FEATURE_BUILD/SKILL.md](FEATURE_BUILD/SKILL.md) | Compute feature layers 0–6 from raw market data. HAR core, semivariances, IV/VRP, microstructure, cross-asset, calendar, interactions. |
| **MODEL_TRAIN** | [MODEL_TRAIN/SKILL.md](MODEL_TRAIN/SKILL.md) | Train volatility models with proper CV (purged k-fold, expanding window). HAR baselines, Ridge/Lasso, LightGBM (QLIKE objective), LSTM/TCN, ensemble. |
| **EVALUATE** | [EVALUATE/SKILL.md](EVALUATE/SKILL.md) | Run evaluation suite: QLIKE/MSE metrics, Diebold-Mariano tests, Model Confidence Set, tournament tables, overfitting detection. |
| **BACKTEST** | [BACKTEST/SKILL.md](BACKTEST/SKILL.md) | Economic value testing: IV-RV gap trading signal, vol-targeting portfolio, P&L backtest with transaction costs, Sharpe/drawdown analysis. |
| **RESEARCH** | [RESEARCH/SKILL.md](RESEARCH/SKILL.md) | Structured research sessions: load journal, explore topic on real data, document findings, update research notes. Agent-driven protocol. |
| **NOTEBOOK** | [NOTEBOOK/SKILL.md](NOTEBOOK/SKILL.md) | Jupyter notebook workflow: creation with templates, cell structure conventions, visualization standards for ML vol exploration. |

## Slang / SecDB

| Skill | Path | Description |
|-------|------|-------------|
| **SLANG_READ** | [SLANG_READ/SKILL.md](SLANG_READ/SKILL.md) | Read Slang script content — VFS-first (zero allows), secexpr/CVS fallback. |
| **SLANG_EDIT** | [SLANG_EDIT/SKILL.md](SLANG_EDIT/SKILL.md) | Edit, create, rewrite, read, and delete Slang scripts via `secexpr`. The primary sanctioned write path for SecDB-hosted scripts. |
| **SLANG_EVAL** | [SLANG_EVAL/SKILL.md](SLANG_EVAL/SKILL.md) | Evaluate Slang expressions and run scripts via the VS Code extension's SSP/REPL endpoint. ~100x faster than cold-start secexpr. Requires active extension REPL session. |
| **SLANG_LINT** | [SLANG_LINT/SKILL.md](SLANG_LINT/SKILL.md) | Run native Slang lint (`@LIBSlang::Lint`) or precommit lint (`@ScriptVal::PreCommit Check Lint`) through a Python wrapper over `secexpr --safe`. |
| **SLANG_GLIMPSE** | [SLANG_GLIMPSE/SKILL.md](SLANG_GLIMPSE/SKILL.md) | Search Slang codebases via ELPS (Elasticsearch) or legacy Glimpse. Find function definitions, references, comments, links, and script names. |
| **SLANG_REVIEW** | [SLANG_REVIEW/SKILL.md](SLANG_REVIEW/SKILL.md) | Create or update ScriptReview code reviews for Slang changes, including CVSed and uncvsed scripts. Manages review metadata and diff refreshes. |
| **SLANG_REVIEW_INSPECT** | [SLANG_REVIEW_INSPECT/SKILL.md](SLANG_REVIEW_INSPECT/SKILL.md) | Read-only validator for ScriptReview objects. Loads review metadata, scripts, revisions, and web-derived checks (shame, missing testing headers). |
| **SLANG_REGTEST_FIX** | [SLANG_REGTEST_FIX/SKILL.md](SLANG_REGTEST_FIX/SKILL.md) | End-to-end workflow for diagnosing failing RegTests, fixing issues, applying cleanup, linting, rerunning tests, and submitting review. |
| **SLANG_CLEANUP** | [SLANG_CLEANUP/SKILL.md](SLANG_CLEANUP/SKILL.md) | Apply Slang best-practice and formatting conventions to scripts — cleanup/audit step for RegTests and general style normalization. |
| **SLANG_COPILOT** | [SLANG_COPILOT/SKILL.md](SLANG_COPILOT/SKILL.md) | Setup guide for pulling the Slang Copilot customization repo into `workspace/docs/slang/` for local AI guidance. |
| **SECDB_POSITION** | [SECDB_POSITION/SKILL.md](SECDB_POSITION/SKILL.md) | Source SecDB positions from books/portfolios with correct diddle patterns for historical (archive) and realtime (intraday) PnL computation. |
| **SECDB_INSPECT** | [SECDB_INSPECT/SKILL.md](SECDB_INSPECT/SKILL.md) | Inspect SecDB security instream (stored VT) values via DiskInstreamValues trace parsing. Supports JSON/flat output, book-based DB resolution, and recursive inspection. |
| **SECDB_DIFF** | [SECDB_DIFF/SKILL.md](SECDB_DIFF/SKILL.md) | Compare instream (stored VT) values between two SecDB securities side-by-side. Outputs diffs as JSON or table. Reuses SECDB_INSPECT for trace parsing. |
| **SECDB_TRANSLOG** | [SECDB_TRANSLOG/SKILL.md](SECDB_TRANSLOG/SKILL.md) | Query SecDB transaction logs (change history) for any security in a database. Based on `_UT Point Finger of Blame` (PFOB). Supports table/JSON output, book-based DB resolution, and configurable transaction limits. |
| **CVS** | [CVS/SKILL.md](CVS/SKILL.md) | Read-only CVS inspection: revision history (`rlog`), diffs (`rdiff`), and blame/annotation (`rannot`) for Slang and other repository files. |

## Infrastructure & Auth

| Skill | Path | Description |
|-------|------|-------------|
| **GIT** | [GIT/SKILL.md](GIT/SKILL.md) | Run git commands via task wrapper to avoid Copilot Allow prompts. Supports any git subcommand with JSON args file. |
| **GIT_COMMIT** | [GIT_COMMIT/SKILL.md](GIT_COMMIT/SKILL.md) | Auto-group changed files by concern, generate conventional commit messages, and execute all commits + push in one task invocation. |
| **GSSSO_AUTH** | [GSSSO_AUTH/SKILL.md](GSSSO_AUTH/SKILL.md) | Obtain a `GSSSO` cookie via Kerberos/SPNEGO for authenticating to internal GS HTTP APIs. Dependency skill used by other web-calling skills. |
| **GITLAB_PIPELINES** | [GITLAB_PIPELINES/SKILL.md](GITLAB_PIPELINES/SKILL.md) | GitLab SSO auth and pipeline inspection — check pipelines, jobs, runner tags, CI lint results, and failure diagnostics. |
| **GITLAB_SEARCH** | [GITLAB_SEARCH/SKILL.md](GITLAB_SEARCH/SKILL.md) | Search GitLab code, MRs, commits, issues, and projects via the Search API — global, group, or project scope. |
| **CANVAS** | [CANVAS/SKILL.md](CANVAS/SKILL.md) | Query the Canvas / AppDir 2.0 deployment API for infrastructure inventory — hosts, resources, beans, families, applications, and deployed applications (DIDs). Includes Python helper for common lookups. |
| **DIRGET** | [DIRGET/SKILL.md](DIRGET/SKILL.md) | Look up employee details (name, office location, title, department, manager) from the GS directory by kerberos ID. |
| **PRIME_QUERY** | [PRIME_QUERY/SKILL.md](PRIME_QUERY/SKILL.md) | Query Prime security details (identifiers, classification, builder, instrument metadata) from GS2ClassificationView by PrimeId or sector-specific lookup. |
| **NDS_INFRA** | [NDS_INFRA/SKILL.md](NDS_INFRA/SKILL.md) | Query NDS Infrastructure Services for user desktop assignments and machine details (OS, hardware, hypervisor, datacenter, IP, memory, disk). |
| **FORWARD_NETWORK** | [FORWARD_NETWORK/SKILL.md](FORWARD_NETWORK/SKILL.md) | Query the Forward Networks API: NQE queries, path searches, device/network/snapshot listing, topology, vulnerability analysis. Includes Python helper and full OpenAPI spec. |




## Operations & Monitoring

| Skill | Path | Description |
|-------|------|-------------|
| **PROCMON_LOGS** | [PROCMON_LOGS/SKILL.md](PROCMON_LOGS/SKILL.md) | Fetch stdout/stderr logs from Procmon for a given process, date, and master. Pulls logs into `workspace/tmp/` for analysis. |
| **PROCMON_JOBS** | [PROCMON_JOBS/SKILL.md](PROCMON_JOBS/SKILL.md) | Query Procmon ProcessList API to discover failed/running jobs by master, date, and process regex. OIDC/Kerberos auth. Dependency skill used by support skills. |
| **ETASK** | [ETASK/SKILL.md](ETASK/SKILL.md) | eTask API for scheduled job management — PACT workflows, job queries, troubleshooting. |
| **SLANG_TEST_COVERAGE** | [SLANG_TEST_COVERAGE/SKILL.md](SLANG_TEST_COVERAGE/SKILL.md) | Fetch test coverage data from EPSSP Sensitive Slang Procedure page: identify untested scripts, prioritized by references and size. |

## Messaging & Communication

| Skill | Path | Description |
|-------|------|-------------|
| **SYMPHONY** | [SYMPHONY/SKILL.md](SYMPHONY/SKILL.md) | Read messages from Symphony chat rooms and search rooms via the GS Bot Framework API Bridge. Read-only. |
| **OUTLOOK** | [OUTLOOK/SKILL.md](OUTLOOK/SKILL.md) | Create Outlook calendar appointments and email drafts via Slang OLE automation through `secexpr --safe`. |

## Documentation & Utilities

| Skill | Path | Description |
|-------|------|-------------|
| **ENGHUB** | [ENGHUB/SKILL.md](ENGHUB/SKILL.md) | Guide for populating `workspace/docs/` with internal EngHub documentation and navigating platform, IAM, cloud, storage, observability, AI, web, and risk docs. |
| **CONFLUENCE** | [CONFLUENCE/SKILL.md](CONFLUENCE/SKILL.md) | Fetch and sync Confluence pages for support memory and documentation. |
| **PDF_READER** | [PDF_READER/SKILL.md](PDF_READER/SKILL.md) | Extract text and metadata from local PDF files using `pypdf`. For summarization, search, and ingestion workflows. |
| **AI_SLOP_CLEANER** | [AI_SLOP_CLEANER/SKILL.md](AI_SLOP_CLEANER/SKILL.md) | Detect and clean AI slop patterns in code and documentation. |

## Python Data Access

| Skill | Path | Description |
|-------|------|-------------|
| **PYTHON_MARKET_DATA** | [PYTHON_MARKET_DATA/SKILL.md](PYTHON_MARKET_DATA/SKILL.md) | Query market data from Python: Chunk Store tick data (L1/L2), TSDB daily/realtime time series, PySlang setup. Covers equities, futures, FX, and rates. |


## Environment & Maintenance

| Skill | Path | Description |
|-------|------|-------------|
| **SEARCH** | [SEARCH/SKILL.md](SEARCH/SKILL.md) | Fast skill and memory search with cached inverted index. Priority-weighted ranking: skills > P0 > P1 > P2 > P3. Under 15ms warm, 100ms cold. |
| **PYTHON_PATH** | [PYTHON_PATH/SKILL.md](PYTHON_PATH/SKILL.md) | Resolve the Python interpreter path from `workspace/config/user.json` with auto-detection fallback. Dependency skill used by all Python-invoking skills. |
| **KILL_ORPHANS** | [KILL_ORPHANS/SKILL.md](KILL_ORPHANS/SKILL.md) | Kill orphaned `powershell.exe` and `conhost.exe` processes left behind by VS Code terminals. Frees memory and reduces process clutter. |
| **TMD** | [TMD/SKILL.md](TMD/SKILL.md) | Manage Technology@MyDesk (TMD) tickets — list orders, get details, submit firewall delete requests. |
