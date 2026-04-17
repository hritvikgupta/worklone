from typing import Any, Dict, List
import httpx
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class WorkdayAssignOnboardingTool(BaseTool):
    name = "workday_assign_onboarding"
    description = "Create or update an onboarding plan assignment for a worker. Sets up onboarding stages and manages the assignment lifecycle."
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> List[CredentialRequirement]:
        return []

    def get_schema(self) -> Dict[str, Any]:
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
                    "description": "Worker ID to assign the onboarding plan to",
                },
                "onboardingPlanId": {
                    "type": "string",
                    "description": "Onboarding plan ID to assign",
                },
                "actionEventId": {
                    "type": "string",
                    "description": "Action event ID that enables the onboarding plan (e.g., the hiring event ID)",
                },
            },
            "required": [
                "tenantUrl",
                "tenant",
                "username",
                "password",
                "workerId",
                "onboardingPlanId",
                "actionEventId",
            ],
        }

    def _build_soap_request(
        self,
        username: str,
        password: str,
        worker_id: str,
        onboarding_plan_id: str,
        action_event_id: str,
    ) -> str:
        effective_moment = datetime.now(timezone.utc).isoformat()
        return f"""<?xml version="1.0" encoding="UTF-8"?>
<env:Envelope xmlns:env="http://www.w3.org/2003/05/soap-envelope">
  <env:Header>
    <wsse:Security env:mustUnderstand="1" xmlns:wsse="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-secext-1.0.xsd">
      <wsse:UsernameToken>
        <wsse:Username>{username}</wsse:Username>
        <wsse:Password Type="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-secext-1.0.xsd#PasswordText">{password}</wsse:Password>
      </wsse:UsernameToken>
    </wsse:Security>
  </env:Header>
  <env:Body>
    <wd:Put_Onboarding_Plan_Assignment_Request wd:version="v47.0" xmlns:wd="urn:com.workday/bsvc">
      <wd:Request_Criteria>
        <wd:Onboarding_Plan_Assignment_Data>
          <wd:Onboarding_Plan_Reference>
            <wd:ID wd:type="Onboarding_Plan_ID">
              <wd:ID>{onboarding_plan_id}</wd:ID>
            </wd:ID>
          </wd:Onboarding_Plan_Reference>
          <wd:Person_Reference>
            <wd:ID wd:type="WID">
              <wd:ID>{worker_id}</wd:ID>
            </wd:ID>
          </wd:Person_Reference>
          <wd:Action_Event_Reference>
            <wd:ID wd:type="Background_Check_ID">
              <wd:ID>{action_event_id}</wd:ID>
            </wd:ID>
          </wd:Action_Event_Reference>
          <wd:Assignment_Effective_Moment>{effective_moment}</wd:Assignment_Effective_Moment>
          <wd:Active>true</wd:Active>
        </wd:Onboarding_Plan_Assignment_Data>
      </wd:Request_Criteria>
    </wd:Put_Onboarding_Plan_Assignment_Request>
  </env:Body>
</env:Envelope>"""

    async def execute(self, parameters: Dict[str, Any], context: Dict | None = None) -> ToolResult:
        try:
            tenant_url: str = parameters["tenantUrl"]
            tenant: str = parameters["tenant"]
            username: str = parameters["username"]
            password: str = parameters["password"]
            worker_id: str = parameters["workerId"]
            onboarding_plan_id: str = parameters["onboardingPlanId"]
            action_event_id: str = parameters["actionEventId"]
        except KeyError as e:
            return ToolResult(success=False, output="", error=f"Missing required parameter: {str(e)}")

        if self._is_placeholder_token(password):
            return ToolResult(success=False, output="", error="Workday password not configured.")

        url = f"{tenant_url.rstrip('/')}/ccx/service/{tenant}/Human_Resources"
        headers = {
            "Content-Type": "text/xml; charset=utf-8",
            "SOAPAction": "urn:com.workday/bsvc/Put_Onboarding_Plan_Assignment",
        }
        soap_xml = self._build_soap_request(
            username, password, worker_id, onboarding_plan_id, action_event_id
        )

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, content=soap_xml)
                if response.status_code != 200:
                    return ToolResult(
                        success=False, output="", error=f"HTTP {response.status_code}: {response.text[:500]}"
                    )

                try:
                    root = ET.fromstring(response.content.decode("utf-8"))
                    ns: Dict[str, str] = {
                        "env": "http://www.w3.org/2003/05/soap-envelope",
                        "wd": "urn:com.workday/bsvc",
                    }
                    fault = root.find(".//env:Fault", ns)
                    if fault is not None:
                        text_elem = root.find(".//env:Text", ns)
                        error_msg = text_elem.text.strip() if text_elem is not None and text_elem.text else "Unknown SOAP fault"
                        return ToolResult(success=False, output="", error=f"SOAP Fault: {error_msg}")

                    assignment_id = ""
                    ref_elem = root.find(".//wd:Onboarding_Plan_Assignment_Reference", ns)
                    if ref_elem is not None:
                        id_elem = ref_elem.find("wd:ID", ns)
                        if id_elem is not None:
                            inner_id_elem = id_elem.find("wd:ID", ns)
                            if inner_id_elem is not None and inner_id_elem.text:
                                assignment_id = inner_id_elem.text.strip()

                    output_data = {
                        "assignmentId": assignment_id,
                        "workerId": worker_id,
                        "planId": onboarding_plan_id,
                    }
                    return ToolResult(success=True, output=response.text, data=output_data)
                except ET.ParseError as pe:
                    return ToolResult(
                        success=False, output="", error=f"Failed to parse XML response: {str(pe)}"
                    )
        except httpx.RequestError as he:
            return ToolResult(success=False, output="", error=f"Request error: {str(he)}")
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")