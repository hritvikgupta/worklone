import boto3
import json
import urllib.parse
from typing import Any, Dict
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class S3CopyObjectTool(BaseTool):
    name = "S3 Copy Object"
    description = "Copy an object within or between AWS S3 buckets"
    category = "integration"

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return []

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
                "sourceBucket": {
                    "type": "string",
                    "description": "Source bucket name (e.g., my-bucket)",
                },
                "sourceKey": {
                    "type": "string",
                    "description": "Source object key/path (e.g., folder/file.txt)",
                },
                "destinationBucket": {
                    "type": "string",
                    "description": "Destination bucket name (e.g., my-other-bucket)",
                },
                "destinationKey": {
                    "type": "string",
                    "description": "Destination object key/path (e.g., backup/file.txt)",
                },
                "acl": {
                    "type": "string",
                    "description": "Access control list for the copied object (e.g., private, public-read)",
                },
            },
            "required": [
                "accessKeyId",
                "secretAccessKey",
                "region",
                "sourceBucket",
                "sourceKey",
                "destinationBucket",
                "destinationKey",
            ],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        try:
            access_key_id = parameters["accessKeyId"]
            secret_access_key = parameters["secretAccessKey"]
            region = parameters["region"]
            source_bucket = parameters["sourceBucket"]
            source_key = parameters["sourceKey"]
            destination_bucket = parameters["destinationBucket"]
            destination_key = parameters["destinationKey"]
            acl = parameters.get("acl")

            s3_client = boto3.client(
                "s3",
                region_name=region,
                aws_access_key_id=access_key_id,
                aws_secret_access_key=secret_access_key,
            )

            encoded_source_key_parts = [
                urllib.parse.quote(part, safe="~-._") for part in source_key.split("/")
            ]
            encoded_source_key = "/".join(encoded_source_key_parts)
            copy_source = f"{source_bucket}/{encoded_source_key}"

            result = s3_client.copy_object(
                Bucket=destination_bucket,
                Key=destination_key,
                CopySource=copy_source,
                ACL=acl,
            )

            encoded_dest_key_parts = [
                urllib.parse.quote(part, safe="~-._") for part in destination_key.split("/")
            ]
            encoded_dest_key = "/".join(encoded_dest_key_parts)
            url = f"https://{destination_bucket}.s3.{region}.amazonaws.com/{encoded_dest_key}"
            uri = f"s3://{destination_bucket}/{destination_key}"

            metadata = {
                "copySourceVersionId": result.get("CopySourceVersionId"),
                "versionId": result.get("VersionId"),
                "etag": result.get("CopyObjectResult", {}).get("ETag"),
            }

            data: Dict[str, Any] = {
                "url": url,
                "uri": uri,
                "metadata": metadata,
            }

            output_str = json.dumps(data)

            return ToolResult(success=True, output=output_str, data=data)

        except KeyError as e:
            return ToolResult(
                success=False, output="", error=f"Missing required parameter: {str(e)}"
            )
        except Exception as e:
            return ToolResult(
                success=False, output="", error=f"S3 API error: {str(e)}"
            )