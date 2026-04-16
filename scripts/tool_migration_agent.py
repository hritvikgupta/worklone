import os
import asyncio
import httpx
from pathlib import Path

# Configuration
SIM_BASE_DIR = Path("/Users/hritvik/Downloads/ceo-agent/.reference/sim/apps/sim")
TOOLS_SCHEMA_DIR = SIM_BASE_DIR / "tools"
TOOLS_API_DIR = SIM_BASE_DIR / "app/api/tools"
OUTPUT_DIR = Path("/Users/hritvik/Downloads/ceo-agent/backend/tools/integration_tools_v2")

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
MODEL = "x-ai/grok-4.1-fast"

PROMPT_TEMPLATE = """You are an expert Python engineer migrating a TypeScript integration tool to our Python AI agent backend.
You are given TWO pieces of information for a single tool:
1. The Schema File (defines what the LLM sees: parameters, description, tool name).
2. The Execution Logic (the actual HTTP logic that talks to the 3rd-party API like Google, Slack, etc.).

Your job is to read the Schema File, find the matching logic in the Execution Logic, and combine them into ONE native Python class inheriting from `BaseTool`.

CRITICAL INSTRUCTIONS:
- You must EXACTLY follow our backend's `BaseTool` formatting for authentication and HTTP execution.
- If the schema file contains multiple versions (e.g., `gmailSendTool` and `gmailSendV2Tool`), ONLY convert the LATEST version (e.g., V2). Ignore the older versions.
- DO NOT append "V2" to the Python class name or the tool `name` attribute. Keep it generic (e.g., use `GmailSendTool` instead of `GmailSendV2Tool`).
- NEVER output multiple classes. Output EXACTLY ONE class per tool.
- Do NOT hardcode local internal proxy routes (like `/api/tools/...`). You MUST use the actual third-party endpoint found in the matching Execution Logic (e.g., `https://gmail.googleapis.com/...`).
- DO NOT put helper functions outside the class unless they are completely agnostic. Prefer writing `_helper_methods` inside the class.
- NEVER wrap the output in ```python markdown blocks. Output raw, valid Python code only.
- SYNTAX RULE: In Python methods, arguments without defaults MUST precede arguments with defaults.
- SYNTAX RULE: DO NOT use the walrus operator (`:=`) inside list comprehensions.
- SYNTAX RULE: Ensure all parentheses, brackets, and braces are correctly closed in dictionaries and tuples (e.g., `("key",)` not `("key",}`).

Here is the EXACT structural pattern you MUST follow:

```python
from typing import Any, Dict
import httpx
import base64
from backend.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.tools.integration_tools.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class [Provider][Action]Tool(BaseTool): # e.g., GmailSendTool
    name = "action_name_from_schema" 
    description = "description from schema"
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

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
                
                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {{str(e)}}")
```

--- SCHEMA FILE ({schema_name}) ---
{schema_code}

--- EXECUTION LOGIC ---
{execution_codes}
"""

class ToolMigrationAgent:
    """An autonomous agent that crawls a TypeScript repository, pairs schema and execution files, and migrates them to Python using an LLM."""
    
    def __init__(self, provider_filter: list[str] = None, skip_providers: list[str] = None):
        self.provider_filter = provider_filter or []
        self.skip_providers = skip_providers or []
        self.client = httpx.AsyncClient()

    async def process_provider(self, provider_dir: Path):
        """Process all tool files for a given provider directory."""
        provider_name = provider_dir.name
        
        if self.provider_filter and provider_name not in self.provider_filter:
            return
            
        if provider_name in self.skip_providers:
            return

        print(f"\n🔍 Crawling provider: {provider_name}")
        ts_files = [f for f in provider_dir.rglob("*.ts") if f.name not in ["index.ts", "utils.ts", "types.ts"] and not f.name.endswith(".test.ts")]

        if not ts_files:
            print(f"  No valid tools found for {provider_name}.")
            return

        for ts_file in ts_files:
            await self.migrate_tool(ts_file, provider_name)

    async def migrate_tool(self, schema_path: Path, provider_name: str):
        """Extract schema and execution logic, then use the LLM to migrate the tool."""
        action_name = schema_path.stem
        print(f"  ➤ Migrating {provider_name}/{action_name}...")

        # Read schema code
        try:
            with open(schema_path, "r", encoding="utf-8") as f:
                schema_code = f.read()
        except Exception as e:
            print(f"    ❌ Error reading schema: {e}")
            return

        # Attempt to find execution route (handling snake_case vs kebab-case)
        action_kebab = action_name.replace("_", "-")
        execution_path_kebab = TOOLS_API_DIR / provider_name / action_kebab / "route.ts"
        execution_path_exact = TOOLS_API_DIR / provider_name / action_name / "route.ts"

        execution_codes = ""
        if execution_path_kebab.exists():
            with open(execution_path_kebab, "r", encoding="utf-8") as f:
                execution_codes = f.read()
        elif execution_path_exact.exists():
            with open(execution_path_exact, "r", encoding="utf-8") as f:
                execution_codes = f.read()
        else:
            # If no route is found, the logic is usually embedded directly in the schema's `request` block.
            execution_codes = "NO SEPARATE EXECUTION FILE FOUND. Extract the endpoint and execution logic directly from the schema file's `request: { ... }` block."

        prompt = PROMPT_TEMPLATE.replace("{schema_name}", f"tools/{provider_name}/{schema_path.name}")
        prompt = prompt.replace("{schema_code}", schema_code)
        prompt = prompt.replace("{execution_codes}", execution_codes)

        try:
            response = await self.client.post(
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
            
            if "error" in data:
                print(f"    ❌ OpenRouter API Error: {data['error']}")
                return
                
            message = data.get("choices", [{}])[0].get("message", {})
            content = message.get("content")
            
            if content is None:
                print(f"    ❌ API returned empty content or refused. Full response: {data}")
                return
                
            python_code = content.strip()
            
            # Clean markdown formatting if present
            if python_code.startswith("```python"):
                python_code = python_code[9:]
            if python_code.startswith("```"):
                python_code = python_code[3:]
            if python_code.endswith("```"):
                python_code = python_code[:-3]
            
            # Ensure output directory exists
            provider_out_dir = OUTPUT_DIR / provider_name
            provider_out_dir.mkdir(parents=True, exist_ok=True)
            
            init_file = provider_out_dir / "__init__.py"
            if not init_file.exists():
                init_file.write_text("")
                
            out_path = provider_out_dir / f"{action_name}.py"
            
            with open(out_path, "w", encoding="utf-8") as f:
                f.write(python_code.strip())
                
            print(f"    ✅ Successfully generated {out_path.name}")

        except httpx.HTTPStatusError as e:
            print(f"    ❌ API Error for {action_name}: {e.response.status_code} - {e.response.text}")
        except Exception as e:
            print(f"    ❌ Failed to generate {action_name}: {str(e)}")

    async def run(self):
        """Start the agent."""
        if not OPENROUTER_API_KEY:
            print("🚨 ERROR: OPENROUTER_API_KEY environment variable is not set.")
            return

        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        init_file = OUTPUT_DIR / "__init__.py"
        if not init_file.exists():
            init_file.write_text("")

        print("🤖 Tool Migration Agent initialized. Starting crawl...")
        
        provider_dirs = [d for d in TOOLS_SCHEMA_DIR.iterdir() if d.is_dir()]
        
        for provider_dir in provider_dirs:
            await self.process_provider(provider_dir)
            
        print("\n🎉 Migration process complete.")

if __name__ == "__main__":
    # You can restrict it to specific providers for testing, e.g., ["gmail", "notion"]
    # Pass an empty list to crawl ALL tools.
    major_providers = [
        "salesforce", "linear", "slack", "hubspot", 
        "stripe", "github", "jira", "google_drive"
    ]
    agent = ToolMigrationAgent(provider_filter=major_providers, skip_providers=["gmail", "notion"])
    asyncio.run(agent.run())
