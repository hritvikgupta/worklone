from typing import Any, Dict
import httpx
import base64
import json
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class AshbyGetCandidateTool(BaseTool):
    name = "ashby_get_candidate"
    description = "Retrieves full details about a single candidate by their ID."
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="ASHBY_API_KEY",
                description="Ashby API Key",
                env_var="ASHBY_API_KEY",
                required=True,
                auth_type="api_key",
            )
        ]

    async def _resolve_access_token(self, context: dict | None) -> str:
        connection = await resolve_oauth_connection(
            "ashby",
            context=context,
            context_token_keys=("ashby_api_key",),
            env_token_keys=("ASHBY_API_KEY",),
            placeholder_predicate=self._is_placeholder_token,
            allow_refresh=False,
        )
        return connection.access_token

    def _transform_response(self, data: Dict[str, Any]) -> Dict[str, Any]:
        if not data.get("success"):
            error_info = data.get("errorInfo", {})
            error_msg = error_info.get("message") if isinstance(error_info, dict) else str(error_info)
            raise ValueError(error_msg or "Failed to get candidate")
        r = data.get("results", {})
        primary_email = r.get("primaryEmailAddress")
        primary_email_address = None
        if primary_email:
            primary_email_address = {
                "value": primary_email.get("value", "") or "",
                "type": primary_email.get("type", "Other"),
                "isPrimary": primary_email.get("isPrimary", True),
            }
        primary_phone = r.get("primaryPhoneNumber")
        primary_phone_number = None
        if primary_phone:
            primary_phone_number = {
                "value": primary_phone.get("value", "") or "",
                "type": primary_phone.get("type", "Other"),
                "isPrimary": primary_phone.get("isPrimary", True),
            }
        social_links = r.get("socialLinks", [])
        linked_in_url = next((link.get("url") for link in social_links if link.get("type") == "LinkedIn"), None)
        github_url = next((link.get("url") for link in social_links if link.get("type") == "GitHub"), None)
        tags = [
            {
                "id": tag.get("id"),
                "title": tag.get("title"),
            }
            for tag in r.get("tags", [])
        ]
        return {
            "id": r.get("id"),
            "name": r.get("name"),
            "primaryEmailAddress": primary_email_address,
            "primaryPhoneNumber": primary_phone_number,
            "profileUrl": r.get("profileUrl"),
            "position": r.get("position"),
            "company": r.get("company"),
            "linkedInUrl": linked_in_url,
            "githubUrl": github_url,
            "tags": tags,
            "applicationIds": r.get("applicationIds", []),
            "createdAt": r.get("createdAt"),
            "updatedAt": r.get("updatedAt"),
        }

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "candidateId": {
                    "type": "string",
                    "description": "The UUID of the candidate to fetch",
                },
            },
            "required": ["candidateId"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        auth_header = base64.b64encode(f"{access_token}:".encode("utf-8")).decode("utf-8")
        headers = {
            "Authorization": f"Basic {auth_header}",
            "Content-Type": "application/json",
        }
        
        url = "https://api.ashbyhq.com/candidate.info"
        body = {
            "candidateId": parameters["candidateId"].strip(),
        }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=body)
                
                if response.status_code not in [200, 201]:
                    return ToolResult(success=False, output="", error=response.text)
                
                data = response.json()
                transformed = self._transform_response(data)
                output_str = json.dumps(transformed)
                return ToolResult(success=True, output=output_str, data=transformed)
                    
        except ValueError as e:
            return ToolResult(success=False, output="", error=str(e))
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")