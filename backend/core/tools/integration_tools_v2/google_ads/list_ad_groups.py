from typing import Any, Dict
import httpx
import json
import os
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class GoogleAdsListAdGroupsTool(BaseTool):
    name = "google_ads_list_ad_groups"
    description = "List ad groups in a Google Ads campaign"
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="GOOGLE_ADS_ACCESS_TOKEN",
                description="OAuth access token for the Google Ads API",
                env_var="GOOGLE_ADS_ACCESS_TOKEN",
                required=True,
                auth_type="oauth",
            ),
            CredentialRequirement(
                key="GOOGLE_ADS_DEVELOPER_TOKEN",
                description="Google Ads API developer token",
                env_var="GOOGLE_ADS_DEVELOPER_TOKEN",
                required=True,
                auth_type="api_key",
            ),
        ]

    async def _resolve_access_token(self, context: dict | None) -> str:
        connection = await resolve_oauth_connection(
            "google-ads",
            context=context,
            context_token_keys=("accessToken", "GOOGLE_ADS_ACCESS_TOKEN"),
            env_token_keys=("GOOGLE_ADS_ACCESS_TOKEN",),
            placeholder_predicate=self._is_placeholder_token,
            allow_refresh=True,
        )
        return connection.access_token

    def _resolve_developer_token(self, context: dict | None) -> str:
        candidates = []
        if context:
            candidates.append(context.get("developerToken"))
            candidates.append(context.get("GOOGLE_ADS_DEVELOPER_TOKEN"))
        candidates.append(os.environ.get("GOOGLE_ADS_DEVELOPER_TOKEN", ""))
        for token in candidates:
            if token and not self._is_placeholder_token(token):
                return token
        return ""

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "customerId": {
                    "type": "string",
                    "description": "Google Ads customer ID (numeric, no dashes)",
                },
                "managerCustomerId": {
                    "type": "string",
                    "description": "Manager account customer ID (if accessing via manager account)",
                },
                "campaignId": {
                    "type": "string",
                    "description": "Campaign ID to list ad groups for",
                },
                "status": {
                    "type": "string",
                    "description": "Filter by ad group status (ENABLED, PAUSED, REMOVED)",
                },
                "limit": {
                    "type": "number",
                    "description": "Maximum number of ad groups to return",
                },
            },
            "required": ["customerId", "campaignId"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        developer_token = self._resolve_developer_token(context)

        if self._is_placeholder_token(access_token) or self._is_placeholder_token(developer_token):
            return ToolResult(success=False, output="", error="Access token or developer token not configured.")

        try:
            customer_id_raw = parameters["customerId"]
            customer_id = str(customer_id_raw).replace("-", "")
            if not customer_id.isdigit():
                raise ValueError("customerId must be numeric (no dashes).")

            campaign_id_raw = parameters["campaignId"]
            campaign_id = str(campaign_id_raw).replace("-", "")
            if not campaign_id.isdigit():
                raise ValueError("campaignId must be numeric (no dashes).")
        except (KeyError, ValueError) as e:
            return ToolResult(success=False, output="", error=f"Invalid parameters: {str(e)}")

        url = f"https://googleads.googleapis.com/v19/customers/{customer_id}/googleAds:search"

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
            "developer-token": developer_token,
        }

        manager_customer_id = parameters.get("managerCustomerId")
        if manager_customer_id:
            manager_customer_id = str(manager_customer_id).replace("-", "")
            if not manager_customer_id.isdigit():
                return ToolResult(success=False, output="", error="managerCustomerId must be numeric (no dashes).")
            headers["login-customer-id"] = manager_customer_id

        query = "SELECT ad_group.id, ad_group.name, ad_group.status, ad_group.type, campaign.id, campaign.name FROM ad_group"
        conditions = [f"campaign.id = {campaign_id}"]

        status = parameters.get("status")
        if status:
            status_upper = str(status).strip().upper()
            if status_upper not in ("ENABLED", "PAUSED", "REMOVED"):
                return ToolResult(success=False, output="", error=f"Invalid ad group status: {status}. Must be ENABLED, PAUSED, or REMOVED.")
            conditions.append(f"ad_group.status = '{status_upper}'")
        else:
            conditions.append("ad_group.status != 'REMOVED'")

        query += f" WHERE {' AND '.join(conditions)}"
        query += " ORDER BY ad_group.name"

        limit = parameters.get("limit")
        if limit is not None:
            try:
                limit_val = int(limit)
                if limit_val <= 0:
                    raise ValueError("limit must be positive integer")
                query += f" LIMIT {limit_val}"
            except (ValueError, TypeError):
                return ToolResult(success=False, output="", error="Invalid limit value. Must be positive integer.")

        body = {"query": query}

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=body)

                if 200 <= response.status_code < 300:
                    data = response.json()
                    results = data.get("results", [])
                    ad_groups = []
                    for r in results:
                        ad_group = r.get("adGroup", {})
                        campaign = r.get("campaign", {})
                        ad_groups.append({
                            "id": ad_group.get("id", ""),
                            "name": ad_group.get("name", ""),
                            "status": ad_group.get("status", ""),
                            "type": ad_group.get("type"),
                            "campaignId": campaign.get("id", ""),
                            "campaignName": campaign.get("name"),
                        })
                    transformed = {
                        "adGroups": ad_groups,
                        "totalCount": len(ad_groups),
                    }
                    return ToolResult(
                        success=True,
                        output=json.dumps(transformed),
                        data=transformed,
                    )
                else:
                    try:
                        data = response.json()
                    except:
                        data = {}
                    error_message = data.get("error", {}).get("message", response.text)
                    details = data.get("error", {}).get("details", [])
                    if isinstance(details, list) and details:
                        first_detail = details[0]
                        if isinstance(first_detail, dict) and "errors" in first_detail:
                            detail_errors = first_detail["errors"]
                            if isinstance(detail_errors, list) and detail_errors:
                                error_message = detail_errors[0].get("message", error_message)
                    return ToolResult(success=False, output="", error=error_message)

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")