from typing import Any, Dict, List
import httpx
import base64
import json
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class GongGetCallTranscriptTool(BaseTool):
    name = "gong_get_call_transcript"
    description = "Retrieve transcripts of calls from Gong by call IDs or date range."
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="GONG_ACCESS_KEY",
                description="Gong API Access Key",
                env_var="GONG_ACCESS_KEY",
                required=True,
                auth_type="api_key",
            ),
            CredentialRequirement(
                key="GONG_ACCESS_KEY_SECRET",
                description="Gong API Access Key Secret",
                env_var="GONG_ACCESS_KEY_SECRET",
                required=True,
                auth_type="api_key",
            ),
        ]

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "callIds": {
                    "type": "string",
                    "description": "Comma-separated list of call IDs to retrieve transcripts for",
                },
                "fromDateTime": {
                    "type": "string",
                    "description": "Start date/time filter in ISO-8601 format",
                },
                "toDateTime": {
                    "type": "string",
                    "description": "End date/time filter in ISO-8601 format",
                },
                "workspaceId": {
                    "type": "string",
                    "description": "Gong workspace ID to filter calls",
                },
                "cursor": {
                    "type": "string",
                    "description": "Pagination cursor from a previous response",
                },
            },
            "required": [],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_key = context.get("GONG_ACCESS_KEY") if context else None
        access_key_secret = context.get("GONG_ACCESS_KEY_SECRET") if context else None
        if (
            not access_key
            or not access_key_secret
            or self._is_placeholder_token(access_key)
            or self._is_placeholder_token(access_key_secret)
        ):
            return ToolResult(success=False, output="", error="Gong credentials not configured.")

        auth_str = f"{access_key}:{access_key_secret}"
        auth_b64 = base64.b64encode(auth_str.encode("utf-8")).decode("utf-8")
        headers = {
            "Authorization": f"Basic {auth_b64}",
            "Content-Type": "application/json",
        }

        filter_dict: Dict[str, Any] = {}
        call_ids = parameters.get("callIds")
        if call_ids:
            filter_dict["callIds"] = [cid.strip() for cid in str(call_ids).split(",") if cid.strip()]
        for key in ("fromDateTime", "toDateTime", "workspaceId"):
            value = parameters.get(key)
            if value:
                filter_dict[key] = value
        body: Dict[str, Any] = {"filter": filter_dict}
        cursor_param = parameters.get("cursor")
        if cursor_param:
            body["cursor"] = cursor_param

        url = "https://api.gong.io/v2/calls/transcript"

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=body)

                if response.status_code not in {200, 201, 204}:
                    error_msg = response.text
                    try:
                        resp_data = response.json()
                        errors = resp_data.get("errors", [])
                        if errors:
                            error_msg = errors[0].get("message", error_msg)
                        else:
                            error_msg = resp_data.get("message", error_msg)
                    except Exception:
                        pass
                    return ToolResult(success=False, output="", error=error_msg)

                resp_data = response.json()

                call_transcripts: List[Dict[str, Any]] = []
                for ct in resp_data.get("callTranscripts", []):
                    transcript: List[Dict[str, Any]] = []
                    for t in ct.get("transcript", []):
                        sentences: List[Dict[str, Any]] = []
                        for s in t.get("sentences", []):
                            sentences.append({
                                "start": s.get("start") or 0,
                                "end": s.get("end") or 0,
                                "text": s.get("text") or "",
                            })
                        transcript.append({
                            "speakerId": t.get("speakerId"),
                            "topic": t.get("topic"),
                            "sentences": sentences,
                        })
                    call_transcripts.append({
                        "callId": ct.get("callId") or "",
                        "transcript": transcript,
                    })

                cursor_out = resp_data.get("records", {}).get("cursor")

                transformed = {
                    "callTranscripts": call_transcripts,
                    "cursor": cursor_out,
                }
                return ToolResult(
                    success=True, output=json.dumps(transformed), data=transformed
                )

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")