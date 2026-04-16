from typing import Any, Dict
import httpx
import asyncio
from backend.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class FalaiVideoTool(BaseTool):
    name = "Fal.ai Video Generation"
    description = "Generate videos using Fal.ai platform with access to multiple models including Veo 3.1, Sora 2, Kling 2.5, MiniMax Hailuo, and more"
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
                    "description": "Video provider (falai)",
                },
                "apiKey": {
                    "type": "string",
                    "description": "Fal.ai API key",
                },
                "model": {
                    "type": "string",
                    "description": "Fal.ai model: veo-3.1 (Google Veo 3.1), sora-2 (OpenAI Sora 2), kling-2.5-turbo-pro (Kling 2.5 Turbo Pro), kling-2.1-pro (Kling 2.1 Master), minimax-hailuo-2.3-pro (MiniMax Hailuo Pro), minimax-hailuo-2.3-standard (MiniMax Hailuo Standard), wan-2.1 (WAN T2V), ltxv-0.9.8 (LTXV 13B)",
                },
                "prompt": {
                    "type": "string",
                    "description": "Text prompt describing the video to generate",
                },
                "duration": {
                    "type": "number",
                    "description": "Video duration in seconds (varies by model)",
                },
                "aspectRatio": {
                    "type": "string",
                    "description": "Aspect ratio (varies by model): 16:9, 9:16, 1:1",
                },
                "resolution": {
                    "type": "string",
                    "description": "Video resolution (varies by model): 540p, 720p, 1080p",
                },
                "promptOptimizer": {
                    "type": "boolean",
                    "description": "Enable prompt optimization for MiniMax models (default: true)",
                },
            },
            "required": ["provider", "apiKey", "model", "prompt"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        provider = parameters.get("provider")
        if provider != "falai":
            return ToolResult(success=False, output="", error="Provider must be 'falai'.")

        api_key = parameters["apiKey"]
        if self._is_placeholder_token(api_key):
            return ToolResult(success=False, output="", error="Fal.ai API key not configured.")

        model = parameters["model"]
        prompt = parameters["prompt"]

        headers = {
            "X-FAL-Key": api_key,
            "Content-Type": "application/json",
        }

        create_url = f"https://fal.run/fal-ai/{model}/async"

        body: Dict[str, Any] = {
            "prompt": prompt,
        }
        duration = parameters.get("duration")
        if duration is not None:
            body["duration"] = duration
        aspect_ratio = parameters.get("aspectRatio")
        if aspect_ratio:
            body["aspect_ratio"] = aspect_ratio
        resolution = parameters.get("resolution")
        if resolution:
            body["resolution"] = resolution
        prompt_optimizer = parameters.get("promptOptimizer", True)
        if prompt_optimizer:
            body["prompt_optimizer"] = True

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(create_url, headers=headers, json=body)
                if resp.status_code not in [200, 201, 202]:
                    return ToolResult(
                        success=False,
                        output="",
                        error=f"Failed to create job ({resp.status_code}): {resp.text}",
                    )
                job_data = resp.json()
                job_id = job_data.get("id")
                if not job_id:
                    return ToolResult(
                        success=False,
                        output="",
                        error="No job ID returned from create request",
                    )

                status_url = f"https://fal.run/fal-ai/{model}/status/{job_id}"
                max_polls = 120
                for attempt in range(max_polls):
                    await asyncio.sleep(2 + attempt * 0.2)
                    status_resp = await client.get(status_url, headers=headers)
                    if status_resp.status_code != 200:
                        return ToolResult(
                            success=False,
                            output="",
                            error=f"Status poll failed ({status_resp.status_code}): {status_resp.text}",
                        )
                    status_data = status_resp.json()
                    status = status_data.get("status", "").upper()
                    if status == "COMPLETED":
                        output = status_data.get("output", {})
                        output_data = {
                            "videoUrl": output.get("video_url", ""),
                            "videoFile": output.get("video_file"),
                            "duration": output.get("duration"),
                            "width": output.get("width"),
                            "height": output.get("height"),
                            "provider": "falai",
                            "model": model,
                            "jobId": job_id,
                        }
                        return ToolResult(
                            success=True,
                            output=output.get("video_url", ""),
                            data=output_data,
                        )
                    elif status in ["FAILED", "ERROR", "CANCELLED"]:
                        return ToolResult(
                            success=False,
                            output="",
                            error=status_data.get("error") or status_data.get("logs", "Job failed"),
                        )
                return ToolResult(
                    success=False,
                    output="",
                    error="Video generation timed out (max 10 minutes)",
                )
        except httpx.RequestError as e:
            return ToolResult(
                success=False,
                output="",
                error=f"Network error: {str(e)}",
            )
        except Exception as e:
            return ToolResult(
                success=False,
                output="",
                error=f"API error: {str(e)}",
            )