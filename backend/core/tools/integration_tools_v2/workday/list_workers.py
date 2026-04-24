from typing import Any, Dict
import json
import xml.etree.ElementTree as ET

import httpx

from backend.core.tools.system_tools.base import BaseTool, CredentialRequirement, ToolResult
from backend.core.tools.integration_tools_v2.workday.soap import (
    DEFAULT_WORKDAY_VERSION,
    build_basic_auth_header,
    build_workday_url,
    xml_escape,
)


class WorkdayListWorkersTool(BaseTool):
    name = "workday_list_workers"
    description = "List or search workers with optional pagination."
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
                "search": {
                    "type": "string",
                    "description": "Optional search text for worker name or employee id",
                },
                "limit": {
                    "type": "number",
                    "description": "Maximum number of workers to return (default: 20)",
                },
                "offset": {
                    "type": "number",
                    "description": "Number of records to skip for pagination",
                },
            },
            "required": ["tenantUrl", "tenant", "username", "password"],
        }

    @staticmethod
    def _element_to_dict(elem: ET.Element | None) -> Any:
        if elem is None:
            return None

        data: Dict[str, Any] = {}
        for key, value in elem.attrib.items():
            data[f"@{key}"] = value

        if elem.text and elem.text.strip():
            data["_text"] = elem.text.strip()

        children: Dict[str, list[Any]] = {}
        for child in elem:
            child_tag = child.tag.rsplit("}", 1)[-1]
            child_dict = WorkdayListWorkersTool._element_to_dict(child)
            children.setdefault(child_tag, []).append(child_dict)

        for tag, values in children.items():
            data[tag] = values[0] if len(values) == 1 else values

        return data

    @staticmethod
    def _find_worker_id(worker_ref: ET.Element | None, ns: dict[str, str]) -> str | None:
        if worker_ref is None:
            return None

        ids = worker_ref.findall("wd:ID", ns)
        for id_elem in ids:
            if (id_elem.get("{urn:com.workday/bsvc}type") or id_elem.get("wd:type")) == "Employee_ID":
                return id_elem.text

        return ids[0].text if ids else None

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        tenant_url = parameters.get("tenantUrl")
        tenant = parameters.get("tenant")
        username = parameters.get("username")
        password = parameters.get("password")
        search = (parameters.get("search") or "").strip()

        if not all([tenant_url, tenant, username, password]):
            return ToolResult(success=False, output="", error="Missing required parameters.")

        try:
            limit = max(1, min(200, int(parameters.get("limit", 20))))
            offset = max(0, int(parameters.get("offset", 0)))
        except (TypeError, ValueError):
            return ToolResult(success=False, output="", error="limit and offset must be valid numbers.")

        page = (offset // limit) + 1
        version = DEFAULT_WORKDAY_VERSION
        url = build_workday_url(tenant_url, tenant, service="human_resources", version=version)
        headers = build_basic_auth_header(username, password)

        request_criteria = ""
        if search:
            search_escaped = xml_escape(search)
            request_criteria = f"""
      <wd:Request_Criteria>
        <wd:Worker_Name>{search_escaped}</wd:Worker_Name>
      </wd:Request_Criteria>"""

        soap_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/" xmlns:wd="urn:com.workday/bsvc">
  <soap:Header/>
  <soap:Body>
    <wd:Get_Workers_Request wd:version="{version}">
      {request_criteria}
      <wd:Response_Filter>
        <wd:Page>{page}</wd:Page>
        <wd:Count>{limit}</wd:Count>
      </wd:Response_Filter>
      <wd:Response_Group>
        <wd:Include_Reference>true</wd:Include_Reference>
        <wd:Include_Personal_Information>true</wd:Include_Personal_Information>
        <wd:Include_Employment_Information>true</wd:Include_Employment_Information>
      </wd:Response_Group>
    </wd:Get_Workers_Request>
  </soap:Body>
</soap:Envelope>"""

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(url, headers=headers, content=soap_xml)

            if response.status_code != 200:
                return ToolResult(
                    success=False,
                    output="",
                    error=f"HTTP {response.status_code}: {response.text}",
                )

            root = ET.fromstring(response.content)
            ns = {
                "soap": "http://schemas.xmlsoap.org/soap/envelope/",
                "wd": "urn:com.workday/bsvc",
            }

            fault = root.find(".//soap:Fault", ns)
            if fault is not None:
                faultstring = fault.find("faultstring")
                error_msg = faultstring.text if faultstring is not None else "Unknown SOAP fault"
                return ToolResult(success=False, output="", error=f"SOAP Fault: {error_msg}")

            response_elem = root.find(".//wd:Get_Workers_Response", ns)
            if response_elem is None:
                return ToolResult(success=False, output="", error="Invalid response: no Get_Workers_Response")

            results_elem = response_elem.find("wd:Response_Results", ns)
            total = 0
            if results_elem is not None:
                total_text = (results_elem.findtext("wd:Total_Results", default="0", namespaces=ns) or "0").strip()
                if total_text.isdigit():
                    total = int(total_text)

            response_data = response_elem.find("wd:Response_Data", ns)
            worker_elems = response_data.findall("wd:Worker", ns) if response_data is not None else []

            workers = []
            for worker_elem in worker_elems:
                worker_ref = worker_elem.find("wd:Worker_Reference", ns)
                worker_id = self._find_worker_id(worker_ref, ns)

                descriptor = worker_elem.findtext("wd:Worker_Descriptor", default="", namespaces=ns)
                worker_data = worker_elem.find("wd:Worker_Data", ns)
                personal_data = (
                    self._element_to_dict(worker_data.find("wd:Personal_Data", ns))
                    if worker_data is not None
                    else None
                )
                employment_data = (
                    self._element_to_dict(worker_data.find("wd:Employment_Data", ns))
                    if worker_data is not None
                    else None
                )

                workers.append(
                    {
                        "id": worker_id,
                        "descriptor": descriptor,
                        "personalData": personal_data,
                        "employmentData": employment_data,
                    }
                )

            result_data = {"workers": workers, "total": total}
            return ToolResult(success=True, output=json.dumps(result_data, indent=2), data=result_data)

        except ET.ParseError as e:
            return ToolResult(success=False, output="", error=f"XML parse error: {str(e)}")
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
