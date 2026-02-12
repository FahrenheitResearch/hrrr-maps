"""
Shared HTTP helpers for wxsection MCP servers (stdio and SSE).

Both mcp_server.py (local stdio) and mcp_public.py (public SSE) import
_api_get, _ext_fetch_json, _ext_fetch_text from here.
"""

import json
import os
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError
from urllib.parse import urlencode

API_BASE = os.environ.get("WXSECTION_API_BASE", "http://127.0.0.1:5565")
USER_AGENT = "wxsection-mcp/1.0"


def _api_get(path: str, params: dict = None, raw: bool = False,
             api_base: str = None) -> dict | bytes:
    """GET from the dashboard HTTP API. Returns parsed JSON or raw bytes."""
    base = api_base or API_BASE
    url = f"{base}{path}"
    if params:
        params = {k: v for k, v in params.items() if v is not None}
        if params:
            url += "?" + urlencode(params)
    try:
        req = Request(url, headers={"User-Agent": USER_AGENT})
        with urlopen(req, timeout=120) as resp:
            data = resp.read()
            if raw:
                return data
            return json.loads(data)
    except HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        try:
            return json.loads(body)
        except json.JSONDecodeError:
            return {"error": f"HTTP {e.code}: {body[:500]}"}
    except URLError as e:
        return {"error": f"Cannot reach API at {base}: {e.reason}. Is the dashboard running?"}
    except Exception as e:
        return {"error": str(e)}


def _ext_fetch_json(url: str, timeout: int = 30, headers: dict = None) -> dict:
    """Fetch JSON from an external URL."""
    hdrs = {"User-Agent": USER_AGENT}
    if headers:
        hdrs.update(headers)
    req = Request(url, headers=hdrs)
    try:
        with urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read())
    except Exception as e:
        return {"error": str(e)}


def _ext_fetch_text(url: str, timeout: int = 30) -> str:
    """Fetch text from an external URL."""
    req = Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urlopen(req, timeout=timeout) as resp:
            return resp.read().decode("utf-8", errors="replace")
    except Exception as e:
        return f"Error: {e}"
