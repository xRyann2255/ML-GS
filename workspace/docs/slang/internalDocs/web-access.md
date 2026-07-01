# Accessing Internal Web Pages

Most internal GS web pages support Kerberos auth. Use PowerShell's `Invoke-WebRequest` with `-UseDefaultCredentials -UseBasicParsing`:

```powershell
Invoke-WebRequest -Uri "<URL>" -UseDefaultCredentials -UseBasicParsing
```

For sites that use SAML/OIDC (like Confluence), see `searching-internal-docs.md` in this folder.
