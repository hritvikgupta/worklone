from typing import Any
import httpx
from worklone_employee.tools.base import BaseTool, ToolResult, CredentialRequirement


class JiraSearchIssuesTool(BaseTool):
    name = "jira_search_issues"
    description = "Search for Jira issues using JQL (Jira Query Language)"
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="access_token",
                description="OAuth access token for Jira",
                env_var="JIRA_ACCESS_TOKEN",
                required=True,
                auth_type="oauth",
            )
        ]

    async def _resolve_access_token(self, context: dict | None) -> str:
        connection = await resolve_oauth_connection(
            "jira",
            context=context,
            context_token_keys=("access_token",),
            env_token_keys=("JIRA_ACCESS_TOKEN",),
            placeholder_predicate=self._is_placeholder_token,
            allow_refresh=True,
        )
        return connection.access_token

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "domain": {
                    "type": "string",
                    "description": "Your Jira domain (e.g., yourcompany.atlassian.net)",
                },
                "jql": {
                    "type": "string",
                    "description": 'JQL query string to search for issues (e.g., "project = PROJ AND status = Open")',
                },
                "nextPageToken": {
                    "type": "string",
                    "description": "Cursor token for the next page of results. Omit for the first page.",
                },
                "maxResults": {
                    "type": "number",
                    "description": "Maximum number of results to return per page (default: 50)",
                },
                "fields": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Array of field names to return (default: all navigable). Use [\"*all\"] for every field.",
                },
            },
            "required": ["domain", "jql"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)

        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")

        domain: str = parameters["domain"]
        jql: str = parameters["jql"]
        next_page_token: str | None = parameters.get("nextPageToken")
        max_results: int | None | float = parameters.get("maxResults")
        fields: list[str] | None = parameters.get("fields")
        cloud_id: str | None = parameters.get("cloudId")

        headers = {
            "Accept": "application/json",
            "Authorization": f"Bearer {access_token}",
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                if cloud_id:
                    pass
                else:
                    access_url = "https://api.atlassian.com/oauth/token/accessible-resources"
                    resp_access = await client.get(access_url, headers=headers)
                    if resp_access.status_code != 200:
                        try:
                            err_data = resp_access.json()
                            if "errorMessages" in err_data:
                                message = ", ".join(err_data["errorMessages"])
                            elif "message" in err_data:
                                message = err_data["message"]
                            else:
                                message = resp_access.text
                        except Exception:
                            message = resp_access.text
                        return ToolResult(
                            success=False,
                            output="",
                            error=f"Failed to get cloud ID ({resp_access.status_code}): {message}",
                        )
                    data_access = resp_access.json()
                    resources = data_access.get("accessibleResources", [])
                    found_cloud_id = None
                    normalized_domain = domain.rstrip("/")
                    for resource in resources:
                        resource_url = resource.get("url", "").rstrip("/")
                        if resource_url == f"https://{normalized_domain}":
                            found_cloud_id = resource["id"]
                            break
                    if not found_cloud_id:
                        return ToolResult(
                            success=False,
                            output="",
                            error=f"No matching cloud ID found for domain '{domain}'",
                        )
                    cloud_id = found_cloud_id

                query_params: dict[str, str] = {
                    "jql": jql,
                }
                if next_page_token:
                    query_params["nextPageToken"] = next_page_token
                if max_results is not None:
                    query_params["maxResults"] = str(int(max_results))
                if isinstance(fields, list) and len(fields) > 0:
                    query_params["fields"] = ",".join(fields)
                else:
                    query_params["fields"] = "*all"

                search_url = f"https://api.atlassian.com/ex/jira/{cloud_id}/rest/api/3/search/jql"
                resp_search = await client.get(search_url, headers=headers, params=query_params)

                if resp_search.status_code != 200:
                    try:
                        err_data = resp_search.json()
                        if "errorMessages" in err_data:
                            message = ", ".join(err_data["errorMessages"])
                        elif "message" in err_data:
                            message = err_data["message"]
                        else:
                            message = resp_search.text
                    except Exception:
                        message = resp_search.text
                    return ToolResult(
                        success=False,
                        output="",
                        error=f"Failed to search Jira issues ({resp_search.status_code}): {message}",
                    )

                return ToolResult(
                    success=True,
                    output=resp_search.text,
                    data=resp_search.json(),
                )
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")