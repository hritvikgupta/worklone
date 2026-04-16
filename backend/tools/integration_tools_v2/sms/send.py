from typing import Any, Dict
import httpx
import base64
import os
import json
from backend.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class SmsSendTool(BaseTool):
    name = "sms_send"
    description = "Send an SMS message using the internal SMS service powered by Twilio"
    category = "integration"

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return []

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "to": {
                    "type": "string",
                    "description": "Recipient phone number (include country code, e.g., +1234567890)",
                },
                "body": {
                    "type": "string",
                    "description": "SMS message content",
                },
            },
            "required": ["to", "body"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        account_sid = os.environ.get("TWILIO_ACCOUNT_SID")
        auth_token = os.environ.get("TWILIO_AUTH_TOKEN")
        from_number = os.environ.get("TWILIO_PHONE_NUMBER")

        if not account_sid or not auth_token or not from_number:
            return ToolResult(
                success=False,
                output="",
                error="Twilio credentials or phone number not configured in environment variables.",
            )

        to_num = parameters.get("to")
        body_msg = parameters.get("body")

        if not to_num or not body_msg:
            return ToolResult(
                success=False,
                output="",
                error="Missing required parameters: to and body.",
            )

        url = f"https://api.twilio.com/2010-04-01/Accounts/{account_sid}/Messages.json"

        data = {
            "To": to_num,
            "From": from_number,
            "Body": body_msg,
        }

        auth_str = base64.b64encode(f"{account_sid}:{auth_token}".encode("utf-8")).decode("utf-8")
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Authorization": f"Basic {auth_str}",
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, data=data)

                if response.status_code == 201:
                    twilio_data = response.json()
                    output_data = {
                        "success": True,
                        "to": to_num,
                        "body": body_msg,
                    }
                    return ToolResult(
                        success=True,
                        output=json.dumps(output_data),
                        data=twilio_data,
                    )
                else:
                    error_msg = response.text
                    try:
                        err_data = response.json()
                        error_msg = err_data.get("message", str(err_data))
                    except ValueError:
                        pass
                    return ToolResult(
                        success=False,
                        output="",
                        error=f"SMS send failed: {error_msg}",
                    )
        except httpx.TimeoutException:
            return ToolResult(
                success=False,
                output="",
                error="Request to Twilio timed out.",
            )
        except Exception as e:
            return ToolResult(
                success=False,
                output="",
                error=f"API error: {str(e)}",
            )