"""
Credential Management Tools — Dynamic credential awareness for the co-worker agent.

These tools let the agent:
1. Discover what credentials each integration tool requires (from the registry, not hardcoded)
2. Check which credentials are configured vs missing for a user
3. Store credentials provided by the user
4. Resolve credentials at runtime (DB > env var fallback)
"""

import os
from backend.workflows.tools.base import BaseTool, ToolResult
from backend.workflows.tools.registry import ToolRegistry
from backend.workflows.store import WorkflowStore


class ListRequiredCredentialsTool(BaseTool):
    """Discover what credentials all registered tools need."""

    name = "list_required_credentials"
    description = (
        "List all credentials required by integration tools. "
        "Shows which tools need which credentials, whether they are configured, "
        "and what to ask the user for. Call this BEFORE creating workflows that "
        "use external services."
    )
    category = "credentials"

    def __init__(self, registry: ToolRegistry):
        self._registry = registry

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "tool_name": {
                    "type": "string",
                    "description": "Optional: filter to a specific tool name. If omitted, shows all tools.",
                },
            },
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        tool_name_filter = parameters.get("tool_name")
        owner_id = (context or {}).get("owner_id", "")
        base_url = (context or {}).get("base_url", "http://localhost:8002")

        store = WorkflowStore()
        user_creds = {c["key"]: c for c in store.list_credentials(owner_id)} if owner_id else {}

        tools = self._registry.list_tools()
        if tool_name_filter:
            tools = [t for t in tools if t.name == tool_name_filter]

        output_lines = []
        all_requirements = []
        auth_actions = []  # Dynamic auth buttons for the frontend

        for tool in tools:
            cred_reqs = tool.get_required_credentials()
            if not cred_reqs:
                continue

            output_lines.append(f"\n🔧 {tool.name} ({tool.description[:60]})")
            for req in cred_reqs:
                # Check: user DB first, then env var
                has_in_db = req.key in user_creds
                has_in_env = bool(os.getenv(req.env_var, ""))
                has_value = has_in_db or has_in_env
                status = "✅ configured" if has_value else "❌ MISSING"
                source = "(user-provided)" if has_in_db else "(env)" if has_in_env else ""

                output_lines.append(
                    f"  • {req.key}: {status} {source}\n"
                    f"    {req.description}\n"
                    f"    Required: {'yes' if req.required else 'optional'}"
                )

                req_data = {
                    "tool": tool.name,
                    "key": req.key,
                    "description": req.description,
                    "required": req.required,
                    "configured": has_value,
                    "example": req.example,
                    "auth_type": req.auth_type,
                    "auth_provider": req.auth_provider,
                }

                # If missing and has OAuth, build an auth action button
                if not has_value and req.required and req.auth_type == "oauth" and req.auth_url:
                    auth_redirect = (
                        f"{base_url}/api/auth/oauth/{req.auth_provider}"
                        f"?owner_id={owner_id}&credential_key={req.key}"
                    )
                    auth_action = {
                        "type": "auth_button",
                        "provider": req.auth_provider,
                        "label": f"Connect {req.auth_provider.title()}",
                        "url": auth_redirect,
                        "credential_key": req.key,
                        "scopes": req.auth_scopes,
                    }
                    auth_actions.append(auth_action)
                    req_data["auth_action"] = auth_action
                    output_lines.append(
                        f"    🔗 Click 'Connect {req.auth_provider.title()}' to authenticate"
                    )
                elif not has_value and req.required and req.auth_type == "api_key" and req.auth_url:
                    auth_action = {
                        "type": "auth_link",
                        "provider": req.auth_provider,
                        "label": f"Get {req.auth_provider.title()} API Key",
                        "url": req.auth_url,
                        "credential_key": req.key,
                    }
                    auth_actions.append(auth_action)
                    req_data["auth_action"] = auth_action
                    output_lines.append(
                        f"    🔗 Get your API key at: {req.auth_url}"
                    )

                all_requirements.append(req_data)

        if not output_lines:
            return ToolResult(
                success=True,
                output="No tools require credentials." if not tool_name_filter
                       else f"Tool '{tool_name_filter}' has no credential requirements.",
                data={"requirements": [], "auth_actions": []},
            )

        missing = [r for r in all_requirements if not r["configured"] and r["required"]]
        summary = f"\nSummary: {len(all_requirements)} credentials tracked, {len(missing)} missing."
        if missing:
            summary += "\nMissing credentials:\n" + "\n".join(
                f"  ❌ {m['key']} (needed by {m['tool']}): {m['description']}"
                for m in missing
            )

        return ToolResult(
            success=True,
            output="\n".join(output_lines) + summary,
            data={"requirements": all_requirements, "auth_actions": auth_actions},
        )


class CheckCredentialTool(BaseTool):
    """Check if a specific credential is configured."""

    name = "check_credential"
    description = (
        "Check if a specific credential is configured for the current user. "
        "Returns whether the credential exists (in user store or environment)."
    )
    category = "credentials"

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "key": {
                    "type": "string",
                    "description": "The credential key to check (e.g., 'SLACK_BOT_TOKEN', 'GMAIL_ACCESS_TOKEN')",
                },
            },
            "required": ["key"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        key = parameters.get("key", "")
        if not key:
            return ToolResult(success=False, output="", error="key is required")

        owner_id = (context or {}).get("owner_id", "")

        store = WorkflowStore()
        db_value = store.get_credential(owner_id, key) if owner_id else None
        env_value = os.getenv(key, "")

        if db_value:
            return ToolResult(
                success=True,
                output=f"✅ {key} is configured (user-provided).",
                data={"key": key, "configured": True, "source": "user"},
            )
        elif env_value:
            return ToolResult(
                success=True,
                output=f"✅ {key} is configured (environment variable).",
                data={"key": key, "configured": True, "source": "env"},
            )
        else:
            return ToolResult(
                success=True,
                output=f"❌ {key} is NOT configured. Ask the user to provide it.",
                data={"key": key, "configured": False, "source": None},
            )


class SetCredentialTool(BaseTool):
    """Store a credential provided by the user."""

    name = "set_credential"
    description = (
        "Store a credential provided by the user. This saves it securely "
        "for future workflow executions. The user should provide the credential "
        "value in the chat, and you call this tool to save it."
    )
    category = "credentials"

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "key": {
                    "type": "string",
                    "description": "The credential key (e.g., 'SLACK_BOT_TOKEN')",
                },
                "value": {
                    "type": "string",
                    "description": "The credential value provided by the user",
                },
                "description": {
                    "type": "string",
                    "description": "Optional description of what this credential is for",
                },
            },
            "required": ["key", "value"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        key = parameters.get("key", "")
        value = parameters.get("value", "")
        description = parameters.get("description", "")

        if not key or not value:
            return ToolResult(success=False, output="", error="key and value are required")

        owner_id = (context or {}).get("owner_id", "")
        if not owner_id:
            return ToolResult(success=False, output="", error="No user context — cannot store credential")

        store = WorkflowStore()
        result = store.set_credential(owner_id, key, value, description)

        return ToolResult(
            success=True,
            output=f"✅ Credential '{key}' saved successfully for your account.",
            data=result,
        )


class DeleteCredentialTool(BaseTool):
    """Remove a stored credential."""

    name = "delete_credential"
    description = "Remove a previously stored credential for the current user."
    category = "credentials"

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "key": {
                    "type": "string",
                    "description": "The credential key to delete",
                },
            },
            "required": ["key"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        key = parameters.get("key", "")
        if not key:
            return ToolResult(success=False, output="", error="key is required")

        owner_id = (context or {}).get("owner_id", "")
        if not owner_id:
            return ToolResult(success=False, output="", error="No user context")

        store = WorkflowStore()
        deleted = store.delete_credential(owner_id, key)

        if deleted:
            return ToolResult(success=True, output=f"✅ Credential '{key}' deleted.", data={"key": key})
        return ToolResult(success=False, output="", error=f"Credential '{key}' not found.")


class SaveUserProfileTool(BaseTool):
    """Save user profile during PA onboarding."""

    name = "save_user_profile"
    description = (
        "Save the user's profile details during onboarding. Call this after asking "
        "the user about their name, company, role, industry, and expectations. "
        "This permanently stores their profile so Harry remembers who they are."
    )
    category = "profile"

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "display_name": {
                    "type": "string",
                    "description": "User's name (e.g., 'John Smith')",
                },
                "company_name": {
                    "type": "string",
                    "description": "Company or org name (e.g., 'Acme Corp')",
                },
                "role": {
                    "type": "string",
                    "description": "User's role (e.g., 'CEO', 'CTO', 'Product Manager')",
                },
                "industry": {
                    "type": "string",
                    "description": "Industry or domain (e.g., 'SaaS', 'Healthcare', 'E-commerce')",
                },
                "company_description": {
                    "type": "string",
                    "description": "Brief description of what the company does",
                },
                "expectations": {
                    "type": "string",
                    "description": "What the user expects from Harry (e.g., 'manage my emails, schedule tasks, monitor APIs')",
                },
            },
            "required": ["display_name"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        owner_id = (context or {}).get("owner_id", "")
        if not owner_id:
            return ToolResult(success=False, output="", error="No user context")

        store = WorkflowStore()
        profile = store.save_user_profile(
            owner_id,
            display_name=parameters.get("display_name", ""),
            company_name=parameters.get("company_name", ""),
            role=parameters.get("role", ""),
            industry=parameters.get("industry", ""),
            company_description=parameters.get("company_description", ""),
            expectations=parameters.get("expectations", ""),
            onboarded=1,
        )

        name = parameters.get("display_name", "the user")
        return ToolResult(
            success=True,
            output=f"✅ Profile saved for {name}. I'll remember everything about you.",
            data=profile,
        )


def create_credential_tools(registry: ToolRegistry) -> list[BaseTool]:
    """Create all credential + profile management tools. Dynamically reads from the registry."""
    return [
        ListRequiredCredentialsTool(registry),
        CheckCredentialTool(),
        SetCredentialTool(),
        DeleteCredentialTool(),
        SaveUserProfileTool(),
    ]
