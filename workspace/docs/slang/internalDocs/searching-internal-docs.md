# Searching Internal Documentation

When asked about internal/company-specific topics (teams, tools, platforms, workflows, SecDb concepts, etc.), use the sources below to find answers.

## Decision flow

```
1. Is the question very narrow and specific (e.g. "what is Team X's distro list",
   "who owns service Y")? Is it related to Syntax (such as Slang) or specific jobs/deployments
     YES --> Skip EngHub. Go straight to Confluence (Section B).
     NO  --> Continue to step 2.

2. Search EngHub first (Section A).
   Are the results clearly relevant and authoritative?
     YES --> Use them as the primary source. Optionally supplement with Confluence.
     NO / few results / off-topic results --> Search Confluence (Section B).

3. If you searched both, synthesize a single answer that combines what you learned
   from each source. Prefer newer information when sources conflict.
```



## CRITICAL: Batch everything -- minimize terminal round-trips

Every terminal call costs seconds. The #1 cause of slow research is making too many sequential calls.

1. **Run ALL search variations in one terminal call** -- multiple CQL queries, synonyms/abbreviations/full names. One call, not five.
2. **Batch-read candidate pages in one loop** -- never one `Read-ConfPage` per terminal call. Read 3-5 pages per batch, truncate each to ~3000 chars, then decide which deserve a full read:
   ```powershell
   @(id1, id2, id3, id4, id5) | ForEach-Object {
     $t = Read-ConfPage $_
     Write-Host "`n=== PAGE $_ ==="
     Write-Host $t.Substring(0, [Math]::Min(3000, $t.Length))
   }
   ```
   After scanning truncated previews, do a second batch for full reads of only the relevant pages.

## General research rules

1. **Read at least 10 pages/chunks before answering** unless the first few completely answer the question. Different teams document the same topic differently. One page is rarely enough.
2. **When results conflict, prefer newer pages.**
3. **Minimize terminal round-trips.** Batch reads into as few calls as possible.

---

## A. EngHub

EngHub is the firm's central engineering documentation hub. Product teams publish official docs, getting-started guides, and release notes here. It has a strong search API that returns chunked, pre-extracted text -- so you can read content directly from search results without fetching full pages.

### How it works

- **Base search URL:** `https://search.enghub.site.gs.com/search/enghub`  
  **WARNING:** This is the ONLY correct URL. Do NOT use `enghub.gs.com/search/api/...` or any other endpoint -- those return client-rendered HTML, not JSON.
- **Auth:** Kerberos (`-UseDefaultCredentials`)
- **Query params:** `searchQuery` (the search terms), `page`, `pageSize`
- **Response:** JSON with `data.totalCount` and `data.searchResults[]`. Each result has a `fields` object containing:
  - `title` -- page title
  - `data` -- the actual text content of the chunk (already extracted, no HTML stripping needed)
  - `page_address_s` -- the page path on EngHub (e.g. `/secdb-platform/slangai/docs/intro`)
  - `chunk_id` -- which chunk of the page this is (pages are split into numbered chunks)
  - `system_entity_s` -- the platform/product the page belongs to
  - `last_update_date_l` -- timestamp for recency comparison

### Approach

1. **Search** with a relevant query. URL-encode the search terms. Request a reasonable page size (20-50).
2. **Scan results** -- the `fields.data` field already contains readable text. You often don't need to fetch the full page. Read the chunks directly from the search response.
3. **Look for multiple chunks of the same page** if you need deeper coverage -- search again with more specific terms or request more results.
4. **Use `page_address_s`** to identify which product/team the doc belongs to, and to judge authority.
5. Tip: if the search query uses **exact phrases** (wrap in `"quotes"`), results are more precise.

### Notes
- EngHub pages are client-side rendered, so fetching the HTML page URL directly gives you a JavaScript shell, not content. **Always use the search API** to get text.
- The search API returns chunks (typically ~500 tokens each). A single page may span many chunks. If you need the full page, collect all chunks with the same `page_address_s`.

---

## B. Confluence

Confluence is used by many teams for internal wikis, runbooks, and project docs. It is better for very specific team-level information, distribution lists, and older documentation that hasn't been migrated to EngHub.

For full details on Confluence auth, search (CQL), and reading pages, see [confluence.md](confluence.md) in this directory.
