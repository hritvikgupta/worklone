from typing import Any, Dict
import httpx
import asyncio
from backend.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class RunwayVideoTool(BaseTool):
    name = "video_runway"
    description = "Generate videos using Runway Gen-4 with world consistency and visual references"
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="RUNWAY_API_KEY",
                description="Runway API key from https://app.runwayml.com/settings/api",
                env_var="RUNWAY_API_KEY",
                required=True,
                auth_type="api_key",
            )
        ]

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "model": {
                    "type": "string",
                    "description": "Runway model: gen-4 (default, higher quality) or gen-4-turbo (faster)",
                },
                "prompt": {
                    "type": "string",
                    "description": "Text prompt describing the video to generate",
                },
                "duration": {
                    "type": "number",
                    "description": "Video duration in seconds (5 or 10, default: 5)",
                },
                "aspectRatio": {
                    "type": "string",
                    "description": "Aspect ratio: 16:9 (landscape), 9:16 (portrait), or 1:1 (square)",
                },
                "resolution": {
                    "type": "string",
                    "description": "Video resolution (720p output). Note: Gen-4 Turbo outputs at 720p natively",
                },
                "visualReference": {
                    "type": "string",
                    "description": "Public HTTPS URL to reference image REQUIRED for Gen-4 (UserFile object). Gen-4 only supports image-to-video, not text-only generation",
                },
            },
            "required": ["prompt", "visualReference"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        api_key = context.get("RUNWAY_API_KEY") if context else None

        if not api_key or self._is_placeholder_token(api_key):
            return ToolResult(success=False, output="", error="Runway API key not configured.")

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        model = parameters.get("model", "gen-4-turbo")
        prompt = parameters.get("prompt")
        duration = parameters.get("duration", 5)
        aspect_ratio = parameters.get("aspectRatio", "16:9")
        resolution = parameters.get("resolution", "720p")
        visual_reference = parameters.get("visualReference")

        if not prompt:
            return ToolResult(success=False, output="", error="Missing required parameter: prompt")
        if not visual_reference:
            return ToolResult(success=False, output="", error="Missing required parameter: visualReference")

        if not isinstance(visual_reference, str):
            return ToolResult(success=False, output="", error="visualReference must be a string (URL to image)")
        image_url = visual_reference.strip()
        if not image_url.startswith("https://"):
            return ToolResult(success=False, output="", error="visualReference must be a public HTTPS URL to an image")

        url = f"https://api.runwayml.com/v1/generations/{model}/image-to-video"

        body = {
            "prompt": prompt,
            "image_url": image_url,
            "duration_seconds": duration,
            "aspect_ratio": aspect_ratio,
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=body)

                if response.status_code != 200:
                    return ToolResult(
                        success=False,
                        output="",
                        error=f"Failed to start video generation: HTTP {response.status_code} - {response.text}",
                    )

                data = response.json()
                if not data.get("success", False):
                    return ToolResult(
                        success=False,
                        output="",
                        error=data.get("error", "Failed to start video generation"),
                    )

                task_id = data.get("data", {}).get("id")
                if not task_id:
                    return ToolResult(success=False, output="", error="No task ID in generation response")

                poll_url = f"https://api.runwayml.com/v1/tasks/{task_id}"
                max_attempts = 120  # ~10 minutes at 5s intervals
                for attempt in range(max_attempts):
                    await asyncio.sleep(5.0)
                    poll_response = await client.get(poll_url, headers=headers)
                    if poll_response.status_code != 200:
                        return ToolResult(
                            success=False,
                            output="",
                            error=f"Failed to poll task status: HTTP {poll_response.status_code} - {poll_response.text}",
                        )

                    poll_data = poll_response.json()
                    status = poll_data.get("status")

                    if status == "succeeded":
                        result = poll_data.get("result", {})
                        videos = result.get("videos", [])
                        if not videos:
                            return ToolResult(
                                success=False,
                                output="",
                                error="Task succeeded but no videos in result",
                            )
                        video_info = videos[0]
                        video_url = video_info.get("url")
                        if not video_url:
                            return ToolResult(
                                success=False,
                                output="",
                                error="Task succeeded but no video URL in result",
                            )

                        output_data = {
                            "videoUrl": video_url,
                            "videoFile": None,
                            "duration": result.get("duration", duration),
                            "width": result.get("width"),
                            "height": result.get("height"),
                            "provider": "runway",
                            "model": model,
                            "jobId": task_id,
                        }
                        return ToolResult(success=True, output=video_url, data=output_data)

                    elif status == "failed":
                        return ToolResult(
                            success=False,
                            output="",
                            error=poll_data.get("error", "Video generation failed"),
                        )

                return ToolResult(
                    success=False,
                    output="",
                    error="Video generation timed out (took longer than 10 minutes)",
                )

        except httpx.TimeoutException:
            return ToolResult(success=False, output="", error="API request timed out")
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")