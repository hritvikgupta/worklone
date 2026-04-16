from typing import Any, Dict
import httpx
import base64
import xml.etree.ElementTree as ET
import xml.sax.saxutils
from backend.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class WorkdayTerminateWorkerTool(BaseTool):
    name = "workday_terminate_worker"
    description = "Initiate a worker termination in Workday. Triggers the Terminate Employee business process."
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="tenantUrl",
                description="Workday instance URL (e.g., https://wd5-impl-services1.workday.com)",
                env_var="WORKDAY_TENANT_URL",
                required=True,
            ),
            CredentialRequirement(
                key="tenant",
                description="Workday tenant name",
                env_var="WORKDAY_TENANT",
                required=True,
            ),
            CredentialRequirement(
                key="username",
                description="Integration System User username",
                env_var="WORKDAY_USERNAME",
                required=True,
            ),
            CredentialRequirement(
                key="password",
                description="Integration System User password",
                env_var="WORKDAY_PASSWORD",
                required=True,
                auth_type="api_key",
            ),
        ]

    def _escape_xml(self, text: str) -> str:
        return xml.sax.saxutils.escape(str(text))

    def _build_soap_request(self, params: dict) -> str:
        worker_id = params["workerId"]
        termination_date = params["terminationDate"]
        reason = params["reason"]
        notification_date = params.get("notificationDate")
        last_day_of_work = params.get("lastDayOfWork", termination_date)

        parts = [
            '<?xml version="1.0" encoding="UTF-8"?>',
            '<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/" xmlns:bsvc="urn:com.workday/bsvc">',
            "  <soap:Header/>",
            "  <soap:Body>",
            "    <bsvc:Terminate>",
            f'      <bsvc:Worker_Reference><bsvc:ID bsvc:type="Worker_ID">{self._escape_xml(worker_id)}</bsvc:ID></bsvc:Worker_Reference>',
            f'      <bsvc:Termination_Date>{termination_date}</bsvc:Termination_Date>',
            f'      <bsvc:Termination_Reason_Reference><bsvc:ID bsvc:type="Termination_Reason_Name">{self._escape_xml(reason)}</bsvc:ID></bsvc:Termination_Reason_Reference>',
        ]
        if notification_date:
            parts.append(f"      <bsvc:Notification_Date>{notification_date}</bsvc:Notification_Date>")
        parts.extend([
            f"      <bsvc:Last_Day_of_Work>{last_day_of_work}</bsvc:Last_Day_of_Work>",
            "    </bsvc:Terminate>",
            "  </soap:Body>",
            "</soap:Envelope>",
        ])
        return "\n".join(parts)

    def _parse_workday_response(self, xml_text: str, params: dict) -> dict:
        ns: Dict[str, str] = {
            "soap": "http://schemas.xmlsoap.org/soap/envelope/",
            "bsvc": "urn:com.workday/bsvc",
        }
        root = ET.fromstring(xml_text)
        fault = root.find(".//soap:Fault", ns)
        if fault is not None:
            faultstring = fault.find("faultstring")
            error_msg = faultstring.text if faultstring is not None else xml_text[:500]
            raise ValueError(f"SOAP Fault: {error_msg}")
        response_elem = root.find(".//bsvc:Terminate_Response", ns)
        if response_elem is None:
            raise ValueError("No Terminate_Response found in response")
        event_id_elem = response_elem.find(".//bsvc:Business_Process_Reference/bsvc:ID[@bsvc:type='Business_Process_ID']", ns)
        event_id = event_id_elem.text if event_id_elem is not None else None
        if event_id is None:
            raise ValueError("No Business_Process_ID found in response")
        return {
            "eventId": event_id,
            "workerId": params["workerId"],
            "terminationDate": params["terminationDate"],
        }

    def get_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "tenantUrl": {
                    "type": "string",
                    "description": "Workday instance URL (e.g., https://wd5-impl-services1.workday.com)",
                },
                "tenant": {
                    "type": "string",
                    "description": "Workday tenant name",
                },
                "username": {
                    "type": "string",
                    "description": "Integration System User username",
                },
                "password": {
                    "type": "string",
                    "description": "Integration System User password",
                },
                "workerId": {
                    "type": "string",
                    "description": "Worker ID to terminate",
                },
                "terminationDate": {
                    "type": "string",
                    "description": "Termination date in ISO 8601 format (e.g., 2025-06-01)",
                },
                "reason": {
                    "type": "string",
                    "description": "Termination reason (e.g., Resignation, End_of_Contract, Retirement)",
                },
                "notificationDate": {
                    "type": "string",
                    "description": "Date the termination was communicated in ISO 8601 format",
                },
                "lastDayOfWork": {
                    "type": "string",
                    "description": "Last day of work in ISO 8601 format (defaults to termination date)",
                },
            },
            "required": ["tenantUrl", "tenant", "username", "password", "workerId", "terminationDate", "reason"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        tenant_url = parameters.get("tenantUrl")
        tenant = parameters.get("tenant")
        username = parameters.get("username")
        password = parameters.get("password")
        if not all([tenant_url, tenant, username, password]):
            return ToolResult(success=False, output="", error="Missing required credentials: tenantUrl, tenant, username, password.")
        if self._is_placeholder_token(password) or self._is_placeholder_token(username):
            return ToolResult(success=False, output="", error="Access credentials not configured.")
        required_params = ["workerId", "terminationDate", "reason"]
        missing_params = [key for key in required_params if not parameters.get(key)]
        if missing_params:
            return ToolResult(success=False, output="", error=f"Missing required parameters: {', '.join(missing_params)}")
        url = f"{tenant_url.rstrip('/')}/ccx/service/{tenant}/Human_Resources"
        xml_body = self._build_soap_request(parameters)
        auth_str = base64.b64encode(f"{username}:{password}".encode("utf-8")).decode("utf-8")
        headers = {
            "Authorization": f"Basic {auth_str}",
            "Content-Type": "text/xml; charset=utf-8",
            "SOAPAction": "Terminate",
        }
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(url, headers=headers, content=xml_body)
                if response.status_code != 200:
                    return ToolResult(
                        success=False,
                        output="",
                        error=f"HTTP error {response.status_code}: {response.text[:500]}",
                    )
                data = self._parse_workday_response(response.text, parameters)
                return ToolResult(success=True, output=str(data), data=data)
        except ValueError as ve:
            return ToolResult(success=False, output="", error=f"Workday API error: {str(ve)}")
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")