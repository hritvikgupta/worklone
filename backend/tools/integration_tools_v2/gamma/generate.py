from typing import Any, Dict
import httpx
from backend.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class GammaGenerateTool(BaseTool):
    name = "gamma_generate"
    description = "Generate a new Gamma presentation, document, webpage, or social post from text input."
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

    async def _resolve_api_key(self, context: dict | None) -> str:
        connection = await resolve_oauth_connection(
            "gamma",
            context=context,
            context_token_keys=("gamma_api_key",),
            env_token_keys=("GAMMA_API_KEY",),
            placeholder_predicate=self._is_placeholder_token,
            allow_refresh=False,
        )
        return connection.access_token

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "inputText": {
                    "type": "string",
                    "description": "Text and image URLs used to generate your gamma (1-100,000 tokens)"
                },
                "textMode": {
                    "type": "string",
                    "description": "How to handle input text: generate (AI expands), condense (AI summarizes), or preserve (keep as-is)"
                },
                "format": {
                    "type": "string",
                    "description": "Output format: presentation, document, webpage, or social (default: presentation)"
                },
                "themeId": {
                    "type": "string",
                    "description": "Custom Gamma workspace theme ID (use List Themes to find available themes)"
                },
                "numCards": {
                    "type": "number",
                    "description": "Number of cards/slides to generate (1-60 for Pro, 1-75 for Ultra; default: 10)"
                },
                "cardSplit": {
                    "type": "string",
                    "description": "How to split content into cards: auto or inputTextBreaks (default: auto)"
                },
                "cardDimensions": {
                    "type": "string",
                    "description": "Card aspect ratio. Presentation: fluid, 16x9, 4x3. Document: fluid, pageless, letter, a4. Social: 1x1, 4x5, 9x16"
                },
                "additionalInstructions": {
                    "type": "string",
                    "description": "Additional instructions for the AI generation (max 2000 chars)"
                },
                "exportAs": {
                    "type": "string",
                    "description": "Automatically export the generated gamma as pdf or pptx"
                },
                "folderIds": {
                    "type": "string",
                    "description": "Comma-separated folder IDs to store the generated gamma in"
                },
                "textAmount": {
                    "type": "string",
                    "description": "Amount of text per card: brief, medium, detailed, or extensive"
                },
                "textTone": {
                    "type": "string",
                    "description": "Tone of the generated text, e.g. \"professional\", \"casual\" (max 500 chars)"
                },
                "textAudience": {
                    "type": "string",
                    "description": "Target audience for the generated text, e.g. \"executives\", \"students\" (max 500 chars)"
                },
                "textLanguage": {
                    "type": "string",
                    "description": "Language code for the generated text (default: en)"
                },
                "imageSource": {
                    "type": "string",
                    "description": "Where to source images: aiGenerated, pictographic, unsplash, webAllImages, webFreeToUse, webFreeToUseCommercially, giphy, placeholder, or noImages"
                },
                "imageModel": {
                    "type": "string",
                    "description": "AI image generation model to use when imageSource is aiGenerated"
                },
                "imageStyle": {
                    "type": "string",
                    "description": "Style directive for AI-generated images, e.g. \"watercolor\", \"photorealistic\" (max 500 chars)"
                }
            },
            "required": ["inputText", "textMode"]
        }

    def _build_body(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        body: Dict[str, Any] = {
            "inputText": parameters["inputText"],
            "textMode": parameters["textMode"],
        }
        for key in ["format", "themeId", "numCards", "cardSplit", "additionalInstructions", "exportAs"]:
            if key in parameters and parameters[key] is not None:
                body[key] = parameters[key]
        if "folderIds" in parameters and parameters["folderIds"]:
            body["folderIds"] = [fid.strip() for fid in str(parameters["folderIds"]).split(",")]
        text_options: Dict[str, Any] = {}
        for key in ["textAmount", "textTone", "textAudience", "textLanguage"]:
            if key in parameters and parameters[key] is not None:
                text_options[key] = parameters[key]
        if text_options:
            body["textOptions"] = text_options
        image_options: Dict[str, Any] = {}
        for key in ["imageSource", "imageModel", "imageStyle"]:
            if key in parameters and parameters[key] is not None:
                image_options[key] = parameters[key]
        if image_options:
            body["imageOptions"] = image_options
        card_options: Dict[str, Any] = {}
        if "cardDimensions" in parameters and parameters["cardDimensions"] is not None:
            card_options["dimensions"] = parameters["cardDimensions"]
        if card_options:
            body["cardOptions"] = card_options
        return body

    async def execute(self, parameters: dict, context: dict | None = None) -> ToolResult:
        api_key = await self._resolve_api_key(context)
        if self._is_placeholder_token(api_key):
            return ToolResult(success=False, output="", error="Gamma API key not configured.")
        headers = {
            "Content-Type": "application/json",
            "X-API-KEY": api_key,
        }
        url = "https://public-api.gamma.app/v1.0/generations"
        body = self._build_body(parameters)
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=body)
                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")