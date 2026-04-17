from typing import Any, Dict
import httpx
import asyncio
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection

class MinimaxVideoTool(BaseTool):
    name = "MiniMax Hailuo Video"
    description = "Generate videos using MiniMax Hailuo through MiniMax Platform API with advanced realism and prompt optimization"
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="MINIMAX_API_KEY",
                description="MiniMax API key from platform.minimax.io",
                env_var="MINIMAX_API_KEY",
                required=True,
                auth_type="api_key",
            )
        ]

    async def _resolve_access_token(self, context: dict | None) -> str:
        connection = await resolve_oauth_connection(
            "minimax",
            context=context,
            context_token_keys=("minimax_api_key", "api_key"),
            env_token_keys=("MINIMAX_API_KEY",),
            placeholder_predicate=self._is_placeholder_token,
            allow_refresh=False,
        )
        return connection.access_token

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "model": {
                    "type": "string",
                    "description": "MiniMax model: hailuo-02 (default)",
                },
                "prompt": {
                    "type": "string",
                    "description": "Text prompt describing the video to generate",
                },
                "duration": {
                    "type": "number",
                    "description": "Video duration in seconds (6 or 10, default: 6)",
                },
                "promptOptimizer": {
                    "type": "boolean",
                    "description": "Enable prompt optimization for better results (default: true)",
                },
            },
            "required": ["prompt"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        
        model = parameters.get("model", "hailuo-02")
        prompt = parameters["prompt"]
        duration = parameters.get("duration", 6)
        prompt_optimizer = parameters.get("promptOptimizer", True)
        
        if prompt_optimizer:
            prompt = f"Generate a realistic, high-quality video with smooth motion, detailed visuals, and cinematic quality: {prompt.strip()}"
        
        url = "https://api.minimax.chat/v1/videos/hailuo_ai_video"
        
        body = {
            "model": model,
            "prompt": prompt,
            "duration": int(duration),
        }
        
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                resp = await client.post(url, headers=headers, json=body)
                
                resp_data = resp.json() if resp.text else {}
                
                if resp.status_code != 200 or resp_data.get("code") != 200:
                    error_msg = resp_data.get("error") or resp_data.get("data", {}).get("error_msg", resp.text)
                    return ToolResult(success=False, output="", error=error_msg)
                
                task_id = resp_data.get("task_id") or resp_data.get("data", {}).get("task_id")
                if not task_id:
                    return ToolResult(success=False, output="", error="No task_id received from API")
                
                poll_url = f"https://api.minimax.chat/v1/videos/{task_id}"
                max_attempts = 120  # ~10 minutes at 5s intervals
                
                for attempt in range(max_attempts):
                    await asyncio.sleep(5)
                    
                    poll_resp = await client.post(poll_url, headers=headers, json={})
                    
                    poll_data = poll_resp.json() if poll_resp.text else {}
                    
                    if poll_resp.status_code != 200 or poll_data.get("code") != 200:
                        error_msg = poll_data.get("error") or poll_data.get("data", {}).get("error_msg", poll_resp.text)
                        return ToolResult(success=False, output="", error=error_msg)
                    
                    status = poll_data.get("status") or poll_data.get("data", {}).get("status")
                    video_data = poll_data.get("data", {})
                    
                    if status in ["success", "succeeded", "completed"]:
                        video_url = video_data.get("video_url")
                        if not video_url:
                            return ToolResult(success=False, output="", error="Video URL missing in completed response")
                        
                        result = {
                            "videoUrl": video_url,
                            "videoFile": {
                                "url": video_url,
                                "name": f"minimax_hailuo_{task_id}.mp4",
                                "mimeType": "video/mp4",
                                "metadata": {
                                    "duration": video_data.get("duration"),
                                    "width": video_data.get("width"),
                                    "height": video_data.get("height"),
                                },
                            },
                            "duration": video_data.get("duration"),
                            "width": video_data.get("width"),
                            "height": video_data.get("height"),
                            "provider": "minimax",
                            "model": model,
                            "jobId": task_id,
                        }
                        
                        output_msg = f"Video generated successfully. URL: {video_url}"
                        return ToolResult(success=True, output=output_msg, data=result)
                    
                    elif status in ["error", "failed", "ERROR", "FAILED"]:
                        error_msg = video_data.get("error_msg") or video_data.get("error") or "Generation failed"
                        return ToolResult(success=False, output="", error=error_msg)
                    
                    # Continue polling if processing/queued
                
                return ToolResult(success=False, output="", error="Timeout: Video generation took too long")
                
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")