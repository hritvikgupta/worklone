from typing import Any, Dict
import httpx
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class LinearUpdateCustomerRequestTool(BaseTool):
    name = "linear_update_customer_request"
    description = "Update a customer request (need) in Linear. Can change urgency, description, customer assignment, and linked issue."
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
                "customerNeedId": {
                    "type": "string",
                    "description": "Customer request ID to update",
                },
                "body": {
                    "type": "string",
                    "description": "Updated description of the customer request",
                },
                "priority": {
                    "type": "number",
                    "description": "Updated urgency level: 0 = Not important, 1 = Important",
                },
                "customerId": {
                    "type": "string",
                    "description": "New customer ID to assign this request to",
                },
                "issueId": {
                    "type": "string",
                    "description": "New issue ID to link this request to",
                },
                "projectId": {
                    "type": "string",
                    "description": "New project ID to link this request to",
                },
            },
            "required": ["customerNeedId"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)

        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }

        input_dict: Dict[str, Any] = {}
        body = parameters.get("body")
        if body is not None and str(body).strip() != "":
            input_dict["body"] = body
        priority = parameters.get("priority")
        if priority is not None:
            input_dict["priority"] = priority
        customer_id = parameters.get("customerId")
        if customer_id is not None and str(customer_id).strip() != "":
            input_dict["customerId"] = customer_id
        issue_id = parameters.get("issueId")
        if issue_id is not None and str(issue_id).strip() != "":
            input_dict["issueId"] = issue_id
        project_id = parameters.get("projectId")
        if project_id is not None and str(project_id).strip() != "":
            input_dict["projectId"] = project_id

        query = """
          mutation CustomerNeedUpdate($id: String!, $input: CustomerNeedUpdateInput!) {
            customerNeedUpdate(id: $id, input: $input) {
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
            "query": query.strip(),
            "variables": {
                "id": parameters["customerNeedId"],
                "input": input_dict,
            },
        }

        url = "https://api.linear.app/graphql"

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=json_body)

                if response.status_code == 200:
                    data = response.json()
                    errors = data.get("errors", [])
                    if errors:
                        error_msg = errors[0].get("message", "Failed to update customer request")
                        return ToolResult(success=False, output="", error=error_msg)

                    result = data.get("data", {}).get("customerNeedUpdate", {})
                    if not result.get("success", False):
                        return ToolResult(
                            success=False,
                            output="",
                            error="Failed to update customer request",
                        )
                    return ToolResult(success=True, output=response.text, data=data)
                else:
                    return ToolResult(success=False, output="", error=response.text)

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")