import asyncio
from typing import Any

import httpx

from backend.core.tools.system_tools.base import BaseTool, CredentialRequirement, ToolResult


class VeoVideoTool(BaseTool):
    name = "video_veo"
    description = "Generate videos using Google Veo."
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return (
            not normalized
            or normalized.startswith("your-")
            or "replace-me" in normalized
            or normalized == "ya29...."
        )

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="GOOGLE_API_KEY",
                description="Google AI Studio API key for Veo",
                env_var="GOOGLE_API_KEY",
                required=True,
                auth_type="api_key",
            )
        ]

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "prompt": {
                    "type": "string",
                    "description": "Text prompt describing the video to generate.",
                },
                "model": {
                    "type": "string",
                    "description": "Veo model name (default: veo-2.0-generate-001).",
                },
                "aspectRatio": {
                    "type": "string",
                    "description": "Aspect ratio such as 16:9, 9:16, or 1:1.",
                },
                "durationSeconds": {
                    "type": "number",
                    "description": "Optional requested duration in seconds.",
                },
                "imageUrl": {
                    "type": "string",
                    "description": "Optional public image URL for image-to-video generation.",
                },
            },
            "required": ["prompt"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        api_key = ""
        if context:
            api_key = str(context.get("GOOGLE_API_KEY") or context.get("google_api_key") or "").strip()
        if self._is_placeholder_token(api_key):
            return ToolResult(success=False, output="", error="Google API key not configured.")

        model = parameters.get("model", "veo-2.0-generate-001")
        prompt = parameters["prompt"]
        aspect_ratio = parameters.get("aspectRatio")
        duration_seconds = parameters.get("durationSeconds")
        image_url = parameters.get("imageUrl")

        body: dict[str, Any] = {
            "prompt": prompt,
        }
        if aspect_ratio:
            body["aspectRatio"] = aspect_ratio
        if duration_seconds is not None:
            body["durationSeconds"] = duration_seconds
        if image_url:
            body["image"] = {"uri": image_url}

        create_url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/{model}:predictLongRunning"
            f"?key={api_key}"
        )

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(create_url, json=body)
                if response.status_code not in {200, 201}:
                    return ToolResult(success=False, output="", error=response.text)

                operation = response.json()
                operation_name = operation.get("name")
                if not operation_name:
                    return ToolResult(success=False, output="", error="No operation name returned by Veo API.")

                poll_url = f"https://generativelanguage.googleapis.com/v1beta/{operation_name}?key={api_key}"
                for _ in range(60):
                    await asyncio.sleep(5)
                    poll_response = await client.get(poll_url)
                    if poll_response.status_code != 200:
                        return ToolResult(success=False, output="", error=poll_response.text)

                    poll_data = poll_response.json()
                    if poll_data.get("done"):
                        if "error" in poll_data:
                            return ToolResult(success=False, output="", error=str(poll_data["error"]))

                        result = poll_data.get("response", {})
                        video_url = (
                            result.get("video", {}).get("uri")
                            or result.get("generatedVideo", {}).get("uri")
                            or result.get("outputUri")
                        )
                        output = video_url or str(result)
                        return ToolResult(success=True, output=output, data=poll_data)

                return ToolResult(success=False, output="", error="Veo video generation timed out.")
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
