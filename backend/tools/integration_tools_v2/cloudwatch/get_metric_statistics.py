from typing import Any, Dict
import boto3
import json
from datetime import datetime
from botocore.exceptions import ClientError, NoCredentialsError
from backend.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class CloudWatchGetMetricStatisticsTool(BaseTool):
    name = "cloudwatch_get_metric_statistics"
    description = "Get statistics for a CloudWatch metric over a time range"
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
                "namespace": {
                    "type": "string",
                    "description": "Metric namespace (e.g., AWS/EC2, AWS/Lambda)",
                },
                "metricName": {
                    "type": "string",
                    "description": "Metric name (e.g., CPUUtilization, Invocations)",
                },
                "startTime": {
                    "type": "number",
                    "description": "Start time as Unix epoch seconds",
                },
                "endTime": {
                    "type": "number",
                    "description": "End time as Unix epoch seconds",
                },
                "period": {
                    "type": "number",
                    "description": "Granularity in seconds (e.g., 60, 300, 3600)",
                },
                "statistics": {
                    "type": "array",
                    "items": {
                        "type": "string"
                    },
                    "description": "Statistics to retrieve (Average, Sum, Minimum, Maximum, SampleCount)",
                },
                "dimensions": {
                    "type": "string",
                    "description": "Dimensions as JSON (e.g., {\"InstanceId\": \"i-1234\"})",
                },
            },
            "required": [
                "awsRegion",
                "awsAccessKeyId",
                "awsSecretAccessKey",
                "namespace",
                "metricName",
                "startTime",
                "endTime",
                "period",
                "statistics",
            ],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        try:
            aws_region = parameters["awsRegion"]
            access_key_id = parameters["awsAccessKeyId"]
            secret_access_key = parameters["awsSecretAccessKey"]
            namespace = parameters["namespace"]
            metric_name = parameters["metricName"]
            start_time = parameters["startTime"]
            end_time = parameters["endTime"]
            period = parameters["period"]
            statistics = parameters["statistics"]

            if self._is_placeholder_token(access_key_id) or self._is_placeholder_token(secret_access_key):
                return ToolResult(success=False, output="", error="AWS credentials not configured.")

            client = boto3.client(
                "cloudwatch",
                region_name=aws_region,
                aws_access_key_id=access_key_id,
                aws_secret_access_key=secret_access_key,
            )

            dimensions = None
            if parameters.get("dimensions"):
                dims_str = parameters["dimensions"]
                dims = json.loads(dims_str)
                if isinstance(dims, list):
                    parsed_dimensions = [
                        {
                            "Name": d["name"],
                            "Value": d["value"],
                        }
                        for d in dims
                    ]
                elif isinstance(dims, dict):
                    parsed_dimensions = [
                        {
                            "Name": name,
                            "Value": str(value),
                        }
                        for name, value in dims.items()
                    ]
                else:
                    raise ValueError("Invalid dimensions format")
                dimensions = parsed_dimensions

            kwargs: Dict[str, Any] = {
                "Namespace": namespace,
                "MetricName": metric_name,
                "StartTime": datetime.fromtimestamp(start_time),
                "EndTime": datetime.fromtimestamp(end_time),
                "Period": period,
                "Statistics": statistics,
            }
            if dimensions is not None:
                kwargs["Dimensions"] = dimensions

            response = client.get_metric_statistics(**kwargs)

            datapoints_raw = response.get("Datapoints", [])
            datapoints_raw.sort(key=lambda dp: dp["Timestamp"])

            datapoints = []
            for dp in datapoints_raw:
                datapoints.append(
                    {
                        "timestamp": int(dp["Timestamp"].timestamp()),
                        "average": dp.get("Average"),
                        "sum": dp.get("Sum"),
                        "minimum": dp.get("Minimum"),
                        "maximum": dp.get("Maximum"),
                        "sampleCount": dp.get("SampleCount"),
                        "unit": dp.get("Unit"),
                    }
                )

            output_data = {
                "label": response.get("Label", metric_name),
                "datapoints": datapoints,
            }

            return ToolResult(
                success=True,
                output=json.dumps(output_data),
                data=output_data,
            )

        except json.JSONDecodeError:
            return ToolResult(success=False, output="", error="Invalid dimensions JSON")
        except (ClientError, NoCredentialsError) as e:
            error_msg = str(e)
            if hasattr(e, "response") and e.response.get("Error"):
                error_msg = e.response["Error"].get("Message", str(e))
            return ToolResult(success=False, output="", error=error_msg)
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")