from typing import Any, Dict
import httpx
import json
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class GoogleAdsAdPerformanceTool(BaseTool):
    name = "google_ads_ad_performance"
    description = "Get performance metrics for individual ads over a date range"
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
            context_token_keys=("google_ads_access_token", "provider_token"),
            env_token_keys=("GOOGLE_ADS_ACCESS_TOKEN",),
            placeholder_predicate=self._is_placeholder_token,
            allow_refresh=True,
        )
        return connection.access_token

    async def _resolve_developer_token(self, context: dict | None) -> str:
        connection = await resolve_oauth_connection(
            "google-ads",
            context=context,
            context_token_keys=("google_ads_developer_token",),
            env_token_keys=("GOOGLE_ADS_DEVELOPER_TOKEN",),
            placeholder_predicate=self._is_placeholder_token,
            allow_refresh=False,
        )
        return connection.access_token

    def _build_query(self, parameters: Dict[str, Any]) -> str:
        query = (
            "SELECT ad_group_ad.ad.id, ad_group.id, ad_group.name, "
            "campaign.id, campaign.name, ad_group_ad.ad.type, "
            "metrics.impressions, metrics.clicks, metrics.cost_micros, "
            "metrics.ctr, metrics.conversions, segments.date "
            "FROM ad_group_ad"
        )
        conditions: list[str] = ["ad_group_ad.status != 'REMOVED'"]
        if campaign_id := parameters.get("campaignId"):
            conditions.append(f"campaign.id = {campaign_id}")
        if ad_group_id := parameters.get("adGroupId"):
            conditions.append(f"ad_group.id = {ad_group_id}")
        start_date = parameters.get("startDate")
        end_date = parameters.get("endDate")
        if start_date and end_date:
            conditions.append(f"segments.date BETWEEN '{start_date}' AND '{end_date}'")
        else:
            date_range = parameters.get("dateRange", "LAST_30_DAYS")
            conditions.append(f"segments.date DURING {date_range}")
        query += f" WHERE {' AND '.join(conditions)}"
        query += " ORDER BY metrics.impressions DESC"
        if limit := parameters.get("limit"):
            query += f" LIMIT {limit}"
        return query

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
                    "description": "Filter by campaign ID",
                },
                "adGroupId": {
                    "type": "string",
                    "description": "Filter by ad group ID",
                },
                "dateRange": {
                    "type": "string",
                    "description": "Predefined date range (LAST_7_DAYS, LAST_30_DAYS, THIS_MONTH, LAST_MONTH, TODAY, YESTERDAY)",
                },
                "startDate": {
                    "type": "string",
                    "description": "Custom start date in YYYY-MM-DD format",
                },
                "endDate": {
                    "type": "string",
                    "description": "Custom end date in YYYY-MM-DD format",
                },
                "limit": {
                    "type": "number",
                    "description": "Maximum number of results to return",
                },
            },
            "required": ["customerId"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        developer_token = await self._resolve_developer_token(context)

        if self._is_placeholder_token(access_token) or self._is_placeholder_token(developer_token):
            return ToolResult(success=False, output="", error="Access token or developer token not configured.")

        customer_id = parameters["customerId"]
        url = f"https://googleads.googleapis.com/v19/customers/{customer_id}/googleAds:search"

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
            "developer-token": developer_token,
        }
        manager_customer_id = parameters.get("managerCustomerId")
        if manager_customer_id:
            headers["login-customer-id"] = manager_customer_id

        query = self._build_query(parameters)
        json_body = {"query": query}

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=json_body)

                try:
                    resp_data = response.json()
                except Exception:
                    resp_data = {}

                if response.status_code not in [200, 201, 204]:
                    error_data = resp_data.get("error", {})
                    error_message = error_data.get("message", "")
                    details = error_data.get("details", [])
                    if not error_message and details:
                        errors = details[0].get("errors", []) if details else []
                        if errors:
                            error_message = errors[0].get("message", "")
                    if not error_message:
                        error_message = response.text[:1000] or "Unknown error"
                    return ToolResult(success=False, output="", error=error_message)

                results = resp_data.get("results", [])
                ads = []
                for r in results:
                    metrics = r.get("metrics", {})
                    ad_group = r.get("adGroup", {})
                    ad_group_ad = r.get("adGroupAd", {})
                    ad = r.get("adGroupAd", {}).get("ad", {})
                    segments = r.get("segments", {})
                    campaign = r.get("campaign", {})
                    ads.append({
                        "adId": ad.get("id", ""),
                        "adGroupId": ad_group.get("id", ""),
                        "adGroupName": ad_group.get("name"),
                        "campaignId": campaign.get("id", ""),
                        "campaignName": campaign.get("name"),
                        "adType": ad.get("type"),
                        "impressions": str(metrics.get("impressions", 0)),
                        "clicks": str(metrics.get("clicks", 0)),
                        "costMicros": str(metrics.get("costMicros", 0)),
                        "ctr": metrics.get("ctr"),
                        "conversions": metrics.get("conversions"),
                        "date": segments.get("date"),
                    })

                output_data = {
                    "ads": ads,
                    "totalCount": len(ads),
                }
                return ToolResult(
                    success=True,
                    output=json.dumps(output_data),
                    data=output_data,
                )

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")