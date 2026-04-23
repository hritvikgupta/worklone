from typing import Any, Dict
import httpx
import json
import re
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class DatabricksListClustersTool(BaseTool):
    name = "databricks_list_clusters"
    description = "List all clusters in a Databricks workspace including their state, configuration, and resource details."
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return []

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "host": {
                    "type": "string",
                    "description": "Databricks workspace host (e.g., dbc-abc123.cloud.databricks.com)",
                },
                "apiKey": {
                    "type": "string",
                    "description": "Databricks Personal Access Token",
                },
            },
            "required": ["host", "apiKey"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        api_key = parameters.get("apiKey", "").strip()
        if self._is_placeholder_token(api_key):
            return ToolResult(success=False, output="", error="Databricks Personal Access Token not configured.")

        host = parameters.get("host", "").strip()
        if not host:
            return ToolResult(success=False, output="", error="Databricks workspace host not configured.")

        host_clean = re.sub(r"^https?://", "", host).rstrip("/")
        url = f"https://{host_clean}/api/2.0/clusters/list"

        headers = {
            "Accept": "application/json",
            "Authorization": f"Bearer {api_key}",
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers)

                if response.status_code == 200:
                    data = response.json()
                    clusters = []
                    for cluster in data.get("clusters", []):
                        autoscale = cluster.get("autoscale")
                        clusters.append(
                            {
                                "clusterId": cluster.get("cluster_id") or "",
                                "clusterName": cluster.get("cluster_name") or "",
                                "state": cluster.get("state") or "UNKNOWN",
                                "stateMessage": cluster.get("state_message") or "",
                                "creatorUserName": cluster.get("creator_user_name") or "",
                                "sparkVersion": cluster.get("spark_version") or "",
                                "nodeTypeId": cluster.get("node_type_id") or "",
                                "driverNodeTypeId": cluster.get("driver_node_type_id") or "",
                                "numWorkers": cluster.get("num_workers"),
                                "autoscale": (
                                    {
                                        "minWorkers": autoscale.get("min_workers") or 0,
                                        "maxWorkers": autoscale.get("max_workers") or 0,
                                    }
                                    if autoscale
                                    else None
                                ),
                                "clusterSource": cluster.get("cluster_source") or "",
                                "autoterminationMinutes": cluster.get("autotermination_minutes") or 0,
                                "startTime": cluster.get("start_time"),
                            }
                        )
                    result_data = {"clusters": clusters}
                    return ToolResult(
                        success=True, output=json.dumps(result_data), data=result_data
                    )
                else:
                    try:
                        error_data = response.json()
                        error_msg = (
                            error_data.get("message")
                            or error_data.get("error", {}).get("message")
                            or response.text
                        )
                    except Exception:
                        error_msg = response.text or "Unknown error"
                    return ToolResult(success=False, output="", error=error_msg)

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")