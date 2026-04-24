from typing import Any, Dict
try:
    import boto3
except ImportError:
    boto3 = None
import json
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class S3ListObjectsTool(BaseTool):
    name = "s3_list_objects"
    description = "List objects in an AWS S3 bucket"
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="accessKeyId",
                description="Your AWS Access Key ID",
                env_var="AWS_ACCESS_KEY_ID",
                required=True,
                auth_type="api_key",
            ),
            CredentialRequirement(
                key="secretAccessKey",
                description="Your AWS Secret Access Key",
                env_var="AWS_SECRET_ACCESS_KEY",
                required=True,
                auth_type="api_key",
            ),
            CredentialRequirement(
                key="region",
                description="AWS region (e.g., us-east-1)",
                env_var="AWS_REGION",
                required=True,
                auth_type="api_key",
            ),
        ]

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "accessKeyId": {
                    "type": "string",
                    "description": "Your AWS Access Key ID",
                },
                "secretAccessKey": {
                    "type": "string",
                    "description": "Your AWS Secret Access Key",
                },
                "region": {
                    "type": "string",
                    "description": "AWS region (e.g., us-east-1)",
                },
                "bucketName": {
                    "type": "string",
                    "description": "S3 bucket name (e.g., my-bucket)",
                },
                "prefix": {
                    "type": "string",
                    "description": "Prefix to filter objects (e.g., folder/, images/2024/)",
                },
                "maxKeys": {
                    "type": "number",
                    "description": "Maximum number of objects to return (default: 1000)",
                },
                "continuationToken": {
                    "type": "string",
                    "description": "Token for pagination from previous list response",
                },
            },
            "required": ["accessKeyId", "secretAccessKey", "region", "bucketName"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        if boto3 is None:
            return ToolResult(success=False, output="", error="boto3 is not installed. Install it to use AWS tools.")

        access_key_id = (parameters.get("accessKeyId") or "").strip()
        secret_access_key = (parameters.get("secretAccessKey") or "").strip()
        region = (parameters.get("region") or "").strip()
        bucket_name = parameters.get("bucketName", "")
        prefix = parameters.get("prefix")
        max_keys = parameters.get("maxKeys")
        continuation_token = parameters.get("continuationToken")

        if self._is_placeholder_token(access_key_id) or self._is_placeholder_token(secret_access_key):
            return ToolResult(success=False, output="", error="AWS credentials not configured.")

        if not all([access_key_id, secret_access_key, region, bucket_name]):
            return ToolResult(success=False, output="", error="Missing required AWS credentials or bucket name.")

        try:
            s3_client = boto3.client(
                "s3",
                aws_access_key_id=access_key_id,
                aws_secret_access_key=secret_access_key,
                region_name=region,
            )

            list_kwargs = {"Bucket": bucket_name}
            if prefix:
                list_kwargs["Prefix"] = prefix
            if max_keys is not None:
                list_kwargs["MaxKeys"] = int(max_keys)
            if continuation_token:
                list_kwargs["ContinuationToken"] = continuation_token

            response = s3_client.list_objects_v2(**list_kwargs)

            objects = []
            if "Contents" in response:
                for obj in response["Contents"]:
                    objects.append({
                        "key": obj.get("Key", ""),
                        "size": obj.get("Size", 0),
                        "lastModified": obj["LastModified"].isoformat() if "LastModified" in obj and obj["LastModified"] else "",
                        "etag": obj.get("ETag", ""),
                    })

            output_data = {
                "objects": objects,
                "metadata": {
                    "isTruncated": response.get("IsTruncated", False),
                    "nextContinuationToken": response.get("NextContinuationToken"),
                    "keyCount": response.get("KeyCount"),
                    "prefix": prefix or "",
                },
            }

            return ToolResult(success=True, output=json.dumps(output_data), data=output_data)

        except Exception as e:
            return ToolResult(success=False, output="", error=f"S3 API error: {str(e)}")
