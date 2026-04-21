from typing import Any, Dict
import httpx
from worklone_employee.tools.base import BaseTool, ToolResult, CredentialRequirement


class SlackEditCanvasTool(BaseTool):
    name = "slack_edit_canvas"
    description = "Edit an existing Slack canvas by inserting, replacing, or deleting content"
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="SLACK_ACCESS_TOKEN",
                description="Access token or bot token",
                env_var="SLACK_ACCESS_TOKEN",
                required=True,
                auth_type="oauth",
            )
        ]

    async def _resolve_access_token(self, context: dict | None) -> str:
        connection = await resolve_oauth_connection(
            "slack",
            context=context,
            context_token_keys=("accessToken", "botToken"),
            env_token_keys=("SLACK_ACCESS_TOKEN",),
            placeholder_predicate=self._is_placeholder_token,
            allow_refresh=True,
        )
        return connection.access_token

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "canvasId": {
                    "type": "string",
                    "description": "Canvas ID to edit (e.g., F1234ABCD)",
                },
                "operation": {
                    "type": "string",
                    "description": "Edit operation: insert_at_start, insert_at_end, insert_after, insert_before, replace, delete, or rename",
                },
                "content": {
                    "type": "string",
                    "description": "Markdown content for the operation (required for insert/replace operations)",
                },
                "sectionId": {
                    "type": "string",
                    "description": "Section ID to target (required for insert_after, insert_before, replace, and delete)",
                },
                "title": {
                    "type": "string",
                    "description": "New title for the canvas (only used with rename operation)",
                },
            },
            "required": ["canvasId", "operation"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        
        url = "https://slack.com/api/canvases.edit"
        
        change = {
            "operation": parameters["operation"],
        }
        if parameters.get("sectionId"):
            change["section_id"] = parameters["sectionId"].strip()
        if parameters["operation"] == "rename" and parameters.get("title"):
            change["title_content"] = {
                "type": "markdown",
                "markdown": parameters["title"],
            }
        elif parameters.get("content") and parameters["operation"] != "delete":
            change["document_content"] = {
                "type": "markdown",
                "markdown": parameters["content"],
            }
        
        body = {
            "canvas_id": parameters["canvasId"].strip(),
            "changes": [change],
        }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=body)
                
                if response.status_code != 200:
                    return ToolResult(success=False, output="", error=response.text)
                
                data = response.json()
                if data.get("ok"):
                    return ToolResult(success=True, output="Successfully edited canvas", data=data)
                else:
                    return ToolResult(success=False, output="", error=data.get("error", "Failed to edit canvas"))
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")