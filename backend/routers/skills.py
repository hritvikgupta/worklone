"""
Skills Router - Proxies Vercel skills.sh catalog data
"""

from __future__ import annotations

import html
import re
import time
from typing import Dict, List
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from fastapi import APIRouter, Depends, HTTPException

from backend.routers.auth import get_current_user

router = APIRouter()

BASE_URL = "https://skills.sh"
OWNER = "vercel"
REQUEST_TIMEOUT = 20
CATALOG_TTL_SECONDS = 1800
DETAIL_TTL_SECONDS = 1800

_catalog_cache: Dict[str, object] = {"expires_at": 0.0, "data": []}
_detail_cache: Dict[str, Dict[str, object]] = {}


def _require_user(user):
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")


def _fetch_html(url: str) -> str:
    request = Request(url, headers={"User-Agent": "CEO-Agent/1.0"})
    try:
        with urlopen(request, timeout=REQUEST_TIMEOUT) as response:
            return response.read().decode("utf-8", errors="replace")
    except HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"skills.sh request failed ({exc.code})") from exc
    except URLError as exc:
        raise HTTPException(status_code=502, detail="skills.sh request failed") from exc


def _parse_metric_value(value: str) -> int:
    cleaned = value.strip().upper().replace(",", "")
    multiplier = 1
    if cleaned.endswith("K"):
        multiplier = 1000
        cleaned = cleaned[:-1]
    elif cleaned.endswith("M"):
        multiplier = 1_000_000
        cleaned = cleaned[:-1]

    try:
        return int(float(cleaned) * multiplier)
    except ValueError:
        return 0


def _clean_text(raw: str) -> str:
    without_tags = re.sub(r"<[^>]+>", " ", raw)
    return " ".join(html.unescape(without_tags).split())


def _extract_anchor_matches(page_html: str, pattern: str) -> List[re.Match[str]]:
    return list(re.finditer(pattern, page_html, re.DOTALL))


def _extract_prose_blocks(page_html: str) -> List[str]:
    return re.findall(
        r'<div class="prose[^"]*">(.*?)</div>',
        page_html,
        re.DOTALL,
    )


def _load_catalog() -> List[dict]:
    if _catalog_cache["expires_at"] > time.time():
        return _catalog_cache["data"]  # type: ignore[return-value]

    owner_html = _fetch_html(f"{BASE_URL}/{OWNER}")
    source_matches = _extract_anchor_matches(owner_html, rf'href="/{OWNER}/([^"/]+)"')
    sources: List[str] = []
    seen_sources = set()
    for match in source_matches:
        source = match.group(1)
        if source in seen_sources:
            continue
        seen_sources.add(source)
        sources.append(source)

    skills: List[dict] = []
    for source in sources:
        source_html = _fetch_html(f"{BASE_URL}/{OWNER}/{source}")
        anchor_pattern = rf'<a[^>]+href="/{OWNER}/{re.escape(source)}/([^"/]+)"[^>]*>(.*?)</a>'
        for match in _extract_anchor_matches(source_html, anchor_pattern):
            skill_name = match.group(1)
            text = _clean_text(match.group(2))
            installs_label = text.split()[-1] if text else "0"
            skills.append(
                {
                    "id": f"{source}/{skill_name}",
                    "name": skill_name,
                    "source": source,
                    "owner": OWNER,
                    "installs_label": installs_label,
                    "installs_count": _parse_metric_value(installs_label),
                }
            )

    skills.sort(key=lambda skill: (-skill["installs_count"], skill["source"], skill["name"]))
    _catalog_cache["expires_at"] = time.time() + CATALOG_TTL_SECONDS
    _catalog_cache["data"] = skills
    return skills


def _extract_metric(page_html: str, label: str) -> str:
    pattern = rf">{re.escape(label)}</span></div><div[^>]*>(.*?)</div>"
    match = re.search(pattern, page_html, re.DOTALL)
    return _clean_text(match.group(1)) if match else ""


def _extract_trust_metric(page_html: str, label: str) -> str:
    pattern = rf">{re.escape(label)}</span><span[^>]*>(.*?)</span>"
    match = re.search(pattern, page_html, re.DOTALL)
    return _clean_text(match.group(1)) if match else ""


def _load_skill_detail(source: str, skill_name: str) -> dict:
    cache_key = f"{source}/{skill_name}"
    cached = _detail_cache.get(cache_key)
    if cached and cached["expires_at"] > time.time():
        return cached["data"]  # type: ignore[return-value]

    page_html = _fetch_html(f"{BASE_URL}/{OWNER}/{source}/{skill_name}")

    title_match = re.search(r"<h1[^>]*>(.*?)</h1>", page_html, re.DOTALL)
    code_match = re.search(r"<code[^>]*>\s*<span[^>]*>\$\s*</span>\s*(.*?)</code>", page_html, re.DOTALL)
    prose_blocks = _extract_prose_blocks(page_html)

    detail = {
        "id": cache_key,
        "owner": OWNER,
        "source": source,
        "name": _clean_text(title_match.group(1)) if title_match else skill_name,
        "install_command": _clean_text(code_match.group(1)) if code_match else "",
        "summary_html": prose_blocks[0] if len(prose_blocks) > 0 else "",
        "skill_html": prose_blocks[1] if len(prose_blocks) > 1 else "",
        "repository": _extract_metric(page_html, "Repository"),
        "weekly_installs": _extract_metric(page_html, "Weekly Installs"),
        "github_stars": _extract_metric(page_html, "GitHub Stars"),
        "first_seen": _extract_metric(page_html, "First Seen"),
        "trust": {
            "gen_agent": _extract_trust_metric(page_html, "Gen Agent Trust Hub"),
            "socket": _extract_trust_metric(page_html, "Socket"),
            "snyk": _extract_trust_metric(page_html, "Snyk"),
        },
    }

    _detail_cache[cache_key] = {
        "expires_at": time.time() + DETAIL_TTL_SECONDS,
        "data": detail,
    }
    return detail


@router.get("/vercel")
async def list_vercel_skills(user=Depends(get_current_user)):
    _require_user(user)
    return {"success": True, "owner": OWNER, "skills": _load_catalog()}


@router.get("/vercel/{source}/{skill_name}")
async def get_vercel_skill_detail(source: str, skill_name: str, user=Depends(get_current_user)):
    _require_user(user)
    return {"success": True, "skill": _load_skill_detail(source, skill_name)}
