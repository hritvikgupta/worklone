"""Web Extract Tool with Hermes-style implementation embedded locally."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
from typing import Any, Dict, List, Optional

import httpx
from firecrawl import Firecrawl

from backend.core.tools.system_tools.base import BaseTool, ToolResult

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


def is_safe_url(_: str) -> bool:
    return True


def check_website_access(_: str):  # type: ignore[no-untyped-def]
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


# Parallel clients

_async_parallel_client = None


def _get_async_parallel_client():
    from parallel import AsyncParallel

    global _async_parallel_client
    if _async_parallel_client is None:
        api_key = os.getenv("PARALLEL_API_KEY")
        if not api_key:
            raise ValueError(
                "PARALLEL_API_KEY environment variable not set. "
                "Get your API key at https://parallel.ai"
            )
        _async_parallel_client = AsyncParallel(api_key=api_key)
    return _async_parallel_client


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


def _normalize_tavily_documents(response: dict, fallback_url: str = "") -> List[Dict[str, Any]]:
    documents: List[Dict[str, Any]] = []
    for result in response.get("results", []):
        url = result.get("url", fallback_url)
        raw = result.get("raw_content", "") or result.get("content", "")
        documents.append(
            {
                "url": url,
                "title": result.get("title", ""),
                "content": raw,
                "raw_content": raw,
                "metadata": {"sourceURL": url, "title": result.get("title", "")},
            }
        )
    for fail in response.get("failed_results", []):
        documents.append(
            {
                "url": fail.get("url", fallback_url),
                "title": "",
                "content": "",
                "raw_content": "",
                "error": fail.get("error", "extraction failed"),
                "metadata": {"sourceURL": fail.get("url", fallback_url)},
            }
        )
    for fail_url in response.get("failed_urls", []):
        url_str = fail_url if isinstance(fail_url, str) else str(fail_url)
        documents.append(
            {
                "url": url_str,
                "title": "",
                "content": "",
                "raw_content": "",
                "error": "extraction failed",
                "metadata": {"sourceURL": url_str},
            }
        )
    return documents


# Extract helpers

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


def _extract_scrape_payload(scrape_result: Any) -> Dict[str, Any]:
    result_plain = _to_plain_object(scrape_result)
    if not isinstance(result_plain, dict):
        return {}

    nested = result_plain.get("data")
    if isinstance(nested, dict):
        return nested

    return result_plain


def clean_base64_images(text: str) -> str:
    base64_with_parens_pattern = r"\(data:image/[^;]+;base64,[A-Za-z0-9+/=]+\)"
    base64_pattern = r"data:image/[^;]+;base64,[A-Za-z0-9+/=]+"
    cleaned_text = re.sub(base64_with_parens_pattern, "[BASE64_IMAGE_REMOVED]", text)
    cleaned_text = re.sub(base64_pattern, "[BASE64_IMAGE_REMOVED]", cleaned_text)
    return cleaned_text


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


def _exa_extract(urls: List[str]) -> List[Dict[str, Any]]:
    if is_interrupted():
        return [{"url": u, "error": "Interrupted", "title": ""} for u in urls]

    response = _get_exa_client().get_contents(urls, text=True)

    results = []
    for result in response.results or []:
        content = result.text or ""
        url = result.url or ""
        title = result.title or ""
        results.append(
            {
                "url": url,
                "title": title,
                "content": content,
                "raw_content": content,
                "metadata": {"sourceURL": url, "title": title},
            }
        )

    return results


async def _parallel_extract(urls: List[str]) -> List[Dict[str, Any]]:
    if is_interrupted():
        return [{"url": u, "error": "Interrupted", "title": ""} for u in urls]

    response = await _get_async_parallel_client().beta.extract(
        urls=urls,
        full_content=True,
    )

    results = []
    for result in response.results or []:
        content = result.full_content or ""
        if not content:
            content = "\n\n".join(result.excerpts or [])
        url = result.url or ""
        title = result.title or ""
        results.append(
            {
                "url": url,
                "title": title,
                "content": content,
                "raw_content": content,
                "metadata": {"sourceURL": url, "title": title},
            }
        )

    for error in response.errors or []:
        results.append(
            {
                "url": error.url or "",
                "title": "",
                "content": "",
                "error": error.content or error.error_type or "extraction failed",
                "metadata": {"sourceURL": error.url or ""},
            }
        )

    return results


async def web_extract_tool(
    urls: List[str],
    format: str = None,
    use_llm_processing: bool = True,
    model: Optional[str] = None,
    min_length: int = 5000,
) -> str:
    del use_llm_processing, model, min_length
    try:
        safe_urls = []
        ssrf_blocked: List[Dict[str, Any]] = []
        for url in urls:
            if not is_safe_url(url):
                ssrf_blocked.append(
                    {
                        "url": url,
                        "title": "",
                        "content": "",
                        "error": "Blocked: URL targets a private or internal network address",
                    }
                )
            else:
                safe_urls.append(url)

        if not safe_urls:
            results = []
        else:
            backend = _get_backend()

            if backend == "parallel":
                results = await _parallel_extract(safe_urls)
            elif backend == "exa":
                results = _exa_extract(safe_urls)
            elif backend == "tavily":
                raw = _tavily_request(
                    "extract",
                    {
                        "urls": safe_urls,
                        "include_images": False,
                    },
                )
                results = _normalize_tavily_documents(
                    raw, fallback_url=safe_urls[0] if safe_urls else ""
                )
            else:
                formats: List[str] = []
                if format == "markdown":
                    formats = ["markdown"]
                elif format == "html":
                    formats = ["html"]
                else:
                    formats = ["markdown", "html"]

                results = []
                for url in safe_urls:
                    if is_interrupted():
                        results.append({"url": url, "error": "Interrupted", "title": ""})
                        continue

                    blocked = check_website_access(url)
                    if blocked:
                        results.append(
                            {
                                "url": url,
                                "title": "",
                                "content": "",
                                "error": blocked["message"],
                                "blocked_by_policy": {
                                    "host": blocked["host"],
                                    "rule": blocked["rule"],
                                    "source": blocked["source"],
                                },
                            }
                        )
                        continue

                    try:
                        scrape_result = await asyncio.wait_for(
                            asyncio.to_thread(
                                _get_firecrawl_client().scrape,
                                url=url,
                                formats=formats,
                            ),
                            timeout=60,
                        )
                        scrape_payload = _extract_scrape_payload(scrape_result)
                        metadata = scrape_payload.get("metadata", {})
                        title = ""
                        content_markdown = scrape_payload.get("markdown")
                        content_html = scrape_payload.get("html")

                        if not isinstance(metadata, dict):
                            if hasattr(metadata, "model_dump"):
                                metadata = metadata.model_dump()
                            elif hasattr(metadata, "__dict__"):
                                metadata = metadata.__dict__
                            else:
                                metadata = {}

                        title = metadata.get("title", "")
                        final_url = metadata.get("sourceURL", url)
                        final_blocked = check_website_access(final_url)
                        if final_blocked:
                            results.append(
                                {
                                    "url": final_url,
                                    "title": title,
                                    "content": "",
                                    "raw_content": "",
                                    "error": final_blocked["message"],
                                    "blocked_by_policy": {
                                        "host": final_blocked["host"],
                                        "rule": final_blocked["rule"],
                                        "source": final_blocked["source"],
                                    },
                                }
                            )
                            continue

                        chosen_content = (
                            content_markdown
                            if (
                                format == "markdown"
                                or (format is None and content_markdown)
                            )
                            else content_html or content_markdown or ""
                        )

                        results.append(
                            {
                                "url": final_url,
                                "title": title,
                                "content": chosen_content,
                                "raw_content": chosen_content,
                                "metadata": metadata,
                            }
                        )
                    except Exception as scrape_err:
                        results.append(
                            {
                                "url": url,
                                "title": "",
                                "content": "",
                                "raw_content": "",
                                "error": str(scrape_err),
                            }
                        )

        if ssrf_blocked:
            results = ssrf_blocked + results

        trimmed_results = [
            {
                "url": r.get("url", ""),
                "title": r.get("title", ""),
                "content": r.get("content", ""),
                "error": r.get("error"),
                **(
                    {"blocked_by_policy": r["blocked_by_policy"]}
                    if "blocked_by_policy" in r
                    else {}
                ),
            }
            for r in results
        ]
        trimmed_response = {"results": trimmed_results}

        if trimmed_response.get("results") == []:
            result_json = tool_error("Content was inaccessible or not found")
            cleaned_result = clean_base64_images(result_json)
        else:
            result_json = json.dumps(trimmed_response, indent=2, ensure_ascii=False)
            cleaned_result = clean_base64_images(result_json)

        return cleaned_result

    except Exception as e:
        error_msg = f"Error extracting content: {str(e)}"
        logger.debug("%s", error_msg)
        return tool_error(error_msg)


def _normalize_urls(urls_raw: Any) -> List[str]:
    if isinstance(urls_raw, list):
        urls = [str(u).strip() for u in urls_raw if str(u).strip()]
    elif isinstance(urls_raw, str):
        urls = [u.strip() for u in urls_raw.split(",") if u.strip()]
    else:
        urls = []

    seen = set()
    out = []
    for u in urls:
        if u in seen:
            continue
        seen.add(u)
        out.append(u)
    return out[:5]


class WebExtractTool(BaseTool):
    name = "web_extract"
    description = "Extract content from web page URLs (Hermes implementation: exa/parallel/tavily/firecrawl)."
    category = "core"

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "urls": {
                    "oneOf": [
                        {"type": "array", "items": {"type": "string"}},
                        {"type": "string"},
                    ],
                    "description": "List of URLs to extract content from (max 5)",
                },
                "format": {
                    "type": "string",
                    "enum": ["markdown", "html"],
                    "description": "Preferred output format (default markdown)",
                },
            },
            "required": ["urls"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        del context
        urls = _normalize_urls(parameters.get("urls"))
        if not urls:
            return ToolResult(False, "", error="urls is required")

        fmt = (parameters.get("format") or "markdown").strip().lower()
        if fmt not in {"markdown", "html"}:
            fmt = "markdown"

        raw = await web_extract_tool(urls=urls, format=fmt)
        data: Any = json.loads(raw)
        success = isinstance(data, dict) and (
            bool(data.get("success", True))
            if "success" in data
            else isinstance(data.get("results"), list)
        )
        return ToolResult(
            success=success,
            output=raw,
            error=data.get("error", "") if isinstance(data, dict) and not success else "",
            data=data,
        )
