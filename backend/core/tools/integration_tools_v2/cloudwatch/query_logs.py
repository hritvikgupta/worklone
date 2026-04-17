from typing import Any, Dict, List, Optional
import asyncio
import boto3
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class CloudWatchQueryLogsTool(BaseTool):
    name = "cloudwatch_query_logs"
    description = "Run a CloudWatch Log Insights query against one or more log groups"
    category = "integration"

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return []

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "awsRegion": {
                    "type": "string",
                    "description": "AWS region (e.g., us-east-1)",
                },
                "awsAccessKeyId": {
                    "type": "string",
                    "description": "AWS access key ID",
                },
                "awsSecretAccessKey": {
                    "type": "string",
                    "description": "AWS secret access key",
                },
                "logGroupNames": {
                    "type": "array",
                    "items": {
                        "type": "string"
                    },
                    "description": "Log group names to query",
                },
                "queryString": {
                    "type": "string",
                    "description": "CloudWatch Log Insights query string",
                },
                "startTime": {
                    "type": "number",
                    "description": "Start time as Unix epoch seconds",
                },
                "endTime": {
                    "type": "number",
                    "description": "End time as Unix epoch seconds",
                },
                "limit": {
                    "type": "number",
                    "description": "Maximum number of results to return",
                },
            },
            "required": [
                "awsRegion",
                "awsAccessKeyId",
                "awsSecretAccessKey",
                "logGroupNames",
                "queryString",
                "startTime",
                "endTime",
            ],
        }

    def _parse_results(self, raw_results: List[Any]) -> List[Dict[str, Any]]:
        if not raw_results:
            return []
        all_fields = set()
        for row in raw_results:
            for item in row:
                all_fields.add(item["field"])
        fields = sorted(all_fields)
        parsed_rows = []
        for row in raw_results:
            row_dict = {item["field"]: item["value"] for item in row}
            parsed_row = {field: row_dict.get(field) for field in fields}
            parsed_rows.append(parsed_row)
        return parsed_rows

    async def _poll_query_results(self, client, query_id: str) -> Dict[str, Any]:
        max_attempts = 60
        poll_interval = 2.0
        for attempt in range(max_attempts):
            get_response = client.get_query_results(queryId=query_id)
            status = get_response["status"]
            statistics = get_response.get("statistics", {})
            results = self._parse_results(get_response.get("results", []))
            if status == "Complete":
                return {
                    "results": results,
                    "statistics": statistics,
                    "status": status,
                }
            if status in ["Failed", "Cancelled", "TimedOut", "Unknown"]:
                error_msg = get_response.get("errorMessage", "")
                raise RuntimeError(f"Query {status.lower()}: {error_msg}")
            await asyncio.sleep(poll_interval)
        raise TimeoutError(f"Query did not complete after {max_attempts * poll_interval} seconds")

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        try:
            aws_region: str = parameters["awsRegion"]
            access_key_id: str = parameters["awsAccessKeyId"]
            secret_access_key: str = parameters["awsSecretAccessKey"]
            log_group_names: List[str] = parameters["logGroupNames"]
            query_string: str = parameters["queryString"]
            start_time: float = parameters["startTime"]
            end_time: float = parameters["endTime"]
            limit: Optional[int] = parameters.get("limit")
            if limit is not None:
                limit = int(limit)

            if not access_key_id.strip() or not secret_access_key.strip():
                raise ValueError("AWS access key ID and secret access key must be provided.")

            start_time_ms = int(start_time * 1000)
            end_time_ms = int(end_time * 1000)

            session = boto3.Session(
                aws_access_key_id=access_key_id,
                aws_secret_access_key=secret_access_key,
                region_name=aws_region,
            )
            client = session.client("logs")

            start_response = client.start_query(
                logGroupNames=log_group_names,
                queryString=query_string,
                startTime=start_time_ms,
                endTime=end_time_ms,
                limit=limit,
            )
            query_id = start_response["queryId"]
            if not query_id:
                raise ValueError("Failed to start CloudWatch Log Insights query: no queryId returned")

            result = await self._poll_query_results(client, query_id)

            return ToolResult(
                success=True,
                output=f"Query status: {result['status']}",
                data=result,
            )
        except KeyError as e:
            return ToolResult(
                success=False,
                output="",
                error=f"Missing required parameter: {str(e)}",
            )
        except Exception as e:
            return ToolResult(
                success=False,
                output="",
                error=f"CloudWatch Log Insights query failed: {str(e)}",
            )