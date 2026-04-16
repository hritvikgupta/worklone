from typing import Any, Dict
import httpx
from backend.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class VeoVideoTool(BaseTool):
    name = "Google Veo 3 Video"
    description = "