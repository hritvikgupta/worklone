from typing import Any, Dict, List
import httpx
import base64
import os
from backend.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

WORKDAY_SERVICES = {
    "staff