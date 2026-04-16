from typing import Any, Dict, List, Optional, Tuple
import httpx
import base64
import os
import hashlib
import hmac
import json
from datetime import datetime
from urllib.parse import urlparse, quote
from backend.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class S3GetObjectTool(BaseTool):
    name = "s3_get_object"
    description = "Retrieve an object from an AWS S3 bucket"
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> List[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="access_key_id",
                description="Your AWS Access Key ID",
                env_var="AWS_ACCESS_KEY_ID",
                required=True,
                auth_type="api_key",
            ),
            CredentialRequirement(
                key="secret_access_key",
                description="Your AWS Secret Access Key",
                env_var="AWS_SECRET_ACCESS_KEY",
                required=True,
                auth_type="api_key",
            ),
            CredentialRequirement(
                key="region",
                description="Optional region override when URL does not include region (e.g., us-east-1, eu-west-1)",
                env_var="AWS_REGION",
                required=False,
                auth_type="api_key",
            ),
        ]

    def _get_credential(self, context: Optional[Dict], key: str, env_var: str, required: bool = True) -> Optional[str]:
        value = context.get(key) if context else None
        if value is None:
            value = os.getenv(env_var)
        normalized = (value or "").strip().lower()
        if required and (not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized.startswith("ya29.")):
            return None
        return value

    def _encode_s3_path_component(self, key: str) -> str:
        return quote(key, safe="/~")

    def _parse_s3_uri(self, s3_uri: str, region_override: Optional[str] = None) -> Tuple[str, str, str]:
        if s3_uri.startswith("s3://"):
            s3_path = s3_uri[5:]
            slash_pos = s3_path.find("/")
            if slash_pos == -1:
                raise ValueError("Invalid s3 URI: no object key specified")
            bucket = s3_path[:slash_pos]
            object_key = s3_path[slash_pos + 1 :]
            region = region_override
            if not region:
                raise ValueError("Region required for s3:// URI")
            return bucket, region, object_key
        parsed = urlparse(s3_uri)
        if parsed.scheme != "https":
            raise ValueError("Only https:// or s3:// S3 URIs are supported")
        hostname = parsed.hostname
        if not hostname or not hostname.endswith("amazonaws.com"):
            raise ValueError("Invalid S3 hostname")
        if ".s3.amazonaws.com" in hostname:
            s3_pos = hostname.find(".s3.amazonaws.com")
            bucket = hostname[:s3_pos]
            region = region_override
        elif ".s3." in hostname:
            s3_pos = hostname.find(".s3.")
            bucket = hostname[:s3_pos]
            rest = hostname[s3_pos + 4 :]
            amz_pos = rest.find(".amazonaws.com")
            if amz_pos == -1:
                raise ValueError("Invalid region in S3 hostname")
            region = rest[:amz_pos]
        else:
            raise ValueError("Invalid S3 URL format")
        object_key = parsed.path.lstrip("/")
        region = region or region_override
        if not region:
            raise ValueError("Region not specified in URL or provided")
        return bucket, region, object_key

    def _get_signature_key(self, key: str, date_stamp: str, region_name: str, service_name: str) -> bytes:
        k_date = hmac.new(("AWS4" + key).encode("utf-8"), date_stamp.encode("utf-8"), hashlib.sha256).digest()
        k_region = hmac.new(k_date, region_name.encode("utf-8"), hashlib.sha256).digest()
        k_service = hmac.new(k_region, service_name.encode("utf-8"), hashlib.sha256).digest()
        k_signing = hmac.new(k_service, b"aws4_request", hashlib.sha256).digest()
        return k_signing

    def _get_s3_headers(
        self, method: str, bucket: str, region: str, object_key: str, access_key: str, secret_key: str
    ) -> Dict[str, str]:
        now = datetime.utcnow()
        amz_date = now.strftime("%Y%m%dT%H%M%SZ")
        date_stamp = amz_date[:8]
        payload_hash = hashlib.sha256(b"").hexdigest()
        host = f"{bucket}.s3.{region}.amazonaws.com".lower()
        encoded_path = self._encode_s3_path_component(object_key)
        canonical_uri = f"/{encoded_path}"
        canonical_query_string = ""
        canonical_headers = (
            f"host:{host}\n"
            f"x-amz-content-sha256:{payload_hash}\n"
            f"x-amz-date:{amz_date}\n"
        )
        signed_headers = "host;x-amz-content-sha256;x-amz-date"
        canonical_request = (
            f"{method}\n"
            f"{canonical_uri}\n"
            f"{canonical_query_string}\n"
            f"{canonical_headers}\n"
            f"{signed_headers}\n"
            f"{payload_hash}"
        )
        cr_hash = hashlib.sha256(canonical_request.encode("utf-8")).hexdigest()
        algorithm = "AWS4-HMAC-SHA256"
        credential_scope = f"{date_stamp}/{region}/s3/aws4_request"
        string_to_sign = (
            f"{algorithm}\n"
            f"{amz_date}\n"
            f"{credential_scope}\n"
            f"{cr_hash}"
        )
        signing_key = self._get_signature_key(secret_key, date_stamp, region, "s3")
        signature = hmac.new(signing_key, string_to_sign.encode("utf-8"), hashlib.sha256).hexdigest()
        authorization_header = (
            f"{algorithm} "
            f"Credential={access_key}/{credential_scope}, "
            f"SignedHeaders={signed_headers}, "
            f"Signature={signature}"
        )
        return {
            "Host": host,
            "X-Amz-Content-Sha256": payload_hash,
            "X-Amz-Date": amz_date,
            "Authorization": authorization_header,
        }

    def _generate_presigned_url(
        self, access_key: str, secret_key: str, region: str, bucket: str, object_key: str, expires_in: int = 3600
    ) -> str:
        now = datetime.utcnow()
        amz_date = now.strftime("%Y%m%dT%H%M%SZ")
        date_stamp = amz_date[:8]
        payload_hash = hashlib.sha256(b"").hexdigest()
        host = f"{bucket}.s3.{region}.amazonaws.com".lower()
        canonical_uri = f"/{self._encode_s3_path_component(object_key)}"
        query_params = {
            "X-Amz-Algorithm": "AWS4-HMAC-SHA256",
            "X-Amz-Credential": f"{access_key}/{date_stamp}/{region}/s3/aws4_request",
            "X-Amz-Date": amz_date,
            "X-Amz-Expires": str(expires_in),
            "X-Amz-SignedHeaders": "host;x-amz-content-sha256",
        }
        sorted_query = sorted(query_params.items())
        canonical_query_string = "&".join(f"{quote(k, safe='~')}={quote(v, safe='~')}" for k, v in sorted_query)
        canonical_headers = f"host:{host}\nx-amz-content-sha256:{payload_hash}\n"
        signed_headers = "host;x-amz-content-sha256"
        canonical_request = (
            "GET\n"
            f"{canonical_uri}\n"
            f"{canonical_query_string}\n"
            f"{canonical_headers}\n"
            f"{signed_headers}\n"
            f"{payload_hash}"
        )
        cr_hash = hashlib.sha256(canonical_request.encode("utf-8")).hexdigest()
        algorithm = "AWS4-HMAC-SHA256"
        credential_scope = f"{date_stamp}/{region}/s3/aws4_request"
        string_to_sign = (
            f"{algorithm}\n"
            f"{amz_date}\n"
            f"{credential_scope}\n"
            f"{cr_hash}"
        )
        signing_key = self._get_signature_key(secret_key, date_stamp, region, "s3")
        signature = hmac.new(signing_key, string_to_sign.encode("utf-8"), hashlib.sha256).hexdigest()
        query_params["X-Amz-Signature"] = signature
        full_query_items = sorted(query_params.items())
        full_query_string = "&".join(f"{quote(k, safe='~')}={quote(v, safe='~')}" for k, v in full_query_items)
        return f"https://{host}{canonical_uri}?{full_query_string}"

    def get_schema(self) -> Dict:
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
                    "description": "Optional region override when URL does not include region (e.g., us-east-1, eu-west-1)",
                },
                "s3Uri": {
                    "type": "string",
                    "description": "S3 Object URL (e.g., https://bucket.s3.region.amazonaws.com/path/to/file)",
                },
            },
            "required": ["accessKeyId", "secretAccessKey", "s3Uri"],
        }

    async def execute(self, parameters: Dict, context: Optional[Dict] = None) -> ToolResult:
        access_key_id = self._get_credential(context, "access_key_id", "AWS_ACCESS_KEY_ID", required=True)
        secret_access_key = self._get_credential(context, "secret_access_key", "AWS_SECRET_ACCESS_KEY", required=True)
        if access_key_id is None or secret_access_key is None:
            return ToolResult(success=False, output="", error="AWS Access Key ID or Secret Access Key not configured.")
        region_cred = self._get_credential(context, "region", "AWS_REGION", required=False)
        s3_uri = parameters.get("s3Uri")
        if not s3_uri:
            return ToolResult(success=False, output="", error="s3Uri is required.")
        region_param = parameters.get("region")
        region = region_param or region_cred
        try:
            bucket_name, region, object_key = self._parse_s3_uri(s3_uri, region)
        except ValueError as e:
            return ToolResult(success=False, output="", error=str(e))
        url = f"https://{bucket_name}.s3.{region}.amazonaws.com/{self._encode_s3_path_component(object_key)}"
        headers = self._get_s3_headers("GET", bucket_name, region, object_key, access_key_id, secret_access_key)
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers)
                if response.status_code == 200:
                    content_type = response.headers.get("content-type", "application/octet-stream")
                    last_modified = response.headers.get("last-modified", datetime.utcnow().isoformat())
                    file_name = object_key.split("/")[-1] if "/" in object_key else object_key
                    content = response.content
                    b64_data = base64.b64encode(content).decode("utf-8")
                    size = len(content)
                    presigned_url = self._generate_presigned_url(access_key_id, secret_access_key, region, bucket_name, object_key, 3600)
                    result = {
                        "url": presigned_url,
                        "file": {
                            "name": file_name,
                            "mimeType": content_type,
                            "data": b64_data,
                            "size": size,
                        },
                        "metadata": {
                            "fileType": content_type,
                            "size": size,
                            "name": file_name,
                            "lastModified": last_modified,
                        },
                    }
                    return ToolResult(success=True, output=json.dumps(result), data=result)
                else:
                    error_text = response.text
                    return ToolResult(
                        success=False,
                        output="",
                        error=f"Failed to download S3 object: {response.status_code} {response.reason_phrase} {error_text}",
                    )
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")