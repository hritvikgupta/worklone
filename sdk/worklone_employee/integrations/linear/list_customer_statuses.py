from typing import Any, Dict
import httpx
import json
from worklone_employee.tools.base import BaseTool, ToolResult, CredentialRequirement


class LinearListCustomerStatusesTool(BaseTool):
    name = "linear_list_customer_statuses"
    description = "List all customer statuses in Linear"
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
                "first": {
                    "type": "number",
                    "description": "Number of statuses to return (default: 50)",
                },
                "after": {
                    "type": "string",
                    "description": "Cursor for pagination",
                },
            },
            "required": [],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)

        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }

        url = "https://api.linear.app/graphql"

        query = """
        query CustomerStatuses($first: Int, $after: String) {
          customerStatuses(first: $first, after: $after) {
            nodes {
              id
              name
              description
              color
              position
              type
              createdAt
              updatedAt
              archivedAt
            }
            pageInfo {
              hasNextPage
              endCursor
            }
          }
        }
        """.strip()

        first = parameters.get("first")
        if first is not None:
            first = int(float(first))
        else:
            first = 50

        after = parameters.get("after")
        if after:
            after = str(after).strip()
            if not after:
                after = None
        else:
            after = None

        variables: Dict[str, Any] = {"first": first}
        if after is not None:
            variables["after"] = after

        body = {
            "query": query,
            "variables": variables,
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=body)

                if response.status_code != 200:
                    return ToolResult(success=False, output="", error=response.text)

                try:
                    data = response.json()
                except Exception:
                    return ToolResult(success=False, output="", error=response.text)

                if data.get("errors"):
                    error_msg = data["errors"][0].get("message", "Failed to list customer statuses") if data["errors"] else "Unknown GraphQL error"
                    return ToolResult(success=False, output="", error=error_msg)

                result = data.get("data", {}).get("customerStatuses")
                if not result:
                    return ToolResult(success=False, output="", error="No customer statuses data in response")

                output_data = {
                    "customerStatuses": result["nodes"],
                    "pageInfo": {
                        "hasNextPage": result["pageInfo"]["hasNextPage"],
                        "endCursor": result["pageInfo"]["endCursor"],
                    },
                }
                output_str = json.dumps(output_data)

                return ToolResult(success=True, output=output_str, data=output_data)

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")