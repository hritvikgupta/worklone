from typing import Any, Dict, Optional
import httpx
import xml.etree.ElementTree as ET
import json
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class WorkdayListWorkersTool(BaseTool):
    name