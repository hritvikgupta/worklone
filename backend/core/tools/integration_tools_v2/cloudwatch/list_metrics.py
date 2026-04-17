from typing import Any, Dict, List, Optional
import httpx
import hashlib
import hmac
import urllib.parse
import json
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class CloudWatchListMetricsTool(BaseTool):
    name = "cloudwatch_list_metrics"
    description = "List available CloudWatch metrics"
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> List[CredentialRequirement]:
        return []

    def get_schema(self) -> Dict:
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
                "namespace": {
                    "type": "string",
                    "description": "Filter by namespace (e.g., AWS/EC2, AWS/Lambda)",
                },
                "metricName": {
                    "type": "string",
                    "description": "Filter by metric name",
                },
                "recentlyActive": {
                    "type": "boolean",
                    "description": "Only show metrics active in the last 3 hours",
                },
                "limit": {
                    "type": "number",
                    "description": "Maximum number of metrics to return",
                },
            },
            "required": ["awsRegion", "awsAccessKeyId", "awsSecretAccessKey"],
        }

    def _parse_metrics(self, xml_text: str, limit: Optional[int]) -> List[Dict]:
        try:
            root = ET.fromstring(xml_text)
            ns = {"ns": "http://monitoring.amazonaws.com/doc/2010-08-01/"}
            metrics = []
            metrics_elem = root.find(".//ns:Metrics", ns)
            if metrics_elem is None:
                return []
            for member in metrics_elem.findall("ns:member", ns):
                metric = {"namespace": "", "metricName": "", "dimensions": []}
                ns_elem = member.find("ns:Namespace", ns)
                if ns_elem is not None:
                    metric["namespace"] = ns_elem.text or ""
                mn_elem = member.find("ns:MetricName", ns)
                if mn_elem is not None:
                    metric["metricName"] = mn_elem.text or ""
                dims_elem = member.find("ns:Dimensions", ns)
                if dims_elem is not None:
                    for dmember in dims_elem.findall("ns:member", ns):
                        dim = {"name": "", "value": ""}
                        name_elem = dmember.find("ns:Name", ns)
                        if name_elem is not None:
                            dim["name"] = name_elem.text or ""
                        value_elem = dmember.find("ns:Value", ns)
                        if value_elem is not None:
                            dim["value"] = value_elem.text or ""
                        if dim["name"]:
                            metric["dimensions"].append(dim)
                metrics.append(metric)
            if limit is not None:
                metrics = metrics[:limit]
            return metrics
        except Exception:
            return []

    async def execute(self, parameters: Dict, context: Dict = None) -> ToolResult:
        aws_region = parameters.get("awsRegion")
        access_key_id = parameters.get("awsAccessKeyId")
        secret_access_key = parameters.get("awsSecretAccessKey")
        if not all([aws_region, access_key_id, secret_access_key]):
            return ToolResult(success=False, output="", error="Missing required AWS credentials or region.")
        if self._is_placeholder_token(access_key_id) or self._is_placeholder_token(secret_access_key):
            return ToolResult(success=False, output="", error="AWS credentials not configured.")
        namespace = parameters.get("namespace")
        metric_name = parameters.get("metricName")
        recently_active = parameters.get("recentlyActive")
        limit = parameters.get("limit")
        if limit is not None:
            limit = int(limit)
        service = "monitoring"
        url = f"https://monitoring.{aws_region}.amazonaws.com/"
        body_params = {
            "Action": "ListMetrics",
            "Version": "2010-08-01",
        }
        if namespace:
            body_params["Namespace"] = namespace
        if metric_name:
            body_params["MetricName"] = metric_name
        if recently_active:
            body_params["RecentlyActive"] = "PT3H"
        max_results = min(limit, 500) if limit is not None else 500
        body_params["MaxResults"] = str(max_results)
        body = urllib.parse.urlencode(body_params)
        now = datetime.now(timezone.utc)
        amz_date = now.strftime("%Y%m%dT%H%M%SZ")
        date_stamp = now.strftime("%Y%m%d")
        headers = {
            "content-type": "application/x-www-form-urlencoded; charset=utf-8",
            "host": f"monitoring.{aws_region}.amazonaws.com",
            "X-Amz-Date": amz_date,
        }
        keys = sorted(headers.keys(), key=str.lower)
        canonical_header_lines = [f"{key.lower()}:{headers[key].strip()}\n" for key in keys]
        canonical_headers = "".join(canonical_header_lines)
        signed_headers = ";".join(key.lower() for key in keys)
        canonical_uri = "/"
        canonical_querystring = ""
        payload_hash = hashlib.sha256(body.encode("utf-8")).hexdigest()
        canonical_request = f"POST\n{canonical_uri}\n{canonical_querystring}\n{canonical_headers}{signed_headers}\n{payload_hash}"
        algorithm = "AWS4-HMAC-SHA256"
        credential_scope = f"{date_stamp}/{aws_region}/{service}/aws4_request"
        cr_hash = hashlib.sha256(canonical_request.encode("utf-8")).hexdigest()
        string_to_sign = f"{algorithm}\n{amz_date}\n{credential_scope}\n{cr_hash}"
        k_date = hmac.new(("AWS4" + secret_access_key).encode("utf-8"), date_stamp.encode("utf-8"), hashlib.sha256).digest()
        k_region = hmac.new(k_date, aws_region.encode("utf-8"), hashlib.sha256).digest()
        k_service = hmac.new(k_region, service.encode("utf-8"), hashlib.sha256).digest()
        signing_key = hmac.new(k_service, b"aws4_request", hashlib.sha256).digest()
        signature = hmac.new(signing_key, string_to_sign.encode("utf-8"), hashlib.sha256).hexdigest()
        headers["Authorization"] = f"{algorithm} Credential={access_key_id}/{credential_scope},SignedHeaders={signed_headers},Signature={signature}"
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, content=body)
                if response.status_code == 200:
                    metrics = self._parse_metrics(response.text, limit)
                    output_data = {"metrics": metrics}
                    return ToolResult(success=True, output=json.dumps(output_data), data=output_data)
                else:
                    return ToolResult(success=False, output="", error=response.text)
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")