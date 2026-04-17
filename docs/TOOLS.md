# Tool System

Worklone employees can use **500+ pre-built tools** to interact with external services, manage files, execute workflows, and collaborate. This document covers the tool architecture, available tools, and how to build custom tools.

---

## Tool Architecture

Every tool implements the `BaseTool` abstract class:

```python
from abc import ABC, abstractmethod

class BaseTool(ABC):
    name: str
    description: str
    
    @abstractmethod
    def get_schema(self) -> dict:
        """Return OpenAI function-calling schema"""
    
    @abstractmethod
    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        """Execute the tool with given parameters"""
    
    def to_openai_schema(self) -> dict:
        """Convert to OpenAI function-calling format"""
```

### Tool Execution Flow

```
LLM decides to use a tool
    │
    ▼
ToolRegistry.lookup(tool_name)
    │
    ▼
Inject credentials (OAuth, API keys)
    │
    ▼
tool.execute(parameters, context)
    │
    ▼
Return ToolResult to LLM
```

---

## Tool Categories

### System Tools

Core utilities available to all employees.

| Tool | Description |
|------|-------------|
| `file_read` | Read file contents |
| `file_write` | Write content to a file |
| `file_delete` | Delete a file |
| `file_list` | List files in a directory |
| `http_request` | Make HTTP requests (GET, POST, PUT, DELETE) |
| `shell_exec` | Execute shell commands |
| `memory_store` | Store a value in employee memory |
| `memory_retrieve` | Retrieve a value from employee memory |

### Integration Tools

Connectors for external services.

#### GitHub (60+ tools)

| Tool | Description |
|------|-------------|
| `github_create_issue` | Create a new issue |
| `github_list_issues` | List repository issues |
| `github_create_pr` | Create a pull request |
| `github_list_prs` | List pull requests |
| `github_create_branch` | Create a new branch |
| `github_list_commits` | List repository commits |
| `github_search_issues` | Search issues across repositories |
| `github_add_comment` | Add comment to issue/PR |
| `github_merge_pr` | Merge a pull request |
| `github_create_release` | Create a release |

#### Slack (25 tools)

| Tool | Description |
|------|-------------|
| `slack_send_message` | Send message to channel/user |
| `slack_list_channels` | List available channels |
| `slack_list_users` | List workspace users |
| `slack_create_channel` | Create a new channel |
| `slack_add_reaction` | Add emoji reaction to message |
| `slack_open_view` | Open modal view |

#### Gmail (20 tools)

| Tool | Description |
|------|-------------|
| `gmail_send_email` | Send an email |
| `gmail_list_emails` | List inbox emails |
| `gmail_read_email` | Read email content |
| `gmail_search_emails` | Search emails by query |
| `gmail_create_draft` | Create email draft |
| `gmail_archive_email` | Archive an email |
| `gmail_trash_email` | Move email to trash |

#### Jira (14 tools)

| Tool | Description |
|------|-------------|
| `jira_create_issue` | Create a Jira issue |
| `jira_transition_issue` | Transition issue status |
| `jira_add_comment` | Add comment to issue |
| `jira_add_attachment` | Attach file to issue |
| `jira_log_work` | Log work time |

#### Notion (9 tools)

| Tool | Description |
|------|-------------|
| `notion_create_page` | Create a Notion page |
| `notion_query_database` | Query a Notion database |
| `notion_search` | Search Notion workspace |
| `notion_read_page` | Read page content |

#### Salesforce (30+ tools)

| Tool | Description |
|------|-------------|
| `salesforce_create_lead` | Create a lead |
| `salesforce_create_contact` | Create a contact |
| `salesforce_create_opportunity` | Create an opportunity |
| `salesforce_create_case` | Create a case |
| `salesforce_query` | Run SOQL query |
| `salesforce_update_record` | Update a record |

#### Stripe (40+ tools)

| Tool | Description |
|------|-------------|
| `stripe_create_customer` | Create a customer |
| `stripe_create_product` | Create a product |
| `stripe_create_subscription` | Create a subscription |
| `stripe_create_invoice` | Create an invoice |
| `stripe_create_payment_intent` | Create a payment intent |
| `stripe_list_charges` | List charges |
| `stripe_refund` | Refund a payment |

#### Linear (60+ tools)

| Tool | Description |
|------|-------------|
| `linear_create_issue` | Create an issue |
| `linear_list_issues` | List issues |
| `linear_create_project` | Create a project |
| `linear_list_cycles` | List cycles |
| `linear_add_comment` | Add comment to issue |

#### HubSpot (30+ tools)

| Tool | Description |
|------|-------------|
| `hubspot_create_contact` | Create a contact |
| `hubspot_create_deal` | Create a deal |
| `hubspot_create_ticket` | Create a ticket |
| `hubspot_list_companies` | List companies |

#### Google Services

| Service | Tools | Examples |
|---------|-------|----------|
| **Drive** (13) | `gdrive_upload`, `gdrive_download`, `gdrive_search`, `gdrive_share` |
| **Calendar** (10) | `gcal_create_event`, `gcal_list_events`, `gcal_freebusy` |
| **Maps** (13) | `gmaps_geocode`, `gmaps_directions`, `gmaps_places` |

#### Other Integrations

| Service | Tools | Description |
|---------|-------|-------------|
| **Kalshi** | Prediction markets | Markets, orders, positions, trades |
| **Gamma** | Presentations | Generate presentations, templates, themes |
| **Granola** | Notes | List and get notes |
| **Devin** | AI coding | Sessions, messages |
| **Attio** | CRM | Records, lists, tasks, notes, comments |
| **Hunter** | Email finding | Email finder, verifier, domain search |
| **DSPy** | Reasoning | Chain of thought, ReAct, predict |

### Employee Tools

Tools for agent collaboration and task management.

| Tool | Description |
|------|-------------|
| `ask_user` | Pause and ask the user a question (human-in-the-loop) |
| `run_task_async` | Spawn a long-running background task |
| `send_message_to_coworker` | Message another employee |
| `check_messages` | Check for messages from coworkers |
| `get_my_team_context` | Get team context and shared memory |
| `create_task` | Create a task for the employee |
| `update_task` | Update task status |

### Workflow Tools

Tools for managing workflows programmatically.

| Tool | Description |
|------|-------------|
| `create_workflow` | Create a new workflow |
| `add_block` | Add a block to a workflow |
| `connect_blocks` | Connect two blocks |
| `execute_workflow` | Execute a workflow |
| `monitor_execution` | Monitor workflow execution |
| `approve_execution` | Approve a human-in-the-loop step |
| `pause_execution` | Pause a running workflow |
| `resume_execution` | Resume a paused workflow |
| `cancel_execution` | Cancel a running workflow |

### Specialized Tools

Role-specific tools for different employee types.

| Role | Tools |
|------|-------|
| **Product Manager** | `pm_create_prd`, `pm_prioritize_features`, `pm_analyze_metrics` |
| **Engineer** | `engineer_review_code`, `engineer_run_tests`, `engineer_debug` |
| **Analyst** | `analyst_query_data`, `analyst_generate_report`, `analyst_visualize` |
| **Designer** | `designer_create_mockup`, `designer_review_ux` |
| **Recruiter** | `recruiter_screen_candidate`, `recruiter_schedule_interview` |
| **Sales** | `sales_create_proposal`, `sales_forecast`, `sales_track_deal` |
| **Operations** | `ops_generate_report`, `ops_monitor_systems`, `ops_automate` |

---

## Building Custom Tools

Creating a custom tool takes under 50 lines of code.

### Step 1: Create the Tool Class

```python
from backend.core.tools.system_tools.base_tool import BaseTool
from backend.core.tools.system_tools.base_tool import ToolResult

class AnalyzeDataTool(BaseTool):
    name = "analyze_data"
    description = "Perform deep data analysis on a dataset"
    
    def get_schema(self) -> dict:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "dataset_path": {
                            "type": "string",
                            "description": "Path to the dataset file"
                        },
                        "analysis_type": {
                            "type": "string",
                            "enum": ["summary", "correlation", "trend"],
                            "description": "Type of analysis to perform"
                        }
                    },
                    "required": ["dataset_path", "analysis_type"]
                }
            }
        }
    
    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        dataset_path = parameters["dataset_path"]
        analysis_type = parameters["analysis_type"]
        
        # Your analysis logic here
        result = perform_analysis(dataset_path, analysis_type)
        
        return ToolResult(success=True, output=result)
```

### Step 2: Register the Tool

Add your tool to the tool catalog:

```python
# backend/core/tools/catalog.py
from .custom.analyze_data import AnalyzeDataTool

TOOL_CATALOG = {
    # ... existing tools ...
    "analyze_data": AnalyzeDataTool(),
}
```

### Step 3: Assign to Employees

Assign the tool to employees via the API or dashboard:

```bash
curl -X PATCH http://localhost:8000/api/employees/{id}/tools \
  -H "Content-Type: application/json" \
  -d '{"tools": ["analyze_data", "file_read", "http_request"]}'
```

### Tool with Credentials

If your tool needs API keys or OAuth:

```python
class SalesforceTool(BaseTool):
    name = "salesforce_query"
    description = "Run a SOQL query against Salesforce"
    
    requires_credentials = ["salesforce_access_token"]
    
    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        # Credentials are injected via context
        token = context.get("salesforce_access_token")
        
        # Use the token to make API calls
        result = query_salesforce(parameters["query"], token)
        
        return ToolResult(success=True, output=result)
```

---

## Tool Registry

The `ToolRegistry` manages all tools:

```python
class ToolRegistry:
    def register(self, tool: BaseTool) -> None:
        """Register a tool"""
    
    def get(self, name: str) -> BaseTool:
        """Get a tool by name"""
    
    def list_all(self) -> list[BaseTool]:
        """List all registered tools"""
    
    def execute(self, name: str, parameters: dict, context: dict) -> ToolResult:
        """Execute a tool"""
    
    def to_openai_schemas(self, tool_names: list[str]) -> list[dict]:
        """Convert tools to OpenAI function-calling format"""
```

---

## ToolResult

All tools return a `ToolResult`:

```python
class ToolResult:
    success: bool      # Whether the tool succeeded
    output: str        # The tool's output (returned to LLM)
    error: str = None  # Error message if failed
```

---

## Best Practices

1. **Clear descriptions** — the LLM uses descriptions to decide when to use a tool
2. **Typed parameters** — use proper JSON schema types and enums
3. **Required fields** — mark truly required parameters, leave optional ones flexible
4. **Error handling** — return `ToolResult(success=False, error="...")` on failure
5. **Credential injection** — use `context` for credentials, never hardcode
6. **Idempotency** — make tools safe to call multiple times
7. **Rate limiting** — respect API rate limits in your tools
