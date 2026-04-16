from typing import Any, Dict
import httpx
import base64
import hashlib
import secrets
from datetime import datetime
import xml.etree.ElementTree as ET
from backend.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class WorkdayGetCompensationTool(BaseTool):
    name = "Get Workday Compensation"
    description = "Retrieve compensation plan details for a specific worker."
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
                "workerId": {
                    "type": "string",
                    "description": "Worker ID to retrieve compensation data for",
                },
            },
            "required": ["tenantUrl", "tenant", "username", "password", "workerId"],
        }

    def _create_username_token(self, username: str, password: str) -> str:
        created = datetime.utcnow().isoformat(timespec="seconds") + "Z"
        nonce_bytes = secrets.token_bytes(32)
        nonce_b64 = base64.b64encode(nonce_bytes).decode("utf-8")
        msg = nonce_bytes + created.encode("utf-8") + password.encode("utf-8")
        digest_bytes = hashlib.sha1(msg).digest()
        digest_b64 = base64.b64encode(digest_bytes).decode("utf-8")
        return f'''<wsse:Security soapenv:mustUnderstand="1" xmlns:wsse="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-secext-1.0.xsd" xmlns:wsu="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-utility-1.0.xsd">
<wsse:UsernameToken wsu:Id="UsernameToken-1">
<wsse:Username>{username}</wsse:Username>
<wsse:Password Type="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-secext-1.0.xsd#PasswordDigest">{digest_b64}</wsse:Password>
<wsse:Nonce EncodingType="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-secext-1.0.xsd#Base64Binary">{nonce_b64}</wsse:Nonce>
<wsu:Created>{created}</wsu:Created>
</wsse:UsernameToken>
</wsse:Security>'''

    def _extract_ref_id(self, ref_elem: ET.Element) -> str | None:
        id_elem_tag = "{urn:com.workday/bsvc}ID"
        id_elem = ref_elem.find(id_elem_tag)
        if id_elem is not None and id_elem.text:
            return id_elem.text.strip()
        return ref_elem.get("{urn:com.workday/bsvc}ref") or ref_elem.get("wd:ref") or ref_elem.get("ref")

    def _extract_compensation_plan(self, pa_elem: ET.Element) -> dict | None:
        bsvc_ns = "urn:com.workday/bsvc"
        comp_plan_ref_tag = f"{{{bsvc_ns}}}Compensation_Plan_Reference"
        currency_ref_tag = f"{{{bsvc_ns}}}Currency_Reference"
        frequency_ref_tag = f"{{{bsvc_ns}}}Frequency_Reference"
        amount_tag = f"{{{bsvc_ns}}}Amount"
        per_unit_tag = f"{{{bsvc_ns}}}Per_Unit_Amount"
        target_tag = f"{{{bsvc_ns}}}Individual_Target_Amount"

        comp_plan_ref = pa_elem.find(comp_plan_ref_tag)
        if comp_plan_ref is None:
            return None

        plan_id = self._extract_ref_id(comp_plan_ref)
        plan_name = (
            comp_plan_ref.get("wd:Descriptor")
            or comp_plan_ref.get("Descriptor")
            or comp_plan_ref.get("{urn:com.workday/bsvc}Descriptor")
        )

        amount_elem = pa_elem.find(amount_tag)
        amount = float(amount_elem.text) if amount_elem is not None and amount_elem.text else None

        per_unit_elem = pa_elem.find(per_unit_tag)
        per_unit = float(per_unit_elem.text) if per_unit_elem is not None and per_unit_elem.text else None

        target_elem = pa_elem.find(target_tag)
        target = float(target_elem.text) if target_elem is not None and target_elem.text else None

        final_amount = amount or per_unit or target

        currency_ref = pa_elem.find(currency_ref_tag)
        currency = self._extract_ref_id(currency_ref) if currency_ref is not None else None

        frequency_ref = pa_elem.find(frequency_ref_tag)
        frequency = self._extract_ref_id(frequency_ref) if frequency_ref is not None else None

        return {
            "id": plan_id,
            "planName": plan_name,
            "amount": final_amount,
            "currency": currency,
            "frequency": frequency,
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        try:
            tenant_url = parameters["tenantUrl"]
            tenant = parameters["tenant"]
            username = parameters["username"]
            password = parameters["password"]
            worker_id = parameters["workerId"]

            soap_url = f"{tenant_url.rstrip('/')}/ccx/service/{tenant}/Human_Resources"
            security_header = self._create_username_token(username, password)
            bsvc_ns = "urn:com.workday/bsvc"
            wd_ns = "urn:com.workday/bsvc"
            soap_ns = "http://schemas.xmlsoap.org/soap/envelope/"
            body_content = f'''<bsvc:Get_Workers_Request xmlns:bsvc="{bsvc_ns}" xmlns:wd="{wd_ns}">
  <bsvc:Request_References>
    <bsvc:Worker_Reference>
      <wd:ID wd:type="Employee_ID">{worker_id}</wd:ID>
    </bsvc:Worker_Reference>
  </bsvc:Request_References>
  <bsvc:Response_Group>
    <bsvc:Include_Reference>true</bsvc:Include_Reference>
    <bsvc:Include_Compensation>true</bsvc:Include_Compensation>
  </bsvc:Response_Group>
</bsvc:Get_Workers_Request>'''
            full_xml = f'''<soapenv:Envelope xmlns:soapenv="{soap_ns}">
  <soapenv:Header>
    {security_header}
  </soapenv:Header>
  <soapenv:Body>
    {body_content}
  </soapenv:Body>
</soapenv:Envelope>'''

            headers = {
                "Content-Type": "text/xml; charset=utf-8",
            }

            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(soap_url, headers=headers, content=full_xml.encode("utf-8"))

            if response.status_code != 200:
                return ToolResult(
                    success=False,
                    output="",
                    error=f"HTTP {response.status_code}: {response.text[:1000]}",
                )

            tree = ET.fromstring(response.text)
            soap_body = tree.find(f'{{{soap_ns}}}Body')
            if soap_body is None:
                return ToolResult(success=False, output="", error="Invalid SOAP response: no body")

            soap_fault_tag = f"{{{soap_ns}}}Fault"
            fault = soap_body.find(soap_fault_tag)
            if fault is not None:
                reason_tag = f"{{{soap_ns}}}Reason"
                text_tag = f"{{{soap_ns}}}Text"
                reason = fault.find(reason_tag)
                fault_text_elem = reason.find(text_tag) if reason is not None else None
                error_msg = fault_text_elem.text if fault_text_elem is not None else "SOAP Fault occurred"
                return ToolResult(success=False, output="", error=error_msg)

            bsvc_get_workers_resp_tag = f"{{{bsvc_ns}}}Get_Workers_Response"
            get_workers_resp = soap_body.find(bsvc_get_workers_resp_tag)
            if get_workers_resp is None:
                return ToolResult(success=False, output="", error="No Get_Workers_Response in SOAP body")

            bsvc_response_data_tag = f"{{{bsvc_ns}}}Response_Data"
            response_data = get_workers_resp.find(bsvc_response_data_tag)
            if response_data is None:
                return ToolResult(success=True, output="No response data", data={"compensationPlans": []})

            bsvc_worker_tag = f"{{{bsvc_ns}}}Worker"
            workers = response_data.findall(bsvc_worker_tag)
            if not workers:
                return ToolResult(success=True, output="No workers found", data={"compensationPlans": []})

            worker = workers[0]
            bsvc_worker_data_tag = f"{{{bsvc_ns}}}Worker_Data"
            worker_data = worker.find(bsvc_worker_data_tag)
            if worker_data is None:
                return ToolResult(success=True, output="No worker data", data={"compensationPlans": []})

            bsvc_compensation_data_tag = f"{{{bsvc_ns}}}Compensation_Data"
            compensation_data = worker_data.find(bsvc_compensation_data_tag)
            if compensation_data is None:
                return ToolResult(success=True, output="No compensation data", data={"compensationPlans": []})

            plan_type_keys = [
                "Employee_Base_Pay_Plan_Assignment_Data",
                "Employee_Salary_Unit_Plan_Assignment_Data",
                "Employee_Bonus_Plan_Assignment_Data",
                "Employee_Allowance_Plan_Assignment_Data",
                "Employee_Commission_Plan_Assignment_Data",
                "Employee_Stock_Plan_Assignment_Data",
                "Employee_Period_Salary_Plan_Assignment_Data",
            ]
            compensation_plans = []
            for ptk in plan_type_keys:
                ptk_tag = f"{{{bsvc_ns}}}{ptk}"
                plan_assignments = compensation_data.findall(ptk_tag)
                for pa_elem in plan_assignments:
                    plan = self._extract_compensation_plan(pa_elem)
                    if plan is not None:
                        compensation_plans.append(plan)

            return ToolResult(
                success=True,
                output="Compensation plans retrieved successfully",
                data={"compensationPlans": compensation_plans},
            )

        except httpx.TimeoutException:
            return ToolResult(success=False, output="", error="Request to Workday timed out")
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")