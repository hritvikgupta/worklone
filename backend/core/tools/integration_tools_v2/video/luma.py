from typing import Any, Dict, List
import httpx
import asyncio
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class LumaVideoTool(BaseTool):
    name = "Luma Dream Machine Video"
    description = "Generate videos using Luma Dream Machine with advanced camera controls"
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return []

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "provider": {
                    "type": "string",
                    "description": "Video provider (luma)",
                },
                "apiKey": {
                    "type": "string",
                    "description": "Luma AI API key",
                },
                "model": {
                    "type": "string",
                    "description": "Luma model: ray-2 (default)",
                },
                "prompt": {
                    "type": "string",
                    "description": "Text prompt describing the video to generate",
                },
                "duration": {
                    "type": "number",
                    "description": "Video duration in seconds (5 or 9, default: 5)",
                },
                "aspectRatio": {
                    "type": "string",
                    "description": "Aspect ratio: 16:9 (landscape), 9:16 (portrait), or 1:1 (square)",
                },
                "resolution": {
                    "type": "string",
                    "description": "Video resolution: 540p, 720p, or 1080p (default: 1080p)",
                },
                "cameraControl": {
                    "type": "array",
                    "items": {
                        "type": "object",
                    },
                    "description": 'Camera controls as array of concept objects. Format: [{ "key": "concept_name" }]. Valid keys: truck_left, truck_right, pan_left, pan_right, tilt_up, tilt_down, zoom_in, zoom_out, push_in, pull_out, orbit_left, orbit_right, crane_up, crane_down, static, handheld, and 20+ more predefined options',
                },
            },
            "required": ["provider", "apiKey", "prompt"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        api_key = parameters.get("apiKey")
        if not api_key or self._is_placeholder_token(api_key):
            return ToolResult(success=False, output="", error="Luma API key not configured.")

        provider = parameters.get("provider")
        if provider != "luma":
            return ToolResult(success=False, output="", error="Only luma provider is supported.")

        body = {
            "prompt": parameters["prompt"],
            "model": parameters.get("model", "ray-2"),
            "duration": parameters.get("duration", 5),
            "aspect_ratio": parameters.get("aspectRatio", "16:9"),
            "resolution": parameters.get("resolution", "1080p"),
        }

        camera_control = parameters.get("cameraControl", [])
        if camera_control:
            body["camera"] = [{"type": concept.get("key")} for concept in camera_control if isinstance(concept, dict)]

        url = "https://api.lumalabs.ai/v1/videos"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(url, headers=headers, json=body)

                if response.status_code not in [200, 201]:
                    return ToolResult(success=False, output="", error=response.text)

                gen_data = response.json()
                job_id = gen_data.get("id")
                if not job_id:
                    return ToolResult(success=False, output="", error="No job ID in generation response")

                max_attempts = 120  # 20 minutes at 10s intervals
                for attempt in range(max_attempts):
                    if attempt > 0:
                        await asyncio.sleep(10)

                    poll_url = f"https://api.lumalabs.ai/v1/videos/{job_id}"
                    poll_response = await client.get(poll_url, headers=headers)

                    if poll_response.status_code != 200:
                        return ToolResult(success=False, output="", error=f"Poll request failed: {poll_response.text}")

                    poll_data = poll_response.json()
                    status = poll_data.get("status")

                    if status == "succeeded":
                        videos = poll_data.get("videos", [])
                        if not videos:
                            return ToolResult(success=False, output="", error="No videos in succeeded response")
                        video = videos[0]
                        video_url = video.get("url")
                        if not video_url:
                            return ToolResult(success=False, output="", error="Missing video URL")
                        width = video.get("width")
                        height = video.get("height")
                        duration = video.get("duration")
                        output_data = {
                            "videoUrl": video_url,
                            "videoFile": {
                                "url": video_url,
                                "width": width,
                                "height": height,
                                "duration": duration,
                            },
                            "duration": duration,
                            "width": width,
                            "height": height,
                            "provider": "luma",
                            "model": body["model"],
                            "jobId": job_id,
                        }
                        return ToolResult(
                            success=True,
                            output=video_url,
                            data=output_data,
                        )
                    elif status in ["failed", "error"]:
                        error_msg = poll_data.get("error", "Video generation failed")
                        return ToolResult(success=False, output="", error=error_msg)

                return ToolResult(success=False, output="", error="Video generation timed out")

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")