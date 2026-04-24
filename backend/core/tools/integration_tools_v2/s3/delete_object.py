import os
try:
    import boto3
except ImportError:
    boto3 = None
from typing import Dict, Any
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class S3DeleteObjectTool(BaseTool):
    name = "s3_delete_object"
    description = "Delete an object from an AWS S3 bucket"
    category = "integration"

    @staticmethod
    def _is_placeholder_value(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized.startswith("ya29.")

    def _resolve_credential(self, context: dict | None, cred_key: str, env_key: str) -> str | None:
        value = context.get(cred_key) if context else None
        if value is None:
            value = os.getenv(env_key)
        return value

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
                env_var="AWS_DEFAULT_REGION",
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
                "objectKey": {
                    "type": "string",
                    "description": "Object key/path to delete (e.g., folder/file.txt)",
                },
            },
            "required": ["accessKeyId", "secretAccessKey", "region", "bucketName", "objectKey"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        if boto3 is None:
            return ToolResult(success=False, output="", error="boto3 is not installed. Install it to use AWS tools.")

        access_key_id = self._resolve_credential(context, "accessKeyId", "AWS_ACCESS_KEY_ID")
        secret_access_key = self._resolve_credential(context, "secretAccessKey", "AWS_SECRET_ACCESS_KEY")
        region = self._resolve_credential(context, "region", "AWS_DEFAULT_REGION")

        if not all([access_key_id, secret_access_key, region]):
            return ToolResult(success=False, output="", error="AWS credentials not configured.")

        if (
            self._is_placeholder_value(access_key_id)
            or self._is_placeholder_value(secret_access_key)
            or self._is_placeholder_value(region)
        ):
            return ToolResult(success=False, output="", error="AWS credentials not configured.")

        bucket_name = parameters.get("bucketName")
        object_key = parameters.get("objectKey")

        if not bucket_name or not object_key:
            return ToolResult(success=False, output="", error="Missing required parameters: bucketName and/or objectKey.")

        try:
            s3_client = boto3.client(
                "s3",
                aws_access_key_id=access_key_id,
                aws_secret_access_key=secret_access_key,
                region_name=region,
            )
            result = s3_client.delete_object(Bucket=bucket_name, Key=object_key)

            metadata = {
                "key": object_key,
                "deleteMarker": result.get("DeleteMarker"),
                "versionId": result.get("VersionId"),
            }
            data = {
                "deleted": True,
                "metadata": metadata,
            }
            return ToolResult(success=True, output="Object deleted successfully.", data=data)

        except Exception as e:
            return ToolResult(success=False, output="", error=f"S3 delete error: {str(e)}")
