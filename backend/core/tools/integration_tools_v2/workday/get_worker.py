from typing import Any, Dict
import httpx
import base64
import xml.etree.ElementTree as ET
import xml.sax.saxutils
import json
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class WorkdayGetWorkerTool(BaseTool):
    name = "workday_get_worker"
    description = "Retrieve a specific worker profile including personal, employment, and organization data."
    category = "integration"

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return []

    @staticmethod
    def _element_to_dict(elem: ET.Element) -> Any:
        if elem is None:
            return None
        d: Dict[str, Any] = {}
        for key, value in elem.attrib.items():
            d[f"@{key}"] = value
        if elem.text and elem.text.strip():
            d["_text"] = elem.text.strip()
        children: Dict[str, list[Any]] = {}
        for child in elem:
            child_tag = child.tag.rsplit("}", 1)[-1]
            child_dict = WorkdayGetWorkerTool._element_to_dict(child)
            if child_tag not in children:
                children[child_tag] = []
            children[child_tag].append(child_dict)
        for tag, clist in children.items():
            d[tag] = clist[0] if len(clist) == 1 else clist
        return d

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
                    "description": "Worker ID to retrieve (e.g., 3aa5550b7fe348b98d7b5741afc65534)",
                },
            },
            "required": ["tenantUrl", "tenant", "username", "password", "workerId"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        tenant_url = parameters.get("tenantUrl")
        tenant = parameters.get("tenant")
        username = parameters.get("username")
        password = parameters.get("password")
        worker_id = parameters.get("workerId")

        if not all([tenant_url, tenant, username, password, worker_id]):
            return ToolResult(success=False, output="", error="Missing required parameters.")

        version = "v45.0"
        service_version = version[1:]
        url = f"{tenant_url.rstrip('/')}/{tenant}/ccx/service/humanresources/Human_Resources/{version}"

        auth_str = base64.b64encode(f"{username}:{password}".encode("utf-8")).decode("utf-8")
        headers = {
            "Authorization": f"Basic {auth_str}",
            "Content-Type": "text/xml; charset=utf-8",
        }

        bsvc_ns = f"http://www.workday.com/xmlns/hr/services/{service_version}"
        wd_ns = f"urn:workday/web/services/{service_version}"
        worker_id_escaped = xml.sax.saxutils.escape(worker_id)
        soap_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:bsvc="{bsvc_ns}" xmlns:wd="{wd_ns}">
  <soapenv:Header/>
  <soapenv:Body>
    <bsvc:Get_Workers_Request bsvc:version="{version}">
      <bsvc:Request_References>
        <bsvc:Worker_Reference>
          <bsvc:ID wd:type="Employee_ID">{worker_id_escaped}</bsvc:ID>
        </bsvc:Worker_Reference>
      </bsvc:Request_References>
      <bsvc:Response_Group>
        <bsvc:Include_Reference/>
        <bsvc:Include_Personal_Information/>
        <bsvc:Include_Employment_Information/>
        <bsvc:Include_Compensation/>
        <bsvc:Include_Organizations/>
      </bsvc:Response_Group>
    </bsvc:Get_Workers_Request>
  </soapenv:Body>
</soapenv:Envelope>"""

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(url, headers=headers, content=soap_xml)

            if response.status_code != 200:
                return ToolResult(
                    success=False, output="", error=f"HTTP {response.status_code}: {response.text}"
                )

            root = ET.fromstring(response.content)
            nsmap = {
                "soapenv": "http://schemas.xmlsoap.org/soap/envelope/",
                "bsvc": bsvc_ns,
                "wd": wd_ns,
            }

            fault = root.find(".//soapenv:Fault", nsmap)
            if fault is not None:
                faultstring = fault.find("soapenv:faultstring", nsmap)
                error_msg = faultstring.text if faultstring is not None else "Unknown SOAP fault"
                return ToolResult(success=False, output="", error=f"SOAP Fault: {error_msg}")

            body = root.find("soapenv:Body", nsmap)
            resp_elem = body.find("bsvc:Get_Workers_Response", nsmap)
            if resp_elem is None:
                return ToolResult(
                    success=False, output="", error="Invalid response: no Get_Workers_Response"
                )

            data_elem = resp_elem.find("bsvc:Response_Data", nsmap)
            worker = None
            if data_elem is not None:
                workers = data_elem.findall("bsvc:Worker", nsmap)
                if workers:
                    worker_elem = workers[0]
                    worker_ref = worker_elem.find("bsvc:Worker_Reference", nsmap)
                    id_ = None
                    if worker_ref is not None:
                        id_elem = worker_ref.find("bsvc:ID", nsmap)
                        if id_elem is not None:
                            id_ = id_elem.text
                    descriptor_elem = worker_elem.find("bsvc:Worker_Descriptor", nsmap)
                    descriptor = descriptor_elem.text if descriptor_elem is not None else None
                    worker_data_elem = worker_elem.find("bsvc:Worker_Data", nsmap)
                    personal_data = (
                        self._element_to_dict(worker_data_elem.find("bsvc:Personal_Data", nsmap))
                        if worker_data_elem is not None
                        else None
                    )
                    employment_data = (
                        self._element_to_dict(worker_data_elem.find("bsvc:Employment_Data", nsmap))
                        if worker_data_elem is not None
                        else None
                    )
                    compensation_data = (
                        self._element_to_dict(worker_data_elem.find("bsvc:Compensation_Data", nsmap))
                        if worker_data_elem is not None
                        else None
                    )
                    organization_data = (
                        self._element_to_dict(worker_data_elem.find("bsvc:Organization_Data", nsmap))
                        if worker_data_elem is not None
                        else None
                    )
                    worker = {
                        "id": id_,
                        "descriptor": descriptor,
                        "personalData": personal_data,
                        "employmentData": employment_data,
                        "compensationData": compensation_data,
                        "organizationData": organization_data,
                    }

            output_data = {"worker": worker}
            output_str = json.dumps(output_data, indent=2)
            return ToolResult(success=True, output=output_str, data=output_data)

        except ET.ParseError as e:
            return ToolResult(success=False, output="", error=f"XML parse error: {str(e)}")
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")