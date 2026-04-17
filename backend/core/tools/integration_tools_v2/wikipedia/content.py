from typing import Dict
import httpx
import re
import urllib.parse
from datetime import datetime, timezone
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class WikipediaContentTool(BaseTool):
    name = "wikipedia_content"
    description = "Get the full HTML content of a Wikipedia page."
    category = "integration"

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return []

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "pageTitle": {
                    "type": "string",
                    "description": "Title of the Wikipedia page to get content for",
                },
            },
            "required": ["pageTitle"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        page_title = parameters["pageTitle"]
        encoded_title = urllib.parse.quote(page_title.replace(" ", "_"))
        url = f"https://en.wikipedia.org/api/rest_v1/page/html/{encoded_title}"
        headers = {
            "User-Agent": "Sim/1.0 (https://sim.ai)",
            "Accept": 'text/html; charset=utf-8; profile="https://www.mediawiki.org/wiki/Specs/HTML/2.1.0"',
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers)

                if response.status_code == 200:
                    html = response.text
                    etag = response.headers.get("etag", "")
                    revision_match = re.match(r'^"(\d+)', etag)
                    revision = int(revision_match.group(1)) if revision_match else 0
                    timestamp = response.headers.get("last-modified", datetime.now(timezone.utc).isoformat())
                    tid = etag
                    content = {
                        "title": "",
                        "pageid": 0,
                        "html": html,
                        "revision": revision,
                        "tid": tid,
                        "timestamp": timestamp,
                        "content_model": "wikitext",
                        "content_format": "text/html",
                    }
                    return ToolResult(success=True, output=html, data={"content": content})
                else:
                    return ToolResult(success=False, output="", error=response.text)

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")