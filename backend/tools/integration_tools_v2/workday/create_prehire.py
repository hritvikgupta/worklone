from typing import Any, Dict
import httpx
import xml.etree.ElementTree as ET
from backend.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class WorkdayCreatePrehireTool(BaseTool):
    name = "workday_create_prehire"
    description = "Create a new pre-hire (applicant) record in Workday. This is typically the first step before hiring an employee."
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
                "legalName": {
                    "type": "string",
                    "description": "Full legal name of the pre-hire (e.g., \"Jane Doe\")",
                },
                "email": {
                    "type": "string",
                    "description": "Email address of the pre-hire",
                },
                "phoneNumber": {
                    "type": "string",
                    "description": "Phone number of the pre-hire",
                },
                "address": {
                    "type": "string",
                    "description": "Address of the pre-hire",
                },
                "countryCode": {
                    "type": "string",
                    "description": "ISO 3166-1 Alpha-2 country code (defaults to US)",
                },
            },
            "required": ["tenantUrl", "tenant", "username", "password", "legalName"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        try:
            tenant_url = parameters["tenantUrl"]
            tenant = parameters["tenant"]
            username = parameters["username"]
            password = parameters["password"]
            legal_name = parameters["legalName"].strip()
            email = parameters.get("email")
            phone_number = parameters.get("phoneNumber")
            address = parameters.get("address")
            country_code = parameters.get("countryCode", "US")

            if self._is_placeholder_token(username) or self._is_placeholder_token(password):
                return ToolResult(success=False, output="", error="Workday credentials not configured.")

            if not any([email, phone_number, address]):
                return ToolResult(
                    success=False,
                    output="",
                    error="At least one contact method (email, phone, or address) is required",
                )

            parts = legal_name.split()
            first_name = parts[0] if parts else ""
            last_name = " ".join(parts[1:]) if len(parts) > 1 else ""
            if not last_name:
                return ToolResult(
                    success=False,
                    output="",
                    error="Legal name must include both a first name and last name",
                )

            ns_bsvc = "bsvc"
            usage_data_xml = f'''<{ns_bsvc}:Usage_Data>
  <{ns_bsvc}:Type_Data>
    <{ns_bsvc}:Type_Reference>
      <{ns_bsvc}:ID type="Communication_Usage_Type_ID">WORK</{ns_bsvc}:ID>
    </{ns_bsvc}:Type_Reference>
  </{ns_bsvc}:Type_Data>
  <{ns_bsvc}:Public>true</{ns_bsvc}:Public>
</{ns_bsvc}:Usage_Data>'''

            contact_parts = []
            if email:
                email_data_xml = f'''<{ns_bsvc}:Email_Address_Data>
  <{ns_bsvc}:Email_Address>{email}</{ns_bsvc}:Email_Address>
  {usage_data_xml}
</{ns_bsvc}:Email_Address_Data>'''
                contact_parts.append(email_data_xml)

            if phone_number:
                phone_device_ref_xml = f'''<{ns_bsvc}:Phone_Device_Type_Reference>
  <{ns_bsvc}:ID type="Phone_Device_Type_ID">Landline</{ns_bsvc}:ID>
</{ns_bsvc}:Phone_Device_Type_Reference>'''
                phone_data_xml = f'''<{ns_bsvc}:Phone_Data>
  <{ns_bsvc}:Phone_Number>{phone_number}</{ns_bsvc}:Phone_Number>
  {phone_device_ref_xml}
  {usage_data_xml}
</{ns_bsvc}:Phone_Data>'''
                contact_parts.append(phone_data_xml)

            if address:
                address_data_xml = f'''<{ns_bsvc}:Address_Data>
  <{ns_bsvc}:Formatted_Address>{address}</{ns_bsvc}:Formatted_Address>
  {usage_data_xml}
</{ns_bsvc}:Address_Data>'''
                contact_parts.append(address_data_xml)

            contact_info_xml = "\n  ".join(contact_parts)

            country_ref_xml = f'''<{ns_bsvc}:Country_Reference>
  <{ns_bsvc}:ID type="ISO_3166-1_Alpha-2_Code">{country_code}</{ns_bsvc}:ID>
</{ns_bsvc}:Country_Reference>'''

            name_detail_xml = f'''<{ns_bsvc}:Name_Detail_Data>
  {country_ref_xml}
  <{ns_bsvc}:First_Name>{first_name}</{ns_bsvc}:First_Name>
  <{ns_bsvc}:Last_Name>{last_name}</{ns_bsvc}:Last_Name>
</{ns_bsvc}:Name_Detail_Data>'''

            legal_name_data_xml = f'''<{ns_bsvc}:Legal_Name_Data>
  {name_detail_xml}
</{ns_bsvc}:Legal_Name_Data>'''

            name_data_xml = f'''<{ns_bsvc}:Name_Data>
  {legal_name_data_xml}
</{ns_bsvc}:Name_Data>'''

            personal_data_xml = f'''<{ns_bsvc}:Personal_Data>
  {name_data_xml}
  <{ns_bsvc}:Contact_Information_Data>
    {contact_info_xml}
  </{ns_bsvc}:Contact_Information_Data>
</{ns_bsvc}:Personal_Data>'''

            applicant_data_xml = f'''<{ns_bsvc}:Applicant_Data>
  {personal_data_xml}
</{ns_bsvc}:Applicant_Data>'''

            put_applicant_request_xml = f'''<{ns_bsvc}:Put_Applicant_Request>
  {applicant_data_xml}
</{ns_bsvc}:Put_Applicant_Request>'''

            soap_xml = f'''<?xml version="1.0" encoding="UTF-8"?>
<env:Envelope xmlns:env="http://schemas.xmlsoap.org/soap/envelope/" xmlns:{ns_bsvc}="urn:com.workday/bsvc">
  <env:Body>
    {put_applicant_request_xml}
  </env:Body>
</env:Envelope>'''

            api_version = "v48.0"
            url = f"{tenant_url.rstrip('/')}/ccx/service/{tenant}/Staffing/{api_version}"

            headers = {
                "Content-Type": "text/xml; charset=UTF-8",
            }

            auth = httpx.BasicAuth(username, password)

            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(url, content=soap_xml, headers=headers, auth=auth)

            if response.status_code != 200:
                return ToolResult(
                    success=False,
                    output="",
                    error=f"HTTP {response.status_code}: {response.text[:1000]}",
                )

            try:
                tree = ET.fromstring(response.text)
            except ET.ParseError as parse_err:
                return ToolResult(
                    success=False,
                    output="",
                    error=f"Invalid XML in response: {str(parse_err)}",
                )

            namespaces = {
                "env": "http://schemas.xmlsoap.org/soap/envelope/",
                "bsvc": "urn:com.workday/bsvc",
            }

            fault = tree.find(".//env:Fault", namespaces)
            if fault is not None:
                fault_string = tree.find(".//env:faultstring", namespaces)
                detail = tree.find(".//env:detail", namespaces)
                error_msg = (
                    fault_string.text
                    if fault_string is not None
                    else (detail.text if detail is not None else "Unknown SOAP fault")
                )
                return ToolResult(success=False, output="", error=f"SOAP Fault: {error_msg}")

            applicant_ref = tree.find(".//bsvc:Applicant_Reference", namespaces)
            if applicant_ref is None:
                return ToolResult(
                    success=False,
                    output="",
                    error="Applicant_Reference not found in response",
                )

            id_elem = applicant_ref.find("bsvc:ID", namespaces)
            pre_hire_id = id_elem.text if id_elem is not None else None

            descriptor = applicant_ref.attrib.get("Descriptor", "")

            data = {
                "preHireId": pre_hire_id,
                "descriptor": descriptor,
            }

            return ToolResult(success=True, output=response.text, data=data)

        except KeyError as key_err:
            return ToolResult(
                success=False,
                output="",
                error=f"Missing required parameter: {str(key_err)}",
            )
        except Exception as exc:
            return ToolResult(success=False, output="", error=f"API error: {str(exc)}")