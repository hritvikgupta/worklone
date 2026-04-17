from typing import Any, Dict
import httpx
import base64
import xml.etree.ElementTree as ET
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class WorkdayChangeJobTool(BaseTool):
    name = "workday_change_job"
    description = "Perform a job change for a worker including transfers, promotions, demotions, and lateral moves."
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="tenant_url",
                description="Workday instance URL (e.g., https://wd5-impl-services1.workday.com)",
                env_var="WORKDAY_TENANT_URL",
                required=True,
                auth_type="custom",
            ),
            CredentialRequirement(
                key="tenant",
                description="Workday tenant name",
                env_var="WORKDAY_TENANT",
                required=True,
                auth_type="custom",
            ),
            CredentialRequirement(
                key="username",
                description="Integration System User username",
                env_var="WORKDAY_USERNAME",
                required=True,
                auth_type="custom",
            ),
            CredentialRequirement(
                key="password",
                description="Integration System User password",
                env_var="WORKDAY_PASSWORD",
                required=True,
                auth_type="password",
            ),
        ]

    def get_schema(self) -> dict:
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
                    "description": "Worker ID for the job change",
                },
                "effectiveDate": {
                    "type": "string",
                    "description": "Effective date for the job change in ISO 8601 format (e.g., 2025-06-01)",
                },
                "newPositionId": {
                    "type": "string",
                    "description": "New position ID (for transfers)",
                },
                "newJobProfileId": {
                    "type": "string",
                    "description": "New job profile ID (for role changes)",
                },
                "newLocationId": {
                    "type": "string",
                    "description": "New work location ID (for relocations)",
                },
                "newSupervisoryOrgId": {
                    "type": "string",
                    "description": "Target supervisory organization ID (for org transfers)",
                },
                "reason": {
                    "type": "string",
                    "description": "Reason for the job change (e.g., Promotion, Transfer, Reorganization)",
                },
            },
            "required": [
                "tenantUrl",
                "tenant",
                "username",
                "password",
                "workerId",
                "effectiveDate",
                "reason",
            ],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        try:
            tenant_url = parameters["tenantUrl"]
            tenant = parameters["tenant"]
            username = parameters["username"]
            password = parameters["password"]
            worker_id = parameters["workerId"]
            effective_date = parameters["effectiveDate"]
            reason = parameters["reason"]
            new_position_id = parameters.get("newPositionId")
            new_job_profile_id = parameters.get("newJobProfileId")
            new_location_id = parameters.get("newLocationId")
            new_supervisory_org_id = parameters.get("newSupervisoryOrgId")
        except KeyError as e:
            return ToolResult(
                success=False,
                output="",
                error=f"Missing required parameter: {str(e)}",
            )

        if self._is_placeholder_token(password) or not password.strip():
            return ToolResult(
                success=False,
                output="",
                error="Password not configured.",
            )

        detail_parts = [
            f'''<bsvc:Reason_Reference>
      <wd:ID wd:type="Change_Job_Subcategory_ID">{reason}</wd:ID>
    </bsvc:Reason_Reference>'''
        ]

        if new_position_id:
            detail_parts.append(
                f'''<bsvc:Position_Reference>
      <wd:ID wd:type="Position_ID">{new_position_id}</wd:ID>
    </bsvc:Position_Reference>'''
            )
        if new_job_profile_id:
            detail_parts.append(
                f'''<bsvc:Job_Profile_Reference>
      <wd:ID wd:type="Job_Profile_ID">{new_job_profile_id}</wd:ID>
    </bsvc:Job_Profile_Reference>'''
            )
        if new_location_id:
            detail_parts.append(
                f'''<bsvc:Location_Reference>
      <wd:ID wd:type="Location_ID">{new_location_id}</wd:ID>
    </bsvc:Location_Reference>'''
            )
        if new_supervisory_org_id:
            detail_parts.append(
                f'''<bsvc:Supervisory_Organization_Reference>
      <wd:ID wd:type="Supervisory_Organization_ID">{new_supervisory_org_id}</wd:ID>
    </bsvc:Supervisory_Organization_Reference>'''
            )

        change_job_detail_data = "\n      ".join(detail_parts)

        soap_body = f"""<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/" xmlns:bsvc="urn:com.workday/bsvc" xmlns:wd="urn:com.workday/bsvc">
  <soap:Header/>
  <soap:Body>
    <bsvc:Change_Job>
      <bsvc:Business_Process_Parameters>
        <wd:Auto_Complete>true</wd:Auto_Complete>
        <wd:Run_Now>true</wd:Run_Now>
      </bsvc:Business_Process_Parameters>
      <bsvc:Change_Job_Data>
        <bsvc:Worker_Reference>
          <wd:ID wd:type="Employee_ID">{worker_id}</wd:ID>
        </bsvc:Worker_Reference>
        <wd:Effective_Date>{effective_date}</wd:Effective_Date>
        <bsvc:Change_Job_Detail_Data>
          {change_job_detail_data}
        </bsvc:Change_Job_Detail_Data>
      </bsvc:Change_Job_Data>
    </bsvc:Change_Job>
  </soap:Body>
</soap:Envelope>"""

        url = f"{tenant_url}/ccx/service/{tenant}/Staffing"

        auth_str = f"{username}:{password}"
        auth_b64 = base64.b64encode(auth_str.encode("utf-8")).decode("utf-8")

        headers = {
            "Authorization": f"Basic {auth_b64}",
            "Content-Type": "text/xml; charset=utf-8",
            "SOAPAction": "http://wsdl.workday.com/Staffing_Service/Change_Job",
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, content=soap_body)

                if response.status_code == 200:
                    try:
                        root = ET.fromstring(response.content)
                        namespaces = {
                            "soap": "http://schemas.xmlsoap.org/soap/envelope/",
                            "bsvc": "urn:com.workday/bsvc",
                            "wd": "urn:com.workday/bsvc",
                        }
                        event_id_elem = root.find(".//bsvc:Event_Reference/wd:ID", namespaces)
                        if event_id_elem is None:
                            return ToolResult(
                                success=False,
                                output=response.text,
                                error="Event_Reference ID not found in response. Check for SOAP fault.",
                            )
                        event_id = (event_id_elem.text or "").strip()
                        output_data = {
                            "eventId": event_id,
                            "workerId": worker_id,
                            "effectiveDate": effective_date,
                        }
                        return ToolResult(
                            success=True,
                            output=response.text,
                            data=output_data,
                        )
                    except ET.ParseError as pe:
                        return ToolResult(
                            success=False,
                            output="",
                            error=f"Failed to parse XML response: {str(pe)}",
                        )
                else:
                    return ToolResult(
                        success=False,
                        output="",
                        error=f"API error {response.status_code}: {response.text}",
                    )
        except Exception as e:
            return ToolResult(
                success=False,
                output="",
                error=f"API error: {str(e)}",
            )