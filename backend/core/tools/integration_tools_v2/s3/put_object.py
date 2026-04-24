from typing import Any, Dict
import base64
import json
import urllib.parse
try:
    import boto3
except ImportError:
    boto3 = None
try:
    from botocore.exceptions import ClientError, NoCredentialsError
except ImportError:
    ClientError = Exception
    NoCredentialsError = Exception
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class S3PutObjectTool(BaseTool):
    name = "s3_put_object"
    description = "Upload a file to an AWS S3 bucket"
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
                "bucketName": {
                    "type": "string",
                    "description": "S3 bucket name (e.g., my-bucket)",
                },
                "objectKey": {
                    "type": "string",
                    "description": "Object key/path in S3 (e.g., folder/filename.ext)",
                },
                "file": {
                    "type": "object",
                    "properties": {
                        "name": {
                            "type": "string",
                            "description": "File name",
                        },
                        "content": {
                            "type": "string",
                            "description": "Base64 encoded file content",
                        },
                        "mimeType": {
                            "type": "string",
                            "description": "MIME type of the file",
                        },
                        "type": {
                            "type": "string",
                            "description": "MIME type of the file (alternative to mimeType)",
                        },
                    },
                    "description": "File to upload",
                },
                "content": {
                    "type": "string",
                    "description": "Text content to upload (alternative to file)",
                },
                "contentType": {
                    "type": "string",
                    "description": "Content-Type header (auto-detected from file if not provided)",
                },
                "acl": {
                    "type": "string",
                    "description": "Access control list (e.g., private, public-read)",
                },
            },
            "required": ["accessKeyId", "secretAccessKey", "region", "bucketName", "objectKey"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        try:
            if boto3 is None:
                return ToolResult(success=False, output="", error="boto3 is not installed. Install it to use AWS tools.")

            access_key_id = parameters["accessKeyId"]
            secret_access_key = parameters["secretAccessKey"]
            region_name = parameters["region"]
            bucket_name = parameters["bucketName"]
            object_key = parameters["objectKey"]
            content_type = parameters.get("contentType")
            acl = parameters.get("acl")

            upload_body: bytes
            final_content_type: str

            file_info = parameters.get("file")
            if file_info:
                if not isinstance(file_info, dict):
                    raise ValueError("file must be a dictionary")
                content_b64 = file_info.get("content")
                if not content_b64:
                    raise ValueError("file.content (base64 encoded) is required when file is provided")
                upload_body = base64.b64decode(content_b64)
                file_mime = file_info.get("mimeType") or file_info.get("type")
                final_content_type = content_type or file_mime or "application/octet-stream"
            elif parameters.get("content"):
                content_str = parameters["content"]
                upload_body = content_str.encode("utf-8")
                final_content_type = content_type or "text/plain"
            else:
                raise ValueError("Either file or content must be provided")

            s3_client = boto3.client(
                "s3",
                aws_access_key_id=access_key_id,
                aws_secret_access_key=secret_access_key,
                region_name=region_name,
            )

            response = s3_client.put_object(
                Bucket=bucket_name,
                Key=object_key,
                Body=upload_body,
                ContentType=final_content_type,
                ACL=acl,
            )

            etag = response["ETag"]

            encoded_key = "/".join(urllib.parse.quote(part, safe="") for part in object_key.split("/"))
            url = f"https://{bucket_name}.s3.{region_name}.amazonaws.com/{encoded_key}"
            uri = f"s3://{bucket_name}/{object_key}"

            output_data = {
                "url": url,
                "uri": uri,
                "metadata": {
                    "etag": etag,
                    "location": url,
                    "key": object_key,
                    "bucket": bucket_name,
                },
            }

            return ToolResult(success=True, output=json.dumps(output_data), data=output_data)

        except KeyError as e:
            return ToolResult(success=False, output="", error=f"Missing required parameter: {str(e)}")
        except (ValueError, base64.binascii.Error) as e:
            return ToolResult(success=False, output="", error=f"Invalid input: {str(e)}")
        except (ClientError, NoCredentialsError) as e:
            return ToolResult(success=False, output="", error=f"AWS S3 error: {str(e)}")
        except Exception as e:
            return ToolResult(success=False, output="", error=f"Upload failed: {str(e)}")
