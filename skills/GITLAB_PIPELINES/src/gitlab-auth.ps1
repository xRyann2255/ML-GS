<#
.SYNOPSIS
    Authenticate to internal GitLab via Kerberos/SAML SSO and return a WebRequestSession.

.DESCRIPTION
    Follows the DesktopSSO → SAML → GitLab callback chain to obtain a
    _gitlab_session cookie. Returns the WebRequestSession object for use
    with subsequent Invoke-WebRequest calls.

.EXAMPLE
    $session = & .\gitlab-auth.ps1
    Invoke-WebRequest -Uri "https://gitlab.aws.site.gs.com/api/v4/projects" -WebSession $session
#>
[CmdletBinding()]
param(
    [string]$GitLabBase = "https://gitlab.aws.site.gs.com"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# --- 1. Verify Kerberos ticket ---
$klistOut = klist 2>&1
if ($LASTEXITCODE -ne 0) {
    throw "No Kerberos ticket found. Run 'kinit' first."
}
Write-Verbose "Kerberos ticket OK"

# --- 2. Start SSO flow — request a page that triggers SAML redirect ---
$startUrl = "$GitLabBase/"
$session  = $null

# First request: expect 302 → IdP
$r1 = Invoke-WebRequest -Uri $startUrl -MaximumRedirection 0 `
        -SessionVariable session -UseBasicParsing -ErrorAction SilentlyContinue -TimeoutSec 30

$location = $null
if ($r1.StatusCode -in 301,302,303,307,308) {
    $location = $r1.Headers["Location"]
} elseif ($r1.StatusCode -eq 200 -and $r1.Content -match '_gitlab_session') {
    # Already authenticated
    Write-Verbose "Already authenticated"
    return $session
}

if (-not $location) {
    throw "Expected redirect from GitLab but got status $($r1.StatusCode)"
}
Write-Verbose "Redirect 1: $location"

# --- 3. Follow redirects until we reach authn.web.gs.com ---
$maxRedirects = 10
for ($i = 0; $i -lt $maxRedirects; $i++) {
    $uri = [System.Uri]$location

    $params = @{
        Uri             = $location
        WebSession      = $session
        MaximumRedirection = 0
        UseBasicParsing = $true
        ErrorAction     = "SilentlyContinue"
        TimeoutSec      = 30
    }

    # Send Kerberos negotiate to the SSO endpoint (authn.web.gs.com or id.web.gs.com)
    if ($uri.Host -in "authn.web.gs.com", "id.web.gs.com") {
        $params["UseDefaultCredentials"] = $true
    }

    $r = Invoke-WebRequest @params

    if ($r.StatusCode -in 301,302,303,307,308) {
        $location = $r.Headers["Location"]
        # Handle relative redirects
        if ($location -and -not $location.StartsWith("http")) {
            $location = [System.Uri]::new($uri, $location).AbsoluteUri
        }
        Write-Verbose "Redirect $($i+2): $location"
        continue
    }

    # If we got a 200 with a SAML form, break out
    if ($r.StatusCode -eq 200 -and $r.Content -match "SAMLResponse") {
        Write-Verbose "Got SAML response form"
        $samlHtml = $r.Content
        break
    }

    throw "Unexpected status $($r.StatusCode) at $location"
}

if (-not $samlHtml) {
    throw "Failed to obtain SAML response after $maxRedirects redirects"
}

# --- 4. Parse SAMLResponse and RelayState ---
$samlMatch  = [regex]::Match($samlHtml, 'name="SAMLResponse"\s+value="([^"]+)"')
$relayMatch = [regex]::Match($samlHtml, 'name="RelayState"\s+value="([^"]+)"')

if (-not $samlMatch.Success) {
    throw "Could not parse SAMLResponse from IdP response"
}

$samlResponse = $samlMatch.Groups[1].Value
$relayState   = if ($relayMatch.Success) { $relayMatch.Groups[1].Value } else { "" }

# Also parse the form action URL (may not always be the default callback)
$actionMatch = [regex]::Match($samlHtml, '<form[^>]+action="([^"]+)"')
$callbackUrl = if ($actionMatch.Success) {
    $actionMatch.Groups[1].Value
} else {
    "$GitLabBase/users/auth/saml/callback"
}

# Decode HTML entities in the callback URL
$callbackUrl = [System.Net.WebUtility]::HtmlDecode($callbackUrl)

Write-Verbose "SAML callback: $callbackUrl"

# --- 5. POST SAML assertion to GitLab ---
$body = @{
    SAMLResponse = $samlResponse
    RelayState   = $relayState
}

$r3 = Invoke-WebRequest -Uri $callbackUrl -Method POST -Body $body `
        -WebSession $session -MaximumRedirection 5 -UseBasicParsing `
        -ErrorAction SilentlyContinue -TimeoutSec 30

Write-Verbose "SAML callback returned status $($r3.StatusCode)"

# Verify we got a session cookie
$cookie = $session.Cookies.GetCookies([System.Uri]$GitLabBase) |
            Where-Object { $_.Name -eq "_gitlab_session" }

if (-not $cookie) {
    throw "Authentication completed but no _gitlab_session cookie was set"
}

Write-Verbose "Authenticated. Session cookie obtained."
return $session
