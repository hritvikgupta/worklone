from typing import Any, Dict, List
import boto3
import json
from backend.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class CloudWatchDescribeLogGroupsTool(BaseTool):
    name = "CloudWatch Describe Log Groups"
    description = "List available CloudWatch log groups"
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="aws_access_key_id",
                description="AWS access key ID",
                env_var="AWS_ACCESS_KEY_ID",
                required=True,
                auth_type="api_key",
            ),
            CredentialRequirement(
                key="aws_secret_access_key",
                description="AWS secret access key",
                env_var="AWS_SECRET_ACCESS_KEY",
                required=True,
                auth_type="api_key",
            ),
        ]

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
                "prefix": {
                    "type": "string",
                    "description": "Filter log groups by name prefix",
                },
                "limit": {
                    "type": "number",
                    "description": "Maximum number of log groups to return",
                },
            },
            "required": ["awsRegion", "awsAccessKeyId", "awsSecretAccessKey"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        try:
            aws_region = parameters["awsRegion"]
            aws_access_key_id = parameters["awsAccessKeyId"]
            aws_secret_access_key = parameters["awsSecretAccessKey"]

            if self._is_placeholder_token(aws_access_key_id) or self._is_placeholder_token(aws_secret_access_key):
                return ToolResult(success=False, output="", error="AWS credentials not configured.")

            session = boto3.Session(
                aws_access_key_id=aws_access_key_id,
                aws_secret_access_key=aws_secret_access_key,
            )
            cloudwatch = session.client("logs", region_name=aws_region)

            kwargs: Dict[str, Any] = {}
            prefix = parameters.get("prefix")
            if prefix:
                kwargs["logGroupNamePrefix"] = prefix
            limit = parameters.get("limit")
            if limit is not None:
                kwargs["limit"] = limit

            response = cloudwatch.describe_log_groups(**kwargs)

            log_groups: List[Dict[str, Any]] = []
            for lg in response.get("logGroups", []):
                log_groups.append({
                    "logGroupName": lg.get("logGroupName", ""),
                    "arn": lg.get("arn", ""),
                    "storedBytes": lg.get("storedBytes", 0),
                    "retentionInDays": lg.get("retentionInDays"),
                    "creationTime": lg.get("creationTime"),
                })

            data = {"logGroups": log_groups}
            output = json.dumps(data)
            return ToolResult(success=True, output=output, data=data)

        except Exception as e:
            error_msg = f"Failed to describe CloudWatch log groups: {str(e)}"
            return ToolResult(success=False, output="", error=error_msg)