from typing import Any, Dict
import httpx
from backend.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class LinearUpdateCustomerTool(BaseTool):
    name = "linear_update_customer"
    description = "Update a customer in Linear"
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="LINEAR_ACCESS_TOKEN",
                description="Access token",
                env_var="LINEAR_ACCESS_TOKEN",
                required=True,
                auth_type="oauth",
            )
        ]

    async def _resolve_access_token(self, context: dict | None) -> str:
        connection = await resolve_oauth_connection(
            "linear",
            context=context,
            context_token_keys=("linear_token",),
            env_token_keys=("LINEAR_ACCESS_TOKEN",),
            placeholder_predicate=self._is_placeholder_token,
            allow_refresh=True,
        )
        return connection.access_token

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "customerId": {
                    "type": "string",
                    "description": "Customer ID to update",
                },
                "name": {
                    "type": "string",
                    "description": "Updated customer name",
                },
                "domains": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Updated domains",
                },
                "externalIds": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Updated external IDs",
                },
                "logoUrl": {
                    "type": "string",
                    "description": "Updated logo URL",
                },
                "ownerId": {
                    "type": "string",
                    "description": "Updated owner user ID",
                },
                "revenue": {
                    "type": "number",
                    "description": "Updated annual revenue",
                },
                "size": {
                    "type": "number",
                    "description": "Updated organization size",
                },
                "statusId": {
                    "type": "string",
                    "description": "Updated customer status ID",
                },
                "tierId": {
                    "type": "string",
                    "description": "Updated customer tier ID",
                },
            },
            "required": ["customerId"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)

        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }

        url = "https://api.linear.app/graphql"

        input_ = {}
        name = parameters.get("name")
        if name is not None and name != "":
            input_["name"] = name
        domains = parameters.get("domains")
        if domains is not None and isinstance(domains, list) and len(domains) > 0:
            input_["domains"] = domains
        external_ids = parameters.get("externalIds")
        if external_ids is not None and isinstance(external_ids, list) and len(external_ids) > 0:
            input_["externalIds"] = external_ids
        logo_url = parameters.get("logoUrl")
        if logo_url is not None and logo_url != "":
            input_["logoUrl"] = logo_url
        owner_id = parameters.get("ownerId")
        if owner_id is not None and owner_id != "":
            input_["ownerId"] = owner_id
        revenue = parameters.get("revenue")
        if revenue is not None:
            input_["revenue"] = revenue
        size_ = parameters.get("size")
        if size_ is not None:
            input_["size"] = size_
        status_id = parameters.get("statusId")
        if status_id is not None and status_id != "":
            input_["statusId"] = status_id
        tier_id = parameters.get("tierId")
        if tier_id is not None and tier_id != "":
            input_["tierId"] = tier_id

        customer_id = parameters["customerId"]

        body = {
            "query": """
mutation CustomerUpdate($id: String!, $input: CustomerUpdateInput!) {
  customerUpdate(id: $id, input: $input) {
    success
    customer {
      id
      name
      domains
      externalIds
      logoUrl
      slugId
      approximateNeedCount
      revenue
      size
      createdAt
      updatedAt
      archivedAt
    }
  }
}
            """.strip(),
            "variables": {
                "id": customer_id,
                "input": input_,
            },
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=body)

                if response.status_code != 200:
                    return ToolResult(success=False, output="", error=response.text)

                data = response.json()

                if data.get("errors"):
                    error_msg = data["errors"][0].get("message", "Failed to update customer") if data["errors"] else "Failed to update customer"
                    return ToolResult(success=False, output={}, error=error_msg)

                result = data.get("data", {}).get("customerUpdate", {})
                return ToolResult(
                    success=result.get("success", False),
                    output={"customer": result.get("customer", {})},
                    data=data,
                )

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")