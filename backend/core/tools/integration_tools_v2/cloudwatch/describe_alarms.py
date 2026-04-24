from typing import Any, Dict
import json
try:
    import boto3
except ImportError:
    boto3 = None
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class CloudWatchDescribeAlarmsTool(BaseTool):
    name = "cloudwatch_describe_alarms"
    description = "List and filter CloudWatch alarms"
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
                "alarmNamePrefix": {
                    "type": "string",
                    "description": "Filter alarms by name prefix",
                },
                "stateValue": {
                    "type": "string",
                    "description": "Filter by alarm state (OK, ALARM, INSUFFICIENT_DATA)",
                },
                "alarmType": {
                    "type": "string",
                    "description": "Filter by alarm type (MetricAlarm, CompositeAlarm)",
                },
                "limit": {
                    "type": "number",
                    "description": "Maximum number of alarms to return",
                },
            },
            "required": ["awsRegion", "awsAccessKeyId", "awsSecretAccessKey"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        if boto3 is None:
            return ToolResult(success=False, output="", error="boto3 is not installed. Install it to use AWS tools.")

        aws_region = parameters["awsRegion"]
        aws_access_key_id = parameters["awsAccessKeyId"]
        aws_secret_access_key = parameters["awsSecretAccessKey"]

        if self._is_placeholder_token(aws_access_key_id) or self._is_placeholder_token(aws_secret_access_key):
            return ToolResult(success=False, output="", error="AWS credentials not configured.")

        client = boto3.client(
            "cloudwatch",
            region_name=aws_region,
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
        )

        describe_kwargs: Dict[str, Any] = {}
        alarm_name_prefix = parameters.get("alarmNamePrefix")
        if alarm_name_prefix:
            describe_kwargs["AlarmNamePrefix"] = alarm_name_prefix
        state_value = parameters.get("stateValue")
        if state_value:
            describe_kwargs["StateValue"] = state_value
        alarm_type = parameters.get("alarmType")
        if alarm_type:
            describe_kwargs["AlarmTypes"] = [alarm_type]
        limit = parameters.get("limit")
        if limit is not None:
            describe_kwargs["MaxRecords"] = int(limit)

        try:
            response = client.describe_alarms(**describe_kwargs)

            metric_alarms = []
            for alarm in response.get("MetricAlarms", []):
                state_updated_timestamp = None
                if alarm.get("StateUpdatedTimestamp"):
                    state_updated_timestamp = int(alarm["StateUpdatedTimestamp"].timestamp() * 1000)
                metric_alarms.append({
                    "alarmName": alarm.get("AlarmName", ""),
                    "alarmArn": alarm.get("AlarmArn", ""),
                    "stateValue": alarm.get("StateValue", "UNKNOWN"),
                    "stateReason": alarm.get("StateReason", ""),
                    "metricName": alarm.get("MetricName"),
                    "namespace": alarm.get("Namespace"),
                    "comparisonOperator": alarm.get("ComparisonOperator"),
                    "threshold": alarm.get("Threshold"),
                    "evaluationPeriods": alarm.get("EvaluationPeriods"),
                    "stateUpdatedTimestamp": state_updated_timestamp,
                })

            composite_alarms = []
            for alarm in response.get("CompositeAlarms", []):
                state_updated_timestamp = None
                if alarm.get("StateUpdatedTimestamp"):
                    state_updated_timestamp = int(alarm["StateUpdatedTimestamp"].timestamp() * 1000)
                composite_alarms.append({
                    "alarmName": alarm.get("AlarmName", ""),
                    "alarmArn": alarm.get("AlarmArn", ""),
                    "stateValue": alarm.get("StateValue", "UNKNOWN"),
                    "stateReason": alarm.get("StateReason", ""),
                    "metricName": None,
                    "namespace": None,
                    "comparisonOperator": None,
                    "threshold": None,
                    "evaluationPeriods": None,
                    "stateUpdatedTimestamp": state_updated_timestamp,
                })

            alarms = metric_alarms + composite_alarms
            result_data = {"alarms": alarms}
            return ToolResult(
                success=True,
                output=json.dumps(result_data),
                data=result_data
            )
        except Exception as e:
            error_msg = f"Failed to describe CloudWatch alarms: {str(e)}"
            return ToolResult(success=False, output="", error=error_msg)
