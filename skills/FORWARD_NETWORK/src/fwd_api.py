"""
Forward Networks API client.

Reusable helper for calling the Forward Networks REST API from a Windows NDS
workstation. Handles authentication, TLS certificate bypass, and JSON
request/response.

Usage:
    # As a library:
    from fwd_api import fwd_api
    networks = fwd_api('GET', '/networks', instance='neteng')

    # Path search with params dict:
    result = fwd_api('GET', '/networks/104/paths', instance='neteng',
                     params={'srcIp': '10.1.1.1', 'dstIp': '10.2.2.2', 'ipProto': 6, 'dstPort': 443})

    # As a CLI:
    python fwd_api.py neteng GET /networks
    python fwd_api.py etp POST /nqe '{"query":"foreach d in network.devices select {Name: d.name}"}'
    python fwd_api.py neteng GET '/networks/104/paths?srcIp=10.1.1.1&dstIp=10.2.2.2&ipProto=6'
"""

import base64
import json
import os
import ssl
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

BASE_URLS = {
    'etp': 'https://fwd.app',
    'neteng': 'https://prod.ui.fwdnetcluster.url.gs.com',
}

TOKEN_FILES = {
    'etp': '.forward_network_etp_token',
    'neteng': '.forward_network_neteng_token',
}

# ETP instance is internet-facing (needs Zscaler proxy); Neteng is internal (direct)
ETP_PROXY_URL = 'http://production.zscaler.nimbus.gs.com:443'


def read_token(instance: str) -> tuple:
    """Return (access_key, secret_key) for a Forward Networks instance."""
    if instance not in TOKEN_FILES:
        raise ValueError(f'Unknown instance: {instance}. Valid: {list(TOKEN_FILES)}')

    token_path = Path(os.environ.get('USERPROFILE', Path.home())) / TOKEN_FILES[instance]
    if not token_path.exists():
        raise FileNotFoundError(
            f'Token file not found: {token_path}\n'
            f'Create an API token at the Forward Networks UI settings page '
            f'and save it to {token_path} (line 1 = access key, line 2 = secret key).'
        )

    lines = token_path.read_text(encoding='utf-8').strip().splitlines()
    if len(lines) < 2:
        raise ValueError(f'Token file {token_path} must have 2 lines: access_key and secret_key')
    return lines[0].strip(), lines[1].strip()


def fwd_api(method, path, instance='etp', body=None, params=None, timeout=30):
    """Call a Forward Networks API endpoint. Returns parsed JSON.

    Args:
        method: HTTP method (GET, POST, etc.)
        path: API path relative to /api (e.g. '/networks')
        instance: 'etp' or 'neteng'
        body: dict for JSON request body (POST)
        params: dict of query parameters (appended to URL)
        timeout: request timeout in seconds
    """
    access_key, secret_key = read_token(instance)

    url = f'{BASE_URLS[instance]}/api{path}'
    if params:
        url += ('&' if '?' in path else '?') + urllib.parse.urlencode(params)
    headers = {
        'Content-Type': 'application/json',
        'Authorization': 'Basic ' + base64.b64encode(
            f'{access_key}:{secret_key}'.encode()
        ).decode(),
    }

    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    ctx = ssl._create_unverified_context()

    if instance == 'etp':
        proxy_handler = urllib.request.ProxyHandler({'https': ETP_PROXY_URL})
        opener = urllib.request.build_opener(
            proxy_handler, urllib.request.HTTPSHandler(context=ctx)
        )
    else:
        # Neteng: direct access on internal GS network, no proxy
        opener = urllib.request.build_opener(urllib.request.HTTPSHandler(context=ctx))

    with opener.open(req, timeout=timeout) as resp:
        raw = resp.read().decode()
        if not raw:
            return None
        return json.loads(raw)


if __name__ == '__main__':
    # --args-file support: load JSON and rebuild argv as CLI positionals
    if "--args-file" in sys.argv:
        idx = sys.argv.index("--args-file")
        with open(sys.argv[idx + 1], "r", encoding="utf-8") as _f:
            _af = json.load(_f)
        _argv = [sys.argv[0]]
        for _pk in ("instance", "method", "path"):
            if _pk in _af:
                _argv.append(str(_af[_pk]))
        if "body" in _af and _af["body"] is not None:
            _argv.append(json.dumps(_af["body"]))
        sys.argv = _argv
        _out_file = _af.get("out_file")
    else:
        _out_file = None

    if len(sys.argv) < 4:
        print('Usage: python fwd_api.py <instance> <METHOD> <path> [json_body]')
        print('  instance: etp | neteng')
        print('  Example:  python fwd_api.py neteng GET /networks')
        sys.exit(1)

    instance = sys.argv[1]
    method = sys.argv[2]
    path = sys.argv[3]
    body = json.loads(sys.argv[4]) if len(sys.argv) > 4 else None

    result = fwd_api(method, path, instance=instance, body=body)
    output = json.dumps(result, indent=2)
    print(output)
    if _out_file:
        import os as _os
        _os.makedirs(_os.path.dirname(_os.path.abspath(_out_file)), exist_ok=True)
        with open(_out_file, "w", encoding="utf-8") as _f:
            _f.write(output)
