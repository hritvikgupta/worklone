from typing import Any, Dict
import httpx
import json
from backend.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class LinearCreateAttachmentTool(BaseTool):
    name = "linear_create_attachment"
    description = "Add an attachment to an issue in Linear"
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="LINEAR_ACCESS_TOKEN",
                description="Access token for Linear",
                env_var="LINEAR_ACCESS_TOKEN",
                required=True,
                auth_type="oauth",
            )
        ]

    async def _resolve_access_token(self, context: dict | None) -> str:
        connection = await resolve_oauth_connection(
            "linear",
            context=context,
            context_token_keys=("provider_token",),
            env_token_keys=("LINEAR_ACCESS_TOKEN",),
            placeholder_predicate=self._is_placeholder_token,
            allow_refresh=True,
        )
        return connection.access_token

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "issueId": {
                    "type": "string",
                    "description": "Issue ID to attach to",
                },
                "url": {
                    "type": "string",
                    "description": "URL of the attachment",
                },
                "file": {
                    "type": "file",
                    "description": "File to attach",
                },
                "title": {
                    "type": "string",
                    "description": "Attachment title",
                },
                "subtitle": {
                    "type": "string",
                    "description": "Attachment subtitle/description",
                },
            },
            "required": ["issueId", "title"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)

        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="{}", error="Access token not configured.")

        issue_id = parameters.get("issueId")
        if not issue_id:
            return ToolResult(success=False, output="{}", error="Issue ID is required")

        title = parameters.get("title")
        if not title:
            return ToolResult(success=False, output="{}", error="Title is required")

        attachment_url = parameters.get("url")
        if not attachment_url:
            file_param = parameters.get("file")
            if isinstance(file_param, dict):
                attachment_url = file_param.get("url")

        if not attachment_url:
            return ToolResult(success=False, output="{}", error="URL or file is required")

        subtitle = parameters.get("subtitle")
        input_data: Dict[str, Any] = {
            "issueId": issue_id,
            "url": attachment_url,
            "title": title,
        }
        if subtitle is not None and subtitle != "":
            input_data["subtitle"] = subtitle

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {access_token}",
        }

        url = "https://api.linear.app/graphql"
        body = {
            "query": """
                mutation CreateAttachment($input: AttachmentCreateInput!) {
                  attachmentCreate(input: $input) {
                    success
                    attachment {
                      id
                      title
                      subtitle
                      url
                      createdAt
                      updatedAt
                    }
                  }
                }
            """.strip(),
            "variables": {
                "input": input_data,
            },
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=body)

                if response.status_code not in (200, 201, 204):
                    return ToolResult(
                        success=False,
                        output="{}",
                        error=f"HTTP {response.status_code}: {response.text}",
                    )

                try:
                    data = response.json()
                except Exception as json_err:
                    return ToolResult(
                        success=False,
                        output=response.text,
                        error=f"Invalid JSON response: {str(json_err)}",
                    )

                if "errors" in data and data["errors"]:
                    error_msg = (
                        data["errors"][0].get("message", "GraphQL error")
                        if isinstance(data["errors"], list) and data["errors"]
                        else "GraphQL errors"
                    )
                    return ToolResult(success=False, output="{}", error=error_msg)

                result = data.get("data", {}).get("attachmentCreate", {})
                if not result.get("success", False):
                    return ToolResult(
                        success=False, output="{}", error="Attachment creation was not successful"
                    )

                attachment = result.get("attachment", {})
                output_data = {"attachment": attachment}
                return ToolResult(
                    success=True, output=json.dumps(output_data), data=output_data
                )

        except Exception as e:
            return ToolResult(success=False, output="{}", error=f"API error: {str(e)}")