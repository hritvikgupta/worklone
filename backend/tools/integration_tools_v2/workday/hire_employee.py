from typing import Any, Dict, Optional
import httpx
import base64
import xml.etree.ElementTree as ET
from backend.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class WorkdayHireEmployeeTool(BaseTool):
    name = "workday_hire_employee"
    description = "Hire a pre-hire into an employee position. Converts an applicant into an active employee record with position, start date, and manager assignment."
    category = "integration"

    VERSION = "v45.0"

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return []

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
                "preHireId": {
                    "type": "string",
                    "description": "Pre-hire (applicant) ID to convert into an employee",
                },
                "positionId": {
                    "type": "string",
                    "description": "Position ID to assign the new hire to",
                },
                "hireDate": {
                    "type": "string",
                    "description": "Hire date in ISO 8601 format (e.g., 2025-06-01)",
                },
                "employeeType": {
                    "type": "string",
                    "description": "Employee type (e.g., Regular, Temporary, Contractor)",
                },
            },
            "required": ["tenantUrl", "tenant", "username", "password", "preHireId", "positionId", "hireDate"],
        }

    def _build_soap_request(self, tenant: str, pre_hire_id: str, position_id: str, hire_date: str, employee_type: Optional[str] = None) -> str:
        version_num = self.VERSION.replace("v", "")
        soap_body = f"""<?xml version="1.0" encoding="UTF-8"?>
<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:bsvc="urn:com.workday/bsvc">
   <soapenv:Header/>
   <soapenv:Body>
      <bsvc:Hire_Pre_Hire_Request bsvc:version="{version_num}">
         <bsvc:Hire_Pre_Hire_Data>
            <bsvc:Prehire_Reference>
               <bsvc:ID type="Prehire_ID">{pre_hire_id}</bsvc:ID>
            </bsvc:Prehire_Reference>
            <bsvc:Position_Reference>
               <bsvc:ID type="Position_ID">{position_id}</bsvc:ID>
            </bsvc:Position_Reference>
            <bsvc:Hire_Date>{hire_date}</bsvc:Hire_Date>"""
        if employee_type:
            soap_body += f"""
            <bsvc:Employee_Type_Reference>
               <bsvc:ID type="Employee_Type_ID">{employee_type}</bsvc:ID>
            </bsvc:Employee_Type_Reference>"""
        soap_body += """
         </bsvc:Hire_Pre_Hire_Data>
      </bsvc:Hire_Pre_Hire_Request>
   </soapenv:Body>
</soapenv:Envelope>"""
        return soap_body

    def _parse_hire_response(self, xml_content: str) -> Dict[str, Any]:
        try:
            tree = ET.fromstring(xml_content)
            ns = {
                "soap": "http://schemas.xmlsoap.org/soap/envelope/",
                "bsvc": "urn:com.workday/bsvc",
            }
            response_elem = tree.find(".//bsvc:Hire_Pre_Hire_Response", ns)
            if response_elem is None:
                raise ValueError("Invalid response: No Hire_Pre_Hire_Response found. Possible SOAP Fault or API error.")

            def find_id(parent: ET.Element, id_type: str) -> Optional[str]:
                for id_elem in parent.findall(".//bsvc:ID", ns):
                    if id_elem.get("type") == id_type:
                        return id_elem.text.strip() if id_elem.text else None
                return None

            worker_id = find_id(response_elem, "Worker_ID")
            employee_id = find_id(response_elem, "Employee_ID")
            event_id = find_id(response_elem, "Business_Process_ID")
            hire_date_elem = response_elem.find(".//bsvc:Hire_Date", ns)
            hire_date_resp = hire_date_elem.text.strip() if hire_date_elem is not None and hire_date_elem.text else None

            return {
                "workerId": worker_id,
                "employeeId": employee_id,
                "eventId": event_id,
                "hireDate": hire_date_resp,
            }
        except ET.ParseError as pe:
            raise ValueError(f"Invalid XML response: {str(pe)}")

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        tenant_url = parameters.get("tenantUrl", "").rstrip("/")
        tenant = parameters.get("tenant")
        username = parameters.get("username")
        password = parameters.get("password")
        pre_hire_id = parameters.get("preHireId")
        position_id = parameters.get("positionId")
        hire_date = parameters.get("hireDate")
        employee_type = parameters.get("employeeType")

        if not all([tenant_url, tenant, username, password, pre_hire_id, position_id, hire_date]):
            return ToolResult(success=False, output="", error="Missing required parameters.")

        auth_str = f"{username}:{password}"
        creds = base64.b64encode(auth_str.encode("utf-8")).decode("utf-8")
        headers = {
            "Authorization": f"Basic {creds}",
            "Content-Type": "text/xml; charset=UTF-8",
        }
        url = f"{tenant_url}/ccx/service/{tenant}/Human_Resources/{self.VERSION}"

        soap_body = self._build_soap_request(tenant, pre_hire_id, position_id, hire_date, employee_type)

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:  # Longer timeout for Workday
                response = await client.post(url, headers=headers, content=soap_body.encode("utf-8"))

            if response.status_code != 200:
                return ToolResult(
                    success=False,
                    output="",
                    error=f"Workday API HTTP error {response.status_code}: {response.text[:1000]}",
                )

            data = self._parse_hire_response(response.text)
            return ToolResult(
                success=True,
                output=f"Employee hired successfully. Worker ID: {data.get('workerId', 'N/A')}",
                data=data,
            )

        except ValueError as ve:
            return ToolResult(success=False, output="", error=f"Workday API error: {str(ve)}")
        except Exception as e:
            return ToolResult(success=False, output="", error=f"Execution error: {str(e)}")