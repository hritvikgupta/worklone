from typing import Any, Dict
import httpx
from worklone_employee.tools.base import BaseTool, ToolResult, CredentialRequirement


class LinearCreateCustomerTool(BaseTool):
    name = "linear_create_customer"
    description = "Create a new customer in Linear"
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
                "name": {
                    "type": "string",
                    "description": "Customer name",
                },
                "domains": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Domains associated with this customer",
                },
                "externalIds": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "External IDs from other systems",
                },
                "logoUrl": {
                    "type": "string",
                    "description": "Customer's logo URL",
                },
                "ownerId": {
                    "type": "string",
                    "description": "ID of the user who owns this customer",
                },
                "revenue": {
                    "type": "number",
                    "description": "Annual revenue from this customer",
                },
                "size": {
                    "type": "number",
                    "description": "Size of the customer organization",
                },
                "statusId": {
                    "type": "string",
                    "description": "Customer status ID",
                },
                "tierId": {
                    "type": "string",
                    "description": "Customer tier ID",
                },
            },
            "required": ["name"],
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

        input_dict: Dict[str, Any] = {
            "name": parameters["name"],
        }

        domains = parameters.get("domains")
        if domains is not None and isinstance(domains, list) and len(domains) > 0:
            input_dict["domains"] = domains

        external_ids = parameters.get("externalIds")
        if external_ids is not None and isinstance(external_ids, list) and len(external_ids) > 0:
            input_dict["externalIds"] = external_ids

        logo_url = parameters.get("logoUrl")
        if logo_url is not None and logo_url != "":
            input_dict["logoUrl"] = logo_url

        owner_id = parameters.get("ownerId")
        if owner_id is not None and owner_id != "":
            input_dict["ownerId"] = owner_id

        revenue = parameters.get("revenue")
        if revenue is not None:
            input_dict["revenue"] = revenue

        size = parameters.get("size")
        if size is not None:
            input_dict["size"] = size

        status_id = parameters.get("statusId")
        if status_id is not None and status_id != "":
            input_dict["statusId"] = status_id

        tier_id = parameters.get("tierId")
        if tier_id is not None and tier_id != "":
            input_dict["tierId"] = tier_id

        query = """
          mutation CustomerCreate($input: CustomerCreateInput!) {
            customerCreate(input: $input) {
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
        """

        body = {
            "query": query,
            "variables": {
                "input": input_dict,
            },
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=body)

                if response.status_code != 200:
                    return ToolResult(success=False, output="", error=response.text)

                data = response.json()

                if "errors" in data and data["errors"]:
                    error_msg = data["errors"][0].get("message", "Failed to create customer") if data["errors"] else "Unknown error"
                    return ToolResult(success=False, output="", error=error_msg)

                result = data.get("data", {}).get("customerCreate", {})
                if not result.get("success", False):
                    return ToolResult(success=False, output="", error="Customer creation was not successful")

                return ToolResult(success=True, output=response.text, data=data)

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")