import os
import asyncio
import httpx
from pathlib import Path

# Paths
SIM_BASE_DIR = Path("/Users/hritvik/Downloads/ceo-agent/.reference/sim/apps/sim")
TOOLS_SCHEMA_DIR = SIM_BASE_DIR / "tools"
TOOLS_API_DIR = SIM_BASE_DIR / "app/api/tools"
OUTPUT_DIR = Path("/Users/hritvik/Downloads/ceo-agent/backend/core/tools/integration_tools_v2")

# OpenRouter Config
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
MODEL = "openrouter/elephant-alpha"

PROMPT_TEMPLATE = """You are an expert Python engineer migrating a TypeScript integration tool to our Python AI agent backend.
You are given TWO pieces of information for a single tool:
1. The Schema File (defines what the LLM sees: parameters, description, tool name).
2. The Execution Files (ALL the HTTP logic routes for this provider that talk to the 3rd-party API).

Your job is to read the Schema File, find the matching logic in the provided Execution Files, and combine them into ONE native Python class inheriting from `BaseTool`.

CRITICAL INSTRUCTIONS:
- You must EXACTLY follow our backend's `BaseTool` formatting for authentication and HTTP execution.
- If the schema file contains multiple versions (e.g., `gmailSendTool` and `gmailSendV2Tool`), ONLY convert the LATEST version (e.g., V2). Ignore the older versions.
- DO NOT append "V2" to the Python class name or the tool `name` attribute. Keep it generic (e.g., use `GmailSendTool` instead of `GmailSendV2Tool`).
- NEVER output multiple classes. Output EXACTLY ONE class per tool.
- Do NOT hardcode local internal proxy routes (like `/api/tools/...`). You MUST use the actual third-party endpoint found in the matching Execution File (e.g., `https://gmail.googleapis.com/...`).
- DO NOT put helper functions outside the class unless they are completely agnostic. Prefer writing `_helper_methods` inside the class.
- NEVER wrap the output in ```python markdown blocks. Output raw, valid Python code only.

Here is the EXACT structural pattern you MUST follow:

```python
from typing import Any
import httpx
import base64
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class [Provider][Action]Tool(BaseTool): # e.g., GmailSendTool
    name = "action_name_from_schema" 
    description = "description from schema"
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or "ya29" in normalized

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="PROVIDER_ACCESS_TOKEN",
                description="Access token",
                env_var="PROVIDER_ACCESS_TOKEN",
                required=True,
                auth_type="oauth", # or "api_key"
            )
        ]

    async def _resolve_access_token(self, context: dict | None) -> str:
        connection = await resolve_oauth_connection(
            "google", # Replace with actual provider name
            context=context,
            context_token_keys=("provider_token",),
            env_token_keys=("PROVIDER_ACCESS_TOKEN",),
            placeholder_predicate=self._is_placeholder_token,
            allow_refresh=True,
        )
        return connection.access_token

    async def _refresh_google_access_token(self, user_id: str) -> str:
        if not user_id: return ""
        connection = await resolve_oauth_connection(
            "google", context={"user_id": user_id}, placeholder_predicate=self._is_placeholder_token, allow_refresh=False
        )
        if not connection.refresh_token: return ""
        return await refresh_oauth_access_token(connection)

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": { ... },
            "required": [ ... ]
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        headers = {
            "Authorization": f"Bearer {{access_token}}",
            "Content-Type": "application/json",
        }
        
        # Build the URL and JSON body dynamically based on the matching TS execution logic
        url = "https://thirdparty.api.com/v1/..."
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json={{...}})
                
                # Retry logic for 401s
                if response.status_code == 401 and context and context.get("user_id"):
                    refreshed = await self._refresh_google_access_token(str(context["user_id"]))
                    if refreshed:
                        headers["Authorization"] = f"Bearer {{refreshed}}"
                        response = await client.post(url, headers=headers, json={{...}})
                
                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {{str(e)}}")
```

--- SCHEMA FILE ({schema_name}) ---
{schema_code}

--- ALL EXECUTION FILES FOR THIS PROVIDER ---
{execution_codes}
"""

async def convert_tool(client: httpx.AsyncClient, schema_path: Path):
    if schema_path.name in ["index.ts", "utils.ts", "types.ts"] or schema_path.name.endswith(".test.ts"):
        return

    provider_name = schema_path.parent.name
    action_name = schema_path.stem

    provider_api_dir = TOOLS_API_DIR / provider_name
    
    if not provider_api_dir.exists():
        print(f"⚠️  Skipping {provider_name}/{schema_path.name}: No API directory found for provider")
        return

    print(f"Converting {provider_name}/{schema_path.name}...")

    with open(schema_path, "r") as f:
        schema_code = f.read()

    execution_codes = ""
    for route_file in provider_api_dir.rglob("route.ts"):
        try:
            with open(route_file, "r") as f:
                execution_codes += f"\\n\\n--- FILE: {route_file.relative_to(TOOLS_API_DIR)} ---\\n"
                execution_codes += f.read()
        except Exception:
            pass

    prompt = PROMPT_TEMPLATE.replace("{schema_name}", f"tools/{provider_name}/{schema_path.name}")
    prompt = prompt.replace("{schema_code}", schema_code)
    prompt = prompt.replace("{execution_codes}", execution_codes)

    try:
        response = await client.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "HTTP-Referer": "http://localhost:3000",
                "X-Title": "SimToPythonConverter",
            },
            json={
                "model": MODEL,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.1,
            },
            timeout=180.0
        )
        response.raise_for_status()
        
        data = response.json()
        python_code = data["choices"][0]["message"]["content"].strip()
        
        if python_code.startswith("```python"):
            python_code = python_code[9:]
        if python_code.startswith("```"):
            python_code = python_code[3:]
        if python_code.endswith("```"):
            python_code = python_code[:-3]
        
        provider_dir = OUTPUT_DIR / provider_name
        provider_dir.mkdir(parents=True, exist_ok=True)
        
        init_file = provider_dir / "__init__.py"
        if not init_file.exists():
            init_file.write_text("")
            
        out_path = provider_dir / f"{action_name}.py"
        
        with open(out_path, "w") as f:
            f.write(python_code.strip())
            
        print(f"✅ Saved to {out_path}")

    except Exception as e:
        print(f"❌ Failed to convert {provider_name}/{schema_path.name}: {str(e)}")

async def main():
    if not OPENROUTER_API_KEY:
        print("Error: OPENROUTER_API_KEY environment variable is not set.")
        return

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    init_file = OUTPUT_DIR / "__init__.py"
    if not init_file.exists():
        init_file.write_text("")

    gmail_files = list((TOOLS_SCHEMA_DIR / "gmail").rglob("*.ts"))
    notion_files = list((TOOLS_SCHEMA_DIR / "notion").rglob("*.ts"))
    
    ts_files = gmail_files + notion_files
    print(f"Found {len(ts_files)} TypeScript files to process (Gmail + Notion).")

    batch_size = 5
    
    async with httpx.AsyncClient() as client:
        for i in range(0, len(ts_files), batch_size):
            batch = ts_files[i:i + batch_size]
            tasks = [convert_tool(client, ts_file) for ts_file in batch]
            await asyncio.gather(*tasks)
            print(f"Completed batch {i//batch_size + 1} of {(len(ts_files) + batch_size - 1) // batch_size}")

if __name__ == "__main__":
    asyncio.run(main())
