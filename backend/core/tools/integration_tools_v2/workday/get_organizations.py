from typing import Any, Dict
import httpx
import xml.etree.ElementTree as ET
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class WorkdayGetOrganizationsTool(BaseTool):
    name = "workday_get_organizations"
    description = "Retrieve organizations, departments, and cost centers from Workday."
    category = "integration"

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
                "type": {
                    "type": "string",
                    "description": "Organization type filter (e.g., Supervisory, Cost_Center, Company, Region)",
                },
                "limit": {
                    "type": "number",
                    "description": "Maximum number of organizations to return (default: 20)",
                },
                "offset": {
                    "type": "number",
                    "description": "Number of records to skip for pagination",
                },
            },
            "required": ["tenantUrl", "tenant", "username", "password"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        tenant_url = parameters["tenantUrl"]
        tenant = parameters["tenant"]
        username = parameters["username"]
        password = parameters["password"]
        org_type = parameters.get("type")
        limit = int(parameters.get("limit", 20))
        offset = int(parameters.get("offset", 0))
        page = 1 if offset == 0 else (offset // limit) + 1

        url = f"{tenant_url.rstrip('/')}/ccx/service/{tenant}/Human_Resources/v45.0"

        request_criteria_xml = ""
        if org_type:
            request_criteria_xml = f'''<wd:Request_Criteria>
        <wd:Organization_Type_Reference>
          <wd:ID wd:type="Organization_Type_ID">{org_type}</wd:ID>
        </wd:Organization_Type_Reference>
      </wd:Request_Criteria>'''

        soap_xml = f'''<?xml version="1.0" encoding="UTF-8"?>
<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/" xmlns:wsse="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-secext-1.0.xsd" xmlns:wd="urn:com.workday/bsvc">
  <soap:Header>
    <wsse:Security soap:mustUnderstand="1">
      <wsse:UsernameToken>
        <wsse:Username>{username}</wsse:Username>
        <wsse:Password Type="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-username-token-profile-1.0#PasswordText">{password}</wsse:Password>
      </wsse:UsernameToken>
    </wsse:Security>
  </soap:Header>
  <soap:Body>
    <wd:Get_Organizations_Request wd:version="v45.0">
      {request_criteria_xml}
      <wd:Response_Filter>
        <wd:Page>{page}</wd:Page>
        <wd:Count>{limit}</wd:Count>
      </wd:Response_Filter>
      <wd:Response_Group>
        <wd:Include_Hierarchy_Data>true</wd:Include_Hierarchy_Data>
      </wd:Response_Group>
    </wd:Get_Organizations_Request>
  </soap:Body>
</soap:Envelope>'''

        headers = {
            "Content-Type": "application/soap+xml; charset=utf-8",
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, content=soap_xml)

                if response.status_code != 200:
                    return ToolResult(success=False, output="", error=response.text)

                tree = ET.fromstring(response.text)
                ns = {
                    "soap": "http://schemas.xmlsoap.org/soap/envelope/",
                    "wd": "urn:com.workday/bsvc",
                }

                fault = tree.find(".//soap:Fault", ns)
                if fault is not None:
                    faultstring = (
                        tree.find(".//faultstring", ns)
                        or tree.find(".//soap:Text", ns)
                        or fault.find("faultstring")
                    )
                    error_msg = (
                        faultstring.text if faultstring is not None else "SOAP Fault"
                    )
                    return ToolResult(
                        success=False, output="", error=f"SOAP Fault: {error_msg}"
                    )

                body = tree.find("soap:Body", ns)
                if body is None:
                    return ToolResult(
                        success=False,
                        output="",
                        error="Invalid SOAP response: no body",
                    )

                response_elem = body.find("wd:Get_Organizations_Response", ns)
                if response_elem is None:
                    return ToolResult(
                        success=False,
                        output="",
                        error="Invalid response: no Get_Organizations_Response",
                    )

                response_data = response_elem.find("wd:Response_Data", ns)
                organizations_elems = (
                    response_data.findall("wd:Organization", ns)
                    if response_data is not None
                    else []
                )

                organizations = []
                for org_elem in organizations_elems:
                    org_ref = org_elem.find("wd:Organization_Reference", ns)
                    org_id_elem = org_ref.find("wd:ID", ns) if org_ref is not None else None
                    org_id = org_id_elem.text if org_id_elem is not None else None

                    descriptor_elem = org_elem.find("wd:Organization_Descriptor", ns)
                    descriptor = descriptor_elem.text if descriptor_elem is not None else None

                    org_data = org_elem.find("wd:Organization_Data", ns)
                    type_id = None
                    subtype_id = None
                    is_active = None
                    if org_data is not None:
                        type_ref = org_data.find("wd:Organization_Type_Reference", ns)
                        if type_ref is not None:
                            type_id_elem = type_ref.find("wd:ID", ns)
                            type_id = type_id_elem.text if type_id_elem is not None else None

                        subtype_ref = org_data.find("wd:Organization_Subtype_Reference", ns)
                        if subtype_ref is not None:
                            subtype_id_elem = subtype_ref.find("wd:ID", ns)
                            subtype_id = (
                                subtype_id_elem.text
                                if subtype_id_elem is not None
                                else None
                            )

                        inactive_elem = org_data.find("wd:Inactive", ns)
                        if inactive_elem is not None:
                            inactive_str = (inactive_elem.text or "").lower().strip()
                            is_active = inactive_str != "true"

                    organizations.append(
                        {
                            "id": org_id,
                            "descriptor": descriptor,
                            "type": type_id,
                            "subtype": subtype_id,
                            "isActive": is_active,
                        }
                    )

                response_results = response_elem.find("wd:Response_Results", ns)
                total = len(organizations)
                if response_results is not None:
                    total_elem = response_results.find("wd:Total_Results", ns)
                    if total_elem is not None and total_elem.text:
                        total = int(total_elem.text)

                result_data = {"organizations": organizations, "total": total}
                return ToolResult(
                    success=True, output=response.text, data=result_data
                )

        except Exception as e:
            return ToolResult(
                success=False, output="", error=f"API error: {str(e)}"
            )