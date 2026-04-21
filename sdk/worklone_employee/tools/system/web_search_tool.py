"""Web Search Tool with Hermes-style implementation embedded locally."""

from __future__ import annotations

import json
import logging
import os
import shutil
import subprocess
from html import unescape
from typing import Any, Dict, List, Optional
from urllib.parse import parse_qs, quote_plus, urlparse, unquote

import httpx
from firecrawl import Firecrawl

from worklone_employee.tools.base import BaseTool, ToolResult

logger = logging.getLogger(__name__)


def tool_error(message: str, success: bool = False) -> str:
    return json.dumps({"success": success, "error": message}, ensure_ascii=False)


# Hermes compatibility shims (Hermes-only modules are not in this repo).
def _is_tool_gateway_ready() -> bool:
    return False


def prefers_gateway(_: str) -> bool:
    return False


def _read_nous_access_token() -> Optional[str]:
    return None


def resolve_managed_tool_gateway(_: str, token_reader=None):  # type: ignore[no-untyped-def]
    del token_reader
    return None


def is_interrupted() -> bool:
    return False


# Backend selection

def _has_env(name: str) -> bool:
    val = os.getenv(name)
    return bool(val and val.strip())


def _load_web_config() -> dict:
    try:
        from hermes_cli.config import load_config

        return load_config().get("web", {})
    except (ImportError, Exception):
        return {}


def _get_backend() -> str:
    env_backend = (os.getenv("WEB_BACKEND") or "").lower().strip()
    if env_backend in ("parallel", "firecrawl", "tavily", "exa"):
        return env_backend

    configured = (_load_web_config().get("backend") or "").lower().strip()
    if configured in ("parallel", "firecrawl", "tavily", "exa"):
        return configured

    backend_candidates = (
        (
            "firecrawl",
            _has_env("FIRECRAWL_API_KEY")
            or _has_env("FIRECRAWL_API_URL")
            or _is_tool_gateway_ready(),
        ),
        ("parallel", _has_env("PARALLEL_API_KEY")),
        ("tavily", _has_env("TAVILY_API_KEY")),
        ("exa", _has_env("EXA_API_KEY")),
    )
    for backend, available in backend_candidates:
        if available:
            return backend

    return "firecrawl"


# Firecrawl client

_firecrawl_client = None
_firecrawl_client_config = None


def _get_direct_firecrawl_config() -> Optional[tuple[Dict[str, str], tuple[str, Optional[str], Optional[str]]]]:
    api_key = os.getenv("FIRECRAWL_API_KEY", "").strip()
    api_url = os.getenv("FIRECRAWL_API_URL", "").strip().rstrip("/")

    if not api_key and not api_url:
        return None

    kwargs: Dict[str, str] = {}
    if api_key:
        kwargs["api_key"] = api_key
    if api_url:
        kwargs["api_url"] = api_url

    return kwargs, ("direct", api_url or None, api_key or None)


def _raise_web_backend_configuration_error() -> None:
    raise ValueError(
        "Web tools are not configured. "
        "Set FIRECRAWL_API_KEY for cloud Firecrawl or set FIRECRAWL_API_URL for a self-hosted Firecrawl instance."
    )


def _get_firecrawl_client():
    global _firecrawl_client, _firecrawl_client_config

    direct_config = _get_direct_firecrawl_config()
    if direct_config is not None and not prefers_gateway("web"):
        kwargs, client_config = direct_config
    else:
        managed_gateway = resolve_managed_tool_gateway(
            "firecrawl",
            token_reader=_read_nous_access_token,
        )
        if managed_gateway is None:
            logger.error(
                "Firecrawl client initialization failed: missing direct config and tool-gateway auth."
            )
            _raise_web_backend_configuration_error()

        kwargs = {
            "api_key": managed_gateway.nous_user_token,
            "api_url": managed_gateway.gateway_origin,
        }
        client_config = (
            "tool-gateway",
            kwargs["api_url"],
            managed_gateway.nous_user_token,
        )

    if _firecrawl_client is not None and _firecrawl_client_config == client_config:
        return _firecrawl_client

    _firecrawl_client = Firecrawl(**kwargs)
    _firecrawl_client_config = client_config
    return _firecrawl_client


# Parallel client

_parallel_client = None


def _get_parallel_client():
    from parallel import Parallel

    global _parallel_client
    if _parallel_client is None:
        api_key = os.getenv("PARALLEL_API_KEY")
        if not api_key:
            raise ValueError(
                "PARALLEL_API_KEY environment variable not set. "
                "Get your API key at https://parallel.ai"
            )
        _parallel_client = Parallel(api_key=api_key)
    return _parallel_client


# Tavily helpers

_TAVILY_BASE_URL = "https://api.tavily.com"


def _tavily_request(endpoint: str, payload: dict) -> dict:
    api_key = os.getenv("TAVILY_API_KEY")
    if not api_key:
        raise ValueError(
            "TAVILY_API_KEY environment variable not set. "
            "Get your API key at https://app.tavily.com/home"
        )
    payload["api_key"] = api_key
    url = f"{_TAVILY_BASE_URL}/{endpoint.lstrip('/')}"
    response = httpx.post(url, json=payload, timeout=60)
    response.raise_for_status()
    return response.json()


def _normalize_tavily_search_results(response: dict) -> dict:
    web_results = []
    for i, result in enumerate(response.get("results", [])):
        web_results.append(
            {
                "title": result.get("title", ""),
                "url": result.get("url", ""),
                "description": result.get("content", ""),
                "position": i + 1,
            }
        )
    return {"success": True, "data": {"web": web_results}}


# Search response normalization helpers

def _to_plain_object(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, (dict, list, str, int, float, bool)):
        return value
    if hasattr(value, "model_dump"):
        try:
            return value.model_dump()
        except Exception:
            pass
    if hasattr(value, "__dict__"):
        try:
            return {k: v for k, v in value.__dict__.items() if not k.startswith("_")}
        except Exception:
            pass
    return value


def _normalize_result_list(values: Any) -> List[Dict[str, Any]]:
    if not isinstance(values, list):
        return []
    normalized: List[Dict[str, Any]] = []
    for item in values:
        plain = _to_plain_object(item)
        if isinstance(plain, dict):
            normalized.append(plain)
    return normalized


def _extract_web_search_results(response: Any) -> List[Dict[str, Any]]:
    response_plain = _to_plain_object(response)

    if isinstance(response_plain, dict):
        data = response_plain.get("data")
        if isinstance(data, list):
            return _normalize_result_list(data)

        if isinstance(data, dict):
            data_web = _normalize_result_list(data.get("web"))
            if data_web:
                return data_web
            data_results = _normalize_result_list(data.get("results"))
            if data_results:
                return data_results

        top_web = _normalize_result_list(response_plain.get("web"))
        if top_web:
            return top_web

        top_results = _normalize_result_list(response_plain.get("results"))
        if top_results:
            return top_results

    if hasattr(response, "web"):
        return _normalize_result_list(getattr(response, "web", []))

    return []


# Exa + Parallel search implementations

def _get_exa_client():
    from exa_py import Exa

    api_key = os.getenv("EXA_API_KEY")
    if not api_key:
        raise ValueError(
            "EXA_API_KEY environment variable not set. "
            "Get your API key at https://exa.ai"
        )
    exa = Exa(api_key=api_key)
    exa.headers["x-exa-integration"] = "hermes-agent"
    return exa


def _exa_search(query: str, limit: int = 10) -> dict:
    if is_interrupted():
        return {"error": "Interrupted", "success": False}

    response = _get_exa_client().search(
        query,
        num_results=limit,
        contents={"highlights": True},
    )

    web_results = []
    for i, result in enumerate(response.results or []):
        highlights = result.highlights or []
        web_results.append(
            {
                "url": result.url or "",
                "title": result.title or "",
                "description": " ".join(highlights) if highlights else "",
                "position": i + 1,
            }
        )

    return {"success": True, "data": {"web": web_results}}


def _parallel_search(query: str, limit: int = 5) -> dict:
    if is_interrupted():
        return {"error": "Interrupted", "success": False}

    mode = os.getenv("PARALLEL_SEARCH_MODE", "agentic").lower().strip()
    if mode not in ("fast", "one-shot", "agentic"):
        mode = "agentic"

    response = _get_parallel_client().beta.search(
        search_queries=[query],
        objective=query,
        mode=mode,
        max_results=min(limit, 20),
    )

    web_results = []
    for i, result in enumerate(response.results or []):
        excerpts = result.excerpts or []
        web_results.append(
            {
                "url": result.url or "",
                "title": result.title or "",
                "description": " ".join(excerpts) if excerpts else "",
                "position": i + 1,
            }
        )

    return {"success": True, "data": {"web": web_results}}


def _normalize_duckduckgo_url(url: str) -> str:
    """Unwrap DuckDuckGo redirect links into destination URLs."""
    if not url:
        return ""
    parsed = urlparse(url)
    if "duckduckgo.com" in (parsed.netloc or "") and parsed.path.startswith("/l/"):
        qs = parse_qs(parsed.query)
        uddg = qs.get("uddg", [])
        if uddg:
            return unquote(uddg[0])
    return url


def _duckduckgo_search_via_python(query: str, limit: int) -> Optional[dict]:
    """Try DDGS python package fallback if available."""
    try:
        from ddgs import DDGS  # type: ignore
    except Exception:
        return None

    try:
        with DDGS() as ddgs:
            rows = list(ddgs.text(query, max_results=limit))
        web_results = []
        for i, row in enumerate(rows, start=1):
            web_results.append(
                {
                    "title": row.get("title", "") if isinstance(row, dict) else "",
                    "url": _normalize_duckduckgo_url(row.get("href", "") if isinstance(row, dict) else ""),
                    "description": row.get("body", "") if isinstance(row, dict) else "",
                    "position": i,
                }
            )
        return {"success": True, "data": {"web": web_results}}
    except Exception:
        return None


def _duckduckgo_search_via_cli(query: str, limit: int) -> Optional[dict]:
    """Try DDGS CLI fallback if available."""
    ddgs_bin = shutil.which("ddgs")
    if not ddgs_bin:
        return None

    try:
        cmd = [ddgs_bin, "text", "-k", query, "-m", str(limit), "-o", "json"]
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if proc.returncode != 0:
            return None

        payload = json.loads(proc.stdout.strip() or "[]")
        if not isinstance(payload, list):
            return None

        web_results = []
        for i, row in enumerate(payload, start=1):
            if not isinstance(row, dict):
                continue
            web_results.append(
                {
                    "title": row.get("title", ""),
                    "url": _normalize_duckduckgo_url(row.get("href", "")),
                    "description": row.get("body", ""),
                    "position": i,
                }
            )
        return {"success": True, "data": {"web": web_results}}
    except Exception:
        return None


def _extract_snippets(html_text: str) -> List[str]:
    snippets = []
    marker = 'class="result__snippet"'
    idx = 0
    while len(snippets) < 50:
        i = html_text.find(marker, idx)
        if i == -1:
            break
        gt = html_text.find(">", i)
        if gt == -1:
            break
        end = html_text.find("</a>", gt)
        if end == -1:
            end = html_text.find("</div>", gt)
        if end == -1:
            break
        raw = html_text[gt + 1 : end]
        cleaned = unescape(
            raw.replace("<b>", "").replace("</b>", "").replace("\n", " ").strip()
        )
        snippets.append(cleaned)
        idx = end + 4
    return snippets


def _duckduckgo_search_via_http(query: str, limit: int) -> dict:
    """Fallback with no key/package: scrape DuckDuckGo HTML results."""
    url = "https://html.duckduckgo.com/html/"
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0 Safari/537.36"
        )
    }
    response = httpx.post(
        url,
        data={"q": query},
        headers=headers,
        timeout=30,
        follow_redirects=True,
    )
    response.raise_for_status()
    html_text = response.text

    # Extract links/titles from result anchors.
    links: List[Dict[str, str]] = []
    marker = 'class="result__a"'
    idx = 0
    while len(links) < max(1, min(20, limit)):
        i = html_text.find(marker, idx)
        if i == -1:
            break
        href_pos = html_text.rfind('href="', 0, i)
        if href_pos == -1:
            idx = i + len(marker)
            continue
        href_start = href_pos + len('href="')
        href_end = html_text.find('"', href_start)
        if href_end == -1:
            break
        href = html_text[href_start:href_end]

        text_start = html_text.find(">", i)
        if text_start == -1:
            break
        text_end = html_text.find("</a>", text_start)
        if text_end == -1:
            break
        title = unescape(
            html_text[text_start + 1 : text_end]
            .replace("<b>", "")
            .replace("</b>", "")
            .strip()
        )
        links.append({"title": title, "url": _normalize_duckduckgo_url(href)})
        idx = text_end + 4

    snippets = _extract_snippets(html_text)
    web_results = []
    for i, row in enumerate(links, start=1):
        web_results.append(
            {
                "title": row.get("title", ""),
                "url": row.get("url", ""),
                "description": snippets[i - 1] if i - 1 < len(snippets) else "",
                "position": i,
            }
        )

    return {"success": True, "data": {"web": web_results}}


def _duckduckgo_fallback_search(query: str, limit: int) -> dict:
    """No-key fallback path using DuckDuckGo."""
    py_res = _duckduckgo_search_via_python(query, limit)
    if py_res is not None:
        return py_res
    cli_res = _duckduckgo_search_via_cli(query, limit)
    if cli_res is not None:
        return cli_res
    return _duckduckgo_search_via_http(query, limit)


# Main search tool function

def web_search_tool(query: str, limit: int = 5) -> str:
    try:
        if is_interrupted():
            return tool_error("Interrupted", success=False)

        backend = _get_backend()
        if backend == "parallel":
            response_data = _parallel_search(query, limit)
            return json.dumps(response_data, indent=2, ensure_ascii=False)

        if backend == "exa":
            response_data = _exa_search(query, limit)
            return json.dumps(response_data, indent=2, ensure_ascii=False)

        if backend == "tavily":
            raw = _tavily_request(
                "search",
                {
                    "query": query,
                    "max_results": min(limit, 20),
                    "include_raw_content": False,
                    "include_images": False,
                },
            )
            response_data = _normalize_tavily_search_results(raw)
            return json.dumps(response_data, indent=2, ensure_ascii=False)

        response = _get_firecrawl_client().search(query=query, limit=limit)
        web_results = _extract_web_search_results(response)

        response_data = {
            "success": True,
            "data": {
                "web": web_results,
            },
        }
        return json.dumps(response_data, indent=2, ensure_ascii=False)

    except Exception as e:
        logger.warning("Primary web backend failed; trying DuckDuckGo fallback: %s", str(e))
        try:
            fallback = _duckduckgo_fallback_search(query, max(1, min(20, limit)))
            return json.dumps(fallback, indent=2, ensure_ascii=False)
        except Exception as fallback_err:
            error_msg = f"Error searching web: {str(fallback_err)}"
            logger.debug("%s", error_msg)
            return tool_error(error_msg)


class WebSearchTool(BaseTool):
    name = "web_search"
    description = "Search the web for information (Hermes implementation: exa/parallel/tavily/firecrawl)."
    category = "core"

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The search query to look up on the web",
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of results (default 5)",
                },
            },
            "required": ["query"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        del context
        query = (parameters.get("query") or "").strip()
        if not query:
            return ToolResult(False, "", error="query is required")

        try:
            limit = int(parameters.get("limit", 5))
        except Exception:
            limit = 5

        raw = web_search_tool(query=query, limit=limit)
        data: Any = json.loads(raw)
        success = bool(data.get("success", True)) if isinstance(data, dict) else True
        return ToolResult(
            success=success,
            output=raw,
            error=(data.get("error", "") if isinstance(data, dict) and not success else ""),
            data=data,
        )
