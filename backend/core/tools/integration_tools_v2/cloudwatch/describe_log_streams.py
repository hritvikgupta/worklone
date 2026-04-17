from typing import Any, Dict
import json
import boto3
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class CloudWatchDescribeLogStreamsTool(BaseTool):
    name = "CloudWatch Describe Log Streams"
    description = "List log streams within a CloudWatch log group"
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="aws_access_key_id",
                description="AWS Access Key ID",
                env_var="AWS_ACCESS_KEY_ID",
                required=True,
                auth_type="api_key",
            ),
            CredentialRequirement(
                key="aws_secret_access_key",
                description="AWS Secret Access Key",
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
                "logGroupName": {
                    "type": "string",
                    "description": "CloudWatch log group name",
                },
                "prefix": {
                    "type": "string",
                    "description": "Filter log streams by name prefix",
                },
                "limit": {
                    "type": "number",
                    "description": "Maximum number of log streams to return",
                },
            },
            "required": ["awsRegion", "awsAccessKeyId", "awsSecretAccessKey", "logGroupName"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        try:
            aws_region = parameters["awsRegion"]
            access_key_id = parameters["awsAccessKeyId"]
            secret_access_key = parameters["awsSecretAccessKey"]
            log_group_name = parameters["logGroupName"]
            prefix = parameters.get("prefix")
            limit = parameters.get("limit")

            if self._is_placeholder_token(access_key_id) or self._is_placeholder_token(secret_access_key):
                return ToolResult(success=False, output="", error="AWS credentials not configured.")

            client = boto3.client(
                "logs",
                region_name=aws_region,
                aws_access_key_id=access_key_id,
                aws_secret_access_key=secret_access_key,
            )

            kwargs: Dict[str, Any] = {"logGroupName": log_group_name}
            if prefix:
                kwargs["logStreamNamePrefix"] = prefix
            if limit is not None:
                kwargs["limit"] = int(limit)

            response = client.describe_log_streams(**kwargs)
            data = {"logStreams": response.get("logStreams", [])}
            return ToolResult(success=True, output=json.dumps(data), data=data)

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")