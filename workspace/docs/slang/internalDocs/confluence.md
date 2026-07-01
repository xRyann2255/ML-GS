# Searching Confluence

Confluence is used by many teams for internal wikis, runbooks, and project docs. It is better for very specific team-level information, distribution lists, and older documentation that hasn't been migrated to EngHub.

## Research rules

1. **Read at least 10 pages before answering** unless the initial few are really good and answer the question completely. Different teams write about the same topic from their own angle. A single page is rarely enough for a well-rounded answer. You may need a lot more than 10 and to experiment with different search terms. Dont overdo it either. if result feels incomplete, ask user if they want u to spend more time on the search

2. **Batch page reads.** Read multiple pages in a single terminal call (loop over IDs) instead of one call per page. This is much faster.

# Step 1: Hit any Confluence URL to get the SAML form
$r1 = Invoke-WebRequest -Uri 'https://confluence.work.gs.com/' -UseDefaultCredentials -UseBasicParsing -SessionVariable session

# Step 2: Extract and POST the SAML response to complete auth
$relayState = ($r1.Content | Select-String 'name="RelayState" value="([^"]*)"').Matches[0].Groups[1].Value
$samlResponse = ($r1.Content | Select-String 'name="SAMLResponse" value="([^"]*)"').Matches[0].Groups[1].Value
$postUrl = ($r1.Content | Select-String 'action="([^"]*)"').Matches[0].Groups[1].Value
Invoke-WebRequest -Uri $postUrl -Method POST -Body @{ RelayState=$relayState; SAMLResponse=$samlResponse } -UseBasicParsing -WebSession $session -MaximumRedirection 10

# Step 3: Now use the authenticated $session for REST API calls
# Search by title:
#   cql=title~"search term"
# Search by page content:
#   cql=text~"search term"
# Combine conditions with AND/OR:
#   cql=text~"term1" AND text~"term2"
$r = Invoke-WebRequest -Uri 'https://confluence.work.gs.com/rest/api/content/search?cql=title~%22slang%22&limit=25&expand=space' -UseBasicParsing -WebSession $session
$data = $r.Content | ConvertFrom-Json
$data.results | ForEach-Object { "$($_.title) | https://confluence.work.gs.com$($_._links.webui)" }
