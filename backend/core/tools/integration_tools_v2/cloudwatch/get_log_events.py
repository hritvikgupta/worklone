import json
import boto3
from botocore.exceptions import ClientError, NoCredentialsError, BotoCoreError
from typing import Dict, Any
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class CloudWatchGetLogEventsTool(BaseTool):
    name = "cloudwatch_get_log_events"
    description = "Retrieve log events from a specific CloudWatch log stream"
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
                "logStreamName": {
                    "type": "string",
                    "description": "CloudWatch log stream name",
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
                    "description": "Maximum number of events to return",
                },
            },
            "required": ["awsRegion", "awsAccessKeyId", "awsSecretAccessKey", "logGroupName", "logStreamName"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        try:
            aws_region = parameters["awsRegion"]
            access_key_id = parameters["awsAccessKeyId"]
            secret_access_key = parameters["awsSecretAccessKey"]
            log_group_name = parameters["logGroupName"]
            log_stream_name = parameters["logStreamName"]

            if self._is_placeholder_token(access_key_id) or self._is_placeholder_token(secret_access_key):
                return ToolResult(success=False, output="", error="AWS credentials not configured.")

            api_params: Dict[str, Any] = {
                "logGroupName": log_group_name,
                "logStreamName": log_stream_name,
            }
            if "startTime" in parameters and parameters["startTime"] is not None:
                api_params["startTime"] = parameters["startTime"]
            if "endTime" in parameters and parameters["endTime"] is not None:
                api_params["endTime"] = parameters["endTime"]
            if "limit" in parameters and parameters["limit"] is not None:
                api_params["limit"] = parameters["limit"]

            client = boto3.client(
                "logs",
                region_name=aws_region,
                aws_access_key_id=access_key_id,
                aws_secret_access_key=secret_access_key,
            )

            response = client.get_log_events(**api_params)

            data = {"events": response.get("events", [])}
            output = json.dumps(data)

            return ToolResult(success=True, output=output, data=data)

        except (ClientError, NoCredentialsError, BotoCoreError) as e:
            error_msg = str(e)
            return ToolResult(success=False, output="", error=error_msg)
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")