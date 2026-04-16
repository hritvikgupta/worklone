from typing import Any, Dict
import httpx
import base64
import hashlib
import secrets
import re
import xml.etree.ElementTree as ET
from datetime import datetime
from backend.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class WorkdayUpdateWorkerTool(BaseTool):
    name = "workday_update_worker"
    description = "Update fields on an existing worker record in Workday."
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def _xml_escape(self, text: str) -> str:
        return (
            text.replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;")
                .replace('"', "&quot;")
                .replace("'", "&apos;")
        )

    def _to_workday_element_name(self, key: str) -> str:
        s = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", key)
        return s.title()

    def _dict_to_xml(self, data: Any, ns: str = "bsvc") -> str:
        if isinstance(data, str):
            return self._xml_escape(data)
        elif isinstance(data, bool):
            return "true" if data else "false"
        elif isinstance(data, (int, float)):
            return str(data)
        elif isinstance(data, dict):
            children = []
            for k, v in data.items():
                elem_name = self._to_workday_element_name(k)
                children.append(f"<{ns}:{elem_name}>{self._dict_to_xml(v, ns)}</{ns}:{elem_name}>")
            return "".join(children)
        elif isinstance(data, list):
            children = []
            for item in data:
                children.append(self._dict_to_xml(item, ns))
            return "".join(children)
        else:
            return self._xml_escape(str(data))

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="workday_tenant_url",
                description="Workday instance URL (e.g., https://wd5-impl-services1.workday.com)",
                env_var="WORKDAY_TENANT_URL",
                required=True,
                auth_type="api_key",
            ),
            CredentialRequirement(
                key="workday_tenant",
                description="Workday tenant name",
                env_var="WORKDAY_TENANT",
                required=True,
                auth_type="api_key",
            ),
            CredentialRequirement(
                key="workday_username",
                description="Integration System User username",
                env_var="WORKDAY_USERNAME",
                required=True,
                auth_type="api_key",
            ),
            CredentialRequirement(
                key="workday_password",
                description="Integration System User password",
                env_var="WORKDAY_PASSWORD",
                required=True,
                auth_type="api_key",
            ),
        ]

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "workerId": {
                    "type": "string",
                    "description": "Worker ID to update",
                },
                "fields": {
                    "type": "object",
                    "description": "Fields to update as JSON (e.g., {\"businessTitle\": \"Senior Engineer\", \"primaryWorkEmail\": \"new@company.com\"})",
                },
            },
            "required": ["workerId", "fields"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        tenant_url = context.get("workday_tenant_url") if context else None
        tenant = context.get("workday_tenant") if context else None
        username = context.get("workday_username") if context else None
        password = context.get("workday_password") if context else None

        if self._is_placeholder_token(tenant_url or ""):
            return ToolResult(success=False, output="", error="Workday tenant URL not configured.")
        if self._is_placeholder_token(tenant or ""):
            return ToolResult(success=False, output="", error="Workday tenant not configured.")
        if self._is_placeholder_token(username or ""):
            return ToolResult(success=False, output="", error="Workday username not configured.")
        if self._is_placeholder_token(password or ""):
            return ToolResult(success=False, output="", error="Workday password not configured.")

        worker_id = parameters.get("workerId")
        fields = parameters.get("fields", {})
        if not worker_id:
            return ToolResult(success=False, output="", error="workerId is required.")

        url = f"{tenant_url.rstrip('/')}/ccx/service/{tenant}/Human_Resources"

        nonce_bytes = secrets.token_bytes(32)
        nonce = base64.b64encode(nonce_bytes).decode("ascii")
        created = datetime.utcnow().replace(microsecond=0).isoformat() + "Z"
        password_digest_input = nonce.encode("ascii") + created.encode("ascii") + password.encode("utf-8")
        digest = base64.b64encode(hashlib.sha1(password_digest_input).digest()).decode("ascii")

        personal_info_xml = self._dict_to_xml(fields)

        soap_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<env:Envelope xmlns:env="http://www.w3.org/2003/05/soap-envelope"
              xmlns:wsse="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-secext-1.0.xsd"
              xmlns:wsu="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-utility-1.0.xsd">
  <env:Header>
    <wsse:Security env:mustUnderstand="1">
      <wsse:UsernameToken>
        <wsse:Username>{self._xml_escape(username)}</wsse:Username>
        <wsse:Password Type="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-username-token-profile-1.0#PasswordDigest">{digest}</wsse:Password>
        <wsu:Nonce EncodingType="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-soap-message-security-1.0#Base64Binary">{nonce}</wsu:Nonce>
        <wsu:Created>{created}</wsu:Created>
      </wsse:UsernameToken>
    </wsse:Security>
  </env:Header>
  <env:Body>
    <bsvc:Change_Personal_Information_Request bsvc:version="v50.0"
        xmlns:bsvc="urn:com.workday/bsvc"
        xmlns:wd="urn:com.workday/bsvc">
      <bsvc:Business_Process_Parameters>
        <bsvc:Auto_Complete>true</bsvc:Auto_Complete>
        <bsvc:Run_Now>true</bsvc:Run_Now>
      </bsvc:Business_Process_Parameters>
      <bsvc:Change_Personal_Information_Data>
        <bsvc:Person_Reference>
          <wd:ID wd:type="Employee_ID">{self._xml_escape(worker_id)}</wd:ID>
        </bsvc:Person_Reference>
        <bsvc:Personal_Information_Data>
          {personal_info_xml}
        </bsvc:Personal_Information_Data>
      </bsvc:Change_Personal_Information_Data>
    </bsvc:Change_Personal_Information_Request>
  </env:Body>
</env:Envelope>"""

        headers = {
            "Content-Type": "text/xml; charset=utf-8",
            "SOAPAction": "Change_Personal_Information",
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, content=soap_xml)

                if response.status_code == 200:
                    try:
                        tree = ET.fromstring(response.text)
                        ns = {
                            "env": "http://www.w3.org/2003/05/soap-envelope",
                            "bsvc": "urn:com.workday/bsvc",
                            "wd": "urn:com.workday/bsvc",
                        }
                        event_elem = tree.find(".//bsvc:Personal_Information_Change_Event_Reference/wd:ID", ns)
                        event_id = event_elem.text.strip() if event_elem is not None and event_elem.text else "unknown"
                    except ET.ParseError:
                        event_id = "unknown"
                    data = {
                        "eventId": event_id,
                        "workerId": worker_id,
                    }
                    return ToolResult(success=True, output=response.text, data=data)
                else:
                    return ToolResult(success=False, output="", error=response.text)
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")