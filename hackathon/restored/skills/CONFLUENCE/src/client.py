"""
ConfluenceClient — standalone REST client for Confluence Server / Cloud.

Usage:
    from tools.confluence import ConfluenceClient

    client = ConfluenceClient(url="https://confluence.example.com", pat="token")
    page = client.get_page_by_id("12345678")
    results = client.search('type=page AND space=SLT AND text~"runbook"')

Or load config from .env automatically:
    client = ConfluenceClient.from_env()
"""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Optional

import requests
import urllib3

# Suppress InsecureRequestWarning if SSL verification is disabled via env override
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logger = logging.getLogger(__name__)


def _load_dotenv_manual(path: str) -> None:
    """Minimal .env loader — fallback when python-dotenv is not installed."""
    import os

    try:
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" not in line:
                    continue
                key, _, value = line.partition("=")
                key = key.strip()
                value = value.strip()
                # Don't override existing env vars
                if key and key not in os.environ:
                    os.environ[key] = value
    except FileNotFoundError:
        logger.warning("dotenv file not found: %s", path)


class ConfluenceClient:
    """Client for the Confluence REST API (v1)."""

    DEFAULT_EXPAND = "body.storage,version,space,ancestors"

    def __init__(
        self,
        url: str,
        pat: str,
        *,
        verify_ssl: bool = True,
        timeout: int = 30,
        max_retries: int = 3,
        backoff_factor: float = 1.0,
    ):
        self.url = url.rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor

        self.session = requests.Session()
        self.session.headers.update(
            {
                "Authorization": f"Bearer {pat}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            }
        )
        self.session.verify = verify_ssl

    # ------------------------------------------------------------------ #
    #  Factory                                                             #
    # ------------------------------------------------------------------ #

    @classmethod
    def from_env(cls, dotenv_path: str | None = None) -> "ConfluenceClient":
        """Create a client from environment / .env variables.

        Reads:
            CONFLUENCE_URL  — base URL (required)
            CONFLUENCE_PAT  — personal access token (required)
            CONFLUENCE_VERIFY_SSL — "true" / "false" (default: true)

        The default .env path resolves relative to this source file:
        ``src/ → CONFLUENCE/ → skills/ → repo-root/ → workspace/config/.env``.
        """
        import os
        from pathlib import Path

        if dotenv_path is None:
            # Resolve relative to this file: src/ -> CONFLUENCE/ -> skills/ -> repo-root/
            dotenv_path = str(
                Path(__file__).resolve().parents[3] / "workspace" / "config" / ".env"
            )

        try:
            from dotenv import load_dotenv

            load_dotenv(dotenv_path)
        except ImportError:
            _load_dotenv_manual(dotenv_path)

        url = os.environ.get("CONFLUENCE_URL")
        pat = os.environ.get("CONFLUENCE_PAT")
        if not url or not pat:
            raise ValueError(
                "CONFLUENCE_URL and CONFLUENCE_PAT must be set in env or .env"
            )
        verify = os.environ.get("CONFLUENCE_VERIFY_SSL", "true").lower() == "true"
        return cls(url=url, pat=pat, verify_ssl=verify)

    # ------------------------------------------------------------------ #
    #  Low-level request with retry / backoff                              #
    # ------------------------------------------------------------------ #

    def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict | None = None,
        json_body: Any = None,
        files: Any = None,
        extra_headers: dict | None = None,
    ) -> requests.Response:
        """Issue an HTTP request with retry + exponential backoff on 429/5xx."""
        url = f"{self.url}{path}"
        for attempt in range(1, self.max_retries + 1):
            try:
                resp = self.session.request(
                    method,
                    url,
                    params=params,
                    json=json_body,
                    files=files,
                    headers=extra_headers,
                    timeout=self.timeout,
                )
                if resp.status_code == 429 or resp.status_code >= 500:
                    if attempt < self.max_retries:
                        wait = self.backoff_factor * (2 ** (attempt - 1))
                        logger.warning(
                            "Confluence %s %s returned %s — retrying in %.1fs",
                            method,
                            path,
                            resp.status_code,
                            wait,
                        )
                        time.sleep(wait)
                        continue
                resp.raise_for_status()
                return resp
            except requests.ConnectionError as exc:
                if attempt < self.max_retries:
                    wait = self.backoff_factor * (2 ** (attempt - 1))
                    logger.warning("Connection error — retrying in %.1fs: %s", wait, exc)
                    time.sleep(wait)
                else:
                    raise
        # unreachable, but keeps mypy happy
        raise RuntimeError("Exhausted retries")

    # ------------------------------------------------------------------ #
    #  Health                                                              #
    # ------------------------------------------------------------------ #

    def is_connected(self) -> bool:
        """Return True if the Confluence instance is reachable and auth works."""
        try:
            resp = self.session.get(
                f"{self.url}/rest/api/space",
                params={"limit": 1},
                timeout=self.timeout,
            )
            return resp.status_code == 200
        except Exception:
            return False

    # ================================================================== #
    #  READ OPERATIONS                                                     #
    # ================================================================== #

    def get_page_content(self, page_id: str) -> str:
        """Return just the body HTML for a page — no wrapper dict."""
        resp = self._request(
            "GET",
            f"/rest/api/content/{page_id}",
            params={"expand": "body.storage"},
        )
        return resp.json().get("body", {}).get("storage", {}).get("value", "")

    def get_page_by_id(
        self, page_id: str, *, expand: str | None = None
    ) -> Dict[str, Any]:
        """Fetch a page by its numeric ID."""
        resp = self._request(
            "GET",
            f"/rest/api/content/{page_id}",
            params={"expand": expand or self.DEFAULT_EXPAND},
        )
        return self._format_page(resp.json())

    def get_page_by_title(
        self, space_key: str, title: str, *, expand: str | None = None
    ) -> Dict[str, Any]:
        """Fetch a page by space key + exact title."""
        resp = self._request(
            "GET",
            "/rest/api/content",
            params={
                "spaceKey": space_key,
                "title": title,
                "expand": expand or self.DEFAULT_EXPAND,
            },
        )
        results = resp.json().get("results", [])
        if not results:
            return {
                "success": False,
                "error": f"Page '{title}' not found in space '{space_key}'",
            }
        return self._format_page(results[0])

    def search(
        self,
        cql: str,
        *,
        max_results: int = 25,
        expand: str = "space,version",
    ) -> Dict[str, Any]:
        """Run a CQL search and return matching pages."""
        resp = self._request(
            "GET",
            "/rest/api/content/search",
            params={"cql": cql, "limit": max_results, "expand": expand},
        )
        data = resp.json()
        pages = [self._format_search_hit(r) for r in data.get("results", [])]
        return {"success": True, "count": len(pages), "pages": pages}

    def search_all(
        self,
        cql: str,
        *,
        batch_size: int = 25,
        expand: str = "space,version",
    ) -> List[Dict[str, Any]]:
        """Paginate through *all* CQL results."""
        all_pages: list[dict] = []
        start = 0
        while True:
            resp = self._request(
                "GET",
                "/rest/api/content/search",
                params={
                    "cql": cql,
                    "limit": batch_size,
                    "start": start,
                    "expand": expand,
                },
            )
            results = resp.json().get("results", [])
            if not results:
                break
            all_pages.extend(self._format_search_hit(r) for r in results)
            start += len(results)
            if len(results) < batch_size:
                break
        return all_pages

    def get_child_pages(
        self, page_id: str, *, max_results: int = 50
    ) -> Dict[str, Any]:
        """Return immediate children of a page."""
        resp = self._request(
            "GET",
            f"/rest/api/content/{page_id}/child/page",
            params={"limit": max_results, "expand": "version,space"},
        )
        children = [
            {"id": r["id"], "title": r["title"]}
            for r in resp.json().get("results", [])
        ]
        return {"success": True, "count": len(children), "children": children}

    def get_page_tree(
        self, page_id: str, *, depth: int = 3
    ) -> Dict[str, Any]:
        """Recursively build the page tree under *page_id*."""
        resp = self._request(
            "GET",
            f"/rest/api/content/{page_id}",
            params={"expand": "version,space"},
        )
        page = resp.json()
        node: Dict[str, Any] = {
            "id": page["id"],
            "title": page["title"],
            "children": [],
        }
        if depth > 0:
            child_resp = self._request(
                "GET",
                f"/rest/api/content/{page_id}/child/page",
                params={"limit": 100},
            )
            for child in child_resp.json().get("results", []):
                node["children"].append(
                    self.get_page_tree(child["id"], depth=depth - 1)
                )
        return node

    def get_space_info(self, space_key: str) -> Dict[str, Any]:
        """Get metadata for a Confluence space."""
        resp = self._request(
            "GET",
            f"/rest/api/space/{space_key}",
            params={"expand": "description.plain,homepage"},
        )
        data = resp.json()
        return {
            "success": True,
            "key": data["key"],
            "name": data["name"],
            "description": data.get("description", {})
            .get("plain", {})
            .get("value", ""),
            "homepage_id": data.get("homepage", {}).get("id", ""),
        }

    def get_page_labels(self, page_id: str) -> List[str]:
        """Return label names for a page."""
        resp = self._request("GET", f"/rest/api/content/{page_id}/label")
        return [lbl["name"] for lbl in resp.json().get("results", [])]

    def get_page_comments(
        self, page_id: str, *, expand: str = "body.storage,version"
    ) -> List[Dict[str, Any]]:
        """Return comments on a page."""
        resp = self._request(
            "GET",
            f"/rest/api/content/{page_id}/child/comment",
            params={"expand": expand},
        )
        return [
            {
                "id": c["id"],
                "body": c.get("body", {}).get("storage", {}).get("value", ""),
            }
            for c in resp.json().get("results", [])
        ]

    def list_attachments(
        self, page_id: str, *, max_results: int = 100
    ) -> List[Dict[str, Any]]:
        """Return attachments on a page."""
        resp = self._request(
            "GET",
            f"/rest/api/content/{page_id}/child/attachment",
            params={"limit": max_results},
        )
        return [
            {
                "title": a["title"],
                "download_url": f"{self.url}{a['_links']['download']}",
            }
            for a in resp.json().get("results", [])
        ]

    def download_attachment(self, download_url: str, dest_path: str) -> str:
        """Download an attachment to *dest_path*. Returns the path."""
        resp = self.session.get(download_url, timeout=self.timeout)
        resp.raise_for_status()
        with open(dest_path, "wb") as fh:
            fh.write(resp.content)
        return dest_path

    # ================================================================== #
    #  WRITE OPERATIONS                                                    #
    # ================================================================== #

    def create_page(
        self,
        space_key: str,
        title: str,
        body: str,
        *,
        parent_id: str | None = None,
    ) -> Dict[str, Any]:
        """Create a new page in Confluence storage format."""
        payload: Dict[str, Any] = {
            "type": "page",
            "title": title,
            "space": {"key": space_key},
            "body": {"storage": {"value": body, "representation": "storage"}},
        }
        if parent_id:
            payload["ancestors"] = [{"id": parent_id}]

        resp = self._request("POST", "/rest/api/content", json_body=payload)
        page = resp.json()
        return {
            "success": True,
            "page_id": page["id"],
            "url": f"{self.url}{page['_links']['webui']}",
        }

    def update_page(
        self,
        page_id: str,
        title: str,
        body: str,
        *,
        version: int | None = None,
    ) -> Dict[str, Any]:
        """Update an existing page. Fetches current version automatically if omitted."""
        if version is None:
            cur = self._request(
                "GET",
                f"/rest/api/content/{page_id}",
                params={"expand": "version"},
            )
            version = cur.json()["version"]["number"]

        payload = {
            "type": "page",
            "title": title,
            "body": {"storage": {"value": body, "representation": "storage"}},
            "version": {"number": version + 1},
        }
        self._request("PUT", f"/rest/api/content/{page_id}", json_body=payload)
        return {"success": True, "page_id": page_id, "new_version": version + 1}

    def append_to_page(self, page_id: str, content: str) -> Dict[str, Any]:
        """Append HTML content to the end of an existing page."""
        resp = self._request(
            "GET",
            f"/rest/api/content/{page_id}",
            params={"expand": "body.storage,version"},
        )
        page = resp.json()
        current_body = page["body"]["storage"]["value"]
        current_version = page["version"]["number"]

        return self.update_page(
            page_id,
            page["title"],
            current_body + content,
            version=current_version,
        )

    def add_comment(self, page_id: str, body: str) -> Dict[str, Any]:
        """Add a comment to a page."""
        payload = {
            "type": "comment",
            "container": {"id": page_id, "type": "page"},
            "body": {"storage": {"value": body, "representation": "storage"}},
        }
        resp = self._request("POST", "/rest/api/content", json_body=payload)
        return {"success": True, "comment_id": resp.json()["id"]}

    def add_labels(self, page_id: str, labels: List[str]) -> Dict[str, Any]:
        """Add one or more labels to a page."""
        payload = [{"name": lbl} for lbl in labels]
        self._request(
            "POST", f"/rest/api/content/{page_id}/label", json_body=payload
        )
        return {"success": True, "labels_added": labels}

    def remove_label(self, page_id: str, label_name: str) -> Dict[str, Any]:
        """Remove a label from a page."""
        self._request(
            "DELETE", f"/rest/api/content/{page_id}/label/{label_name}"
        )
        return {"success": True, "label_removed": label_name}

    def upload_attachment(
        self, page_id: str, file_path: str, content_type: str = "application/octet-stream"
    ) -> Dict[str, Any]:
        """Upload a file as an attachment to a page."""
        import os

        filename = os.path.basename(file_path)
        with open(file_path, "rb") as fh:
            resp = self._request(
                "POST",
                f"/rest/api/content/{page_id}/child/attachment",
                files={"file": (filename, fh, content_type)},
                extra_headers={"X-Atlassian-Token": "nocheck"},
            )
        att = resp.json().get("results", [{}])[0]
        return {"success": True, "attachment_id": att.get("id", ""), "title": filename}

    # ================================================================== #
    #  EXPORT                                                              #
    # ================================================================== #

    @staticmethod
    def export_pages(pages: list, output_path: str) -> str:
        """Dump a list of page dicts to JSON."""
        import json

        with open(output_path, "w", encoding="utf-8") as fh:
            json.dump(pages, fh, indent=2, ensure_ascii=False, default=str)
        return output_path

    # ================================================================== #
    #  Internal helpers                                                    #
    # ================================================================== #

    def _format_page(self, data: dict) -> Dict[str, Any]:
        """Content-first format: body/title/id at top level.

        Metadata (version, author, timestamps) is saved in ``_meta`` for
        staleness tracking and update operations but is NOT surfaced to the
        user unless explicitly requested.  Pages are mutable — always
        capture the version so we know what snapshot we analysed.
        """
        version_block = data.get("version", {})
        return {
            "success": True,
            # ---- content (what matters) ----
            "id": data["id"],
            "title": data["title"],
            "body": data.get("body", {}).get("storage", {}).get("value", ""),
            "url": f"{self.url}{data.get('_links', {}).get('webui', '')}",
            "ancestors": [
                {"id": a["id"], "title": a["title"]}
                for a in data.get("ancestors", [])
            ],
            # ---- metadata (only when asked) ----
            "_meta": {
                "space": data.get("space", {}).get("key", ""),
                "version": version_block.get("number", 0),
                "last_updated": version_block.get("when", ""),
                "last_updated_by": version_block.get("by", {}).get("displayName", ""),
            },
        }

    def _format_search_hit(self, data: dict) -> Dict[str, Any]:
        """Search-result format — content-first, metadata in _meta."""
        version_block = data.get("version", {})
        return {
            # ---- content ----
            "id": data["id"],
            "title": data["title"],
            "url": f"{self.url}{data.get('_links', {}).get('webui', '')}",
            # ---- metadata ----
            "_meta": {
                "space": data.get("space", {}).get("key", ""),
                "version": version_block.get("number", 0),
                "last_updated": version_block.get("when", ""),
            },
        }
