"""Agent that fixes truncated or broken Python tool files by regenerating them from the TypeScript source."""

import os
import ast
import asyncio
import httpx
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SIM_BASE_DIR = Path(
    os.getenv("SIM_BASE_DIR", str(REPO_ROOT / ".reference/sim/apps/sim"))
).resolve()
TOOLS_SCHEMA_DIR = SIM_BASE_DIR / "tools"
TOOLS_API_DIR = SIM_BASE_DIR / "app/api/tools"
INTEGRATION_TOOLS_DIR = REPO_ROOT / "backend/core/tools/integration_tools_v2"

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
MODEL = "x-ai/grok-4"

PROMPT_TEMPLATE = """You are an expert Python engineer. The Python tool file below is INCOMPLETE or TRUNCATED — it is cut off mid-method.

Your job is to COMPLETE the file so it is valid, runnable Python. Do NOT change anything that is already written. Only add the missing code to make the class fully functional.

Use the TypeScript reference source (if provided) to understand the API endpoint and request structure.

CRITICAL RULES:
- Output ONLY raw Python code. No markdown, no ``` blocks.
- Keep the existing class name, tool `name`, and `description` exactly as-is.
- Follow the exact BaseTool pattern used in the existing code.
- SYNTAX: All tuples must use () not }, e.g. `("key",)` not `("key",}`.
- SYNTAX: Arguments without defaults MUST come before arguments with defaults.
- SYNTAX: All parentheses, brackets, and braces must be correctly matched and closed.
- Do NOT use the walrus operator (:=) inside list comprehensions.
- The `_resolve_access_token` method must call `resolve_oauth_connection(...)` properly and return `connection.access_token`.
- The `execute` method must: resolve the token, check placeholder, build URL+headers, make the HTTP call, return ToolResult.

--- BROKEN PYTHON FILE (complete this) ---
{broken_code}

--- TYPESCRIPT REFERENCE (for API endpoint/logic, may be empty) ---
{ts_reference}

Complete the Python file above. Output the FULL corrected Python file from line 1.
"""


def has_syntax_error(filepath: Path) -> bool:
    try:
        ast.parse(filepath.read_text(encoding="utf-8"))
        return False
    except SyntaxError:
        return True


def find_broken_files() -> list[Path]:
    broken = []
    for py_file in sorted(INTEGRATION_TOOLS_DIR.rglob("*.py")):
        if "__pycache__" in str(py_file):
            continue
        if has_syntax_error(py_file):
            broken.append(py_file)
    return broken


def get_ts_reference(provider: str, action: str) -> str:
    """Try to find the TypeScript source for this tool."""
    schema_path = TOOLS_SCHEMA_DIR / provider / f"{action}.ts"
    api_path_kebab = TOOLS_API_DIR / provider / action.replace("_", "-") / "route.ts"
    api_path_exact = TOOLS_API_DIR / provider / action / "route.ts"

    parts = []
    if schema_path.exists():
        parts.append(f"// SCHEMA: {schema_path.name}\n{schema_path.read_text(encoding='utf-8', errors='ignore')}")
    if api_path_kebab.exists():
        parts.append(f"// ROUTE: {api_path_kebab}\n{api_path_kebab.read_text(encoding='utf-8', errors='ignore')}")
    elif api_path_exact.exists():
        parts.append(f"// ROUTE: {api_path_exact}\n{api_path_exact.read_text(encoding='utf-8', errors='ignore')}")

    return "\n\n".join(parts) if parts else "NO TYPESCRIPT REFERENCE AVAILABLE."


class ToolFixAgent:
    def __init__(self):
        self.client = httpx.AsyncClient()

    async def fix_file(self, py_file: Path):
        provider = py_file.parent.name
        action = py_file.stem
        print(f"  ➤ Fixing {provider}/{action}.py ...")

        broken_code = py_file.read_text(encoding="utf-8", errors="ignore")
        ts_reference = get_ts_reference(provider, action)

        prompt = PROMPT_TEMPLATE.replace("{broken_code}", broken_code)
        prompt = prompt.replace("{ts_reference}", ts_reference)

        try:
            response = await self.client.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                    "HTTP-Referer": "http://localhost:3000",
                    "X-Title": "ToolFixAgent",
                },
                json={
                    "model": MODEL,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.1,
                },
                timeout=180.0,
            )
            response.raise_for_status()

            data = response.json()
            if "error" in data:
                print(f"    ❌ API Error: {data['error']}")
                return

            content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
            if not content:
                print(f"    ❌ Empty response for {action}")
                return

            # Strip markdown fences if present
            fixed_code = content.strip()
            if fixed_code.startswith("```python"):
                fixed_code = fixed_code[9:]
            if fixed_code.startswith("```"):
                fixed_code = fixed_code[3:]
            if fixed_code.endswith("```"):
                fixed_code = fixed_code[:-3]
            fixed_code = fixed_code.strip()

            # Validate before writing
            try:
                ast.parse(fixed_code)
            except SyntaxError as e:
                print(f"    ❌ LLM output still has syntax error: {e}")
                return

            py_file.write_text(fixed_code, encoding="utf-8")
            print(f"    ✅ Fixed {py_file.name}")

        except httpx.HTTPStatusError as e:
            print(f"    ❌ HTTP Error: {e.response.status_code} - {e.response.text}")
        except Exception as e:
            print(f"    ❌ Failed: {e}")

    async def run(self):
        if not OPENROUTER_API_KEY:
            print("🚨 ERROR: OPENROUTER_API_KEY not set.")
            return

        broken = find_broken_files()
        if not broken:
            print("✅ No broken files found.")
            return

        print(f"🔧 Found {len(broken)} broken file(s):")
        for f in broken:
            print(f"  - {f.relative_to(REPO_ROOT)}")

        print("\n🤖 Starting fix agent...\n")
        for py_file in broken:
            await self.fix_file(py_file)

        # Re-check
        still_broken = find_broken_files()
        if still_broken:
            print(f"\n⚠️  {len(still_broken)} file(s) still broken after fix:")
            for f in still_broken:
                print(f"  - {f.relative_to(REPO_ROOT)}")
        else:
            print("\n🎉 All files fixed successfully.")


if __name__ == "__main__":
    agent = ToolFixAgent()
    asyncio.run(agent.run())
