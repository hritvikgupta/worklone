from typing import Dict
import httpx
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class LinearCreateCustomerRequestTool(BaseTool):
    name = "linear_create_customer_request"
    description = "Create a customer request (need) in Linear. Assign to customer, set urgency (priority: 0 = Not important, 1 = Important), and optionally link to an issue."
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="LINEAR_ACCESS_TOKEN",
                description="Access token",
                env_var="LINEAR_ACCESS_TOKEN",
                required=True,
                auth_type="oauth",
            )
        ]

    async def _resolve_access_token(self, context: dict | None) -> str:
        connection = await resolve_oauth_connection(
            "linear",
            context=context,
            context_token_keys=("linear_token",),
            env_token_keys=("LINEAR_ACCESS_TOKEN",),
            placeholder_predicate=self._is_placeholder_token,
            allow_refresh=True,
        )
        return connection.access_token

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "customerId": {
                    "type": "string",
                    "description": "Customer ID to assign this request to",
                },
                "body": {
                    "type": "string",
                    "description": "Description of the customer request",
                },
                "priority": {
                    "type": "number",
                    "description": "Urgency level: 0 = Not important, 1 = Important (default: 0)",
                },
                "issueId": {
                    "type": "string",
                    "description": "Issue ID to link this request to",
                },
                "projectId": {
                    "type": "string",
                    "description": "Project ID to link this request to",
                },
            },
            "required": ["customerId"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)

        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }

        input_data: Dict[str, any] = {
            "customerId": parameters["customerId"],
            "priority": parameters.get("priority", 0),
        }
        body = parameters.get("body")
        if body:
            input_data["body"] = body
        issue_id = parameters.get("issueId")
        if issue_id:
            input_data["issueId"] = issue_id
        project_id = parameters.get("projectId")
        if project_id:
            input_data["projectId"] = project_id

        query = """
          mutation CustomerNeedCreate($input: CustomerNeedCreateInput!) {
            customerNeedCreate(input: $input) {
              success
              need {
                id
                body
                priority
                createdAt
                updatedAt
                archivedAt
                customer {
                  id
                  name
                }
                issue {
                  id
                  title
                }
                project {
                  id
                  name
                }
                creator {
                  id
                  name
                }
                url
              }
            }
          }
        """
        json_body = {
            "query": query,
            "variables": {
                "input": input_data,
            },
        }

        url = "https://api.linear.app/graphql"

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=json_body)

                if response.status_code not in [200]:
                    return ToolResult(success=False, output="", error=response.text)

                data = response.json()

                if data.get("errors"):
                    error_msg = data["errors"][0].get("message", "Failed to create customer request")
                    return ToolResult(success=False, output="", error=error_msg)

                result = data.get("data", {}).get("customerNeedCreate", {})
                if not result.get("success"):
                    return ToolResult(success=False, output="", error="Customer request creation was not successful")

                return ToolResult(success=True, output=response.text, data=data)

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")