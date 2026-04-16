from typing import Any, Dict
import httpx
import os
from backend.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class GammaGenerateFromTemplateTool(BaseTool):
    name = "gamma_generate_from_template"
    description = "Generate a new Gamma by adapting an existing template with a prompt."
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="GAMMA_API_KEY",
                description="Gamma API key",
                env_var="GAMMA_API_KEY",
                required=True,
                auth_type="api_key",
            )
        ]

    def _resolve_api_key(self, context: dict | None) -> str:
        api_key = context.get("GAMMA_API_KEY") if context else None
        if not api_key:
            api_key = os.getenv("GAMMA_API_KEY")
        return api_key or ""

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "gammaId": {
                    "type": "string",
                    "description": "The ID of the template gamma to adapt",
                },
                "prompt": {
                    "type": "string",
                    "description": "Instructions for how to adapt the template (1-100,000 tokens)",
                },
                "themeId": {
                    "type": "string",
                    "description": "Custom Gamma workspace theme ID to apply",
                },
                "exportAs": {
                    "type": "string",
                    "description": "Automatically export the generated gamma as pdf or pptx",
                },
                "folderIds": {
                    "type": "string",
                    "description": "Comma-separated folder IDs to store the generated gamma in",
                },
                "imageModel": {
                    "type": "string",
                    "description": "AI image generation model to use when imageSource is aiGenerated",
                },
                "imageStyle": {
                    "type": "string",
                    "description": 'Style directive for AI-generated images, e.g. "watercolor", "photorealistic" (max 500 chars)',
                },
            },
            "required": ["gammaId", "prompt"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        api_key = self._resolve_api_key(context)

        if self._is_placeholder_token(api_key):
            return ToolResult(success=False, output="", error="API key not configured.")

        headers = {
            "Content-Type": "application/json",
            "X-API-KEY": api_key,
        }

        url = "https://public-api.gamma.app/v1.0/generations/from-template"

        body = {
            "gammaId": parameters["gammaId"],
            "prompt": parameters["prompt"],
        }

        theme_id = parameters.get("themeId")
        if theme_id:
            body["themeId"] = theme_id

        export_as = parameters.get("exportAs")
        if export_as:
            body["exportAs"] = export_as

        folder_ids = parameters.get("folderIds")
        if folder_ids:
            body["folderIds"] = [id.strip() for id in str(folder_ids).split(",")]

        image_options: Dict[str, Any] = {}
        image_model = parameters.get("imageModel")
        if image_model:
            image_options["model"] = image_model
        image_style = parameters.get("imageStyle")
        if image_style:
            image_options["style"] = image_style
        if image_options:
            body["imageOptions"] = image_options

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=body)

                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")