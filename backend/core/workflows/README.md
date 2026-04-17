# Workflow Engine — Your AI Co-Worker

A complete workflow automation system built from scratch. No Sim dependency. No licensing fees. 100% yours.

## Architecture

```
workflows/
├── types.py                    # All data models (Workflow, Block, Connection, etc.)
├── utils.py                    # Template resolution, ID generation, time utils
├── logger.py                   # Centralized logging
├── store.py                    # SQLite persistence layer
├── coworker.py                 # The Co-Worker ReAct Agent
│
├── engine/                     # Execution engine
│   ├── dag_builder.py          # Converts workflow → DAG
│   ├── executor.py             # Runs the DAG block by block
│   ├── variable_resolver.py    # Resolves {{block.output.field}} references
│   └── handlers/               # Block type handlers
│       ├── base.py             # Base handler + NoOp handler
│       ├── registry.py         # Handler registry
│       ├── agent_handler.py    # LLM agent blocks
│       ├── tool_handler.py     # Tool blocks
│       ├── function_handler.py # Python code blocks
│       ├── condition_handler.py# Conditional branching
│       └── http_handler.py     # HTTP request blocks
│
└── __init__.py                 # Public API

workflows_server.py             # FastAPI server (REST + WebSocket)

backend/core/tools/
├── system_tools/               # BaseTool interface, registry, HTTP
├── run_tools/                  # LLM and function execution
├── integration_tools/          # Slack and Gmail integrations
└── workflow_tools/             # Workflow management tools
test_workflows.py               # End-to-end tests
```

## How It Works

### 1. The Co-Worker Agent
A ReAct agent (like your CEO agent) that has tools to:
- **create_workflow** — Create a new workflow
- **add_block** — Add blocks (agent, tool, function, http, condition)
- **connect_blocks** — Wire blocks together
- **execute_workflow** — Run a workflow immediately
- **monitor_workflow** — Check execution history
- **list_workflows** — See all workflows
- **get_workflow** — Get workflow details

Plus integration tools: `slack_send`, `gmail`, `http_request`, `call_llm`, `run_function`

### 2. Workflow Storage
- Shared SQLite database (`workflows.db` by default)
- Tables: workflows, blocks, connections, triggers, executions
- No PostgreSQL, no Redis, no external dependencies

### 3. Execution Engine
1. Workflow loaded from DB
2. **DAG Builder** converts blocks + connections → execution graph
3. **Executor** processes blocks in topological order
4. **Variable Resolver** resolves `{{block.output.field}}` references
5. **Block Handlers** execute each block type
6. Results saved to executions table

### 4. Block Types
| Type | What It Does |
|------|-------------|
| `start` | Entry point (no-op) |
| `agent` | LLM call with system prompt + model |
| `tool` | Call a registered tool (slack, gmail, http, etc.) |
| `function` | Execute Python code |
| `http` | Make an HTTP request |
| `condition` | Branch based on a condition |
| `variable` | Set workflow variables |
| `end` | Exit point (no-op) |

## Quick Start

### Run the Co-Worker Server
```bash
cd /Users/hritvik/Downloads/ceo-agent
export OPENROUTER_API_KEY="sk-or-..."
uvicorn workflows_server:app --reload --port 8002
```

### Use the API
```bash
# Health check
curl http://localhost:8002/health

# List tools
curl http://localhost:8002/tools

# List workflows
curl http://localhost:8002/workflows

# Send a task to the co-worker
curl -X POST http://localhost:8002/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Create a workflow that checks Gmail for unread emails and sends a summary to Slack",
    "model": "openai/gpt-4o"
  }'

# Execute a workflow directly
curl -X POST http://localhost:8002/workflows/execute \
  -H "Content-Type: application/json" \
  -d '{"workflow_id": "wf_abc123"}'
```

### Use via WebSocket
```javascript
const ws = new WebSocket('ws://localhost:8002/ws');

ws.onmessage = (event) => {
  const msg = JSON.parse(event.data);
  
  if (msg.type === 'chunk') process.stdout.write(msg.content);
  if (msg.type === 'action') console.log(`Tool: ${msg.tool}`, msg.input);
  if (msg.type === 'observation') console.log(`Result: ${msg.content}`);
  if (msg.type === 'final') console.log(`Done: ${msg.content}`);
};

ws.onopen = () => {
  ws.send(JSON.stringify({
    type: 'message',
    content: 'Create a workflow that monitors my inbox and sends daily summaries'
  }));
};
```

### Use Programmatically (Python)
```python
import asyncio
from workflows.coworker import create_coworker_session

async def main():
    session = await create_coworker_session()
    
    async for event in session.send_message(
        "Create a workflow that fetches weather data and emails it to me"
    ):
        if event["type"] == "final":
            print(event["content"])
        elif event["type"] == "action":
            print(f"Calling: {event['tool']}")
        elif event["type"] == "error":
            print(f"Error: {event['message']}")

asyncio.run(main())
```

### Add Your Own Tools
```python
from workflows.tools.base import BaseTool, ToolResult
from workflows.tools.registry import registry

class MyCustomTool(BaseTool):
    name = "my_tool"
    description = "Does something custom"
    category = "custom"
    
    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "input": {"type": "string", "description": "Something"},
            },
            "required": ["input"],
        }
    
    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        # Your logic here
        return ToolResult(
            success=True,
            output=f"Processed: {parameters['input']}",
        )

# Register it
registry.register(MyCustomTool())
# Now the co-worker can use it
```

## Environment Variables

| Variable | Purpose |
|----------|---------|
| `OPENROUTER_API_KEY` | LLM calls (OpenAI, Anthropic, etc.) |
| `SLACK_BOT_TOKEN` | Slack integration |
| `GMAIL_ACCESS_TOKEN` | Gmail integration |
| `APP_DB` | Shared SQLite database path for auth, employee, and workflow data |

## What's Next — Add More Tools

The system is designed to grow. Add tools for:
- **Databases**: PostgreSQL, MySQL, MongoDB
- **CRMs**: HubSpot, Salesforce
- **Project Management**: Linear, Jira, Asana
- **Search**: Google, Tavily, DuckDuckGo
- **Document Processing**: Google Docs, Notion, Confluence

Each tool is just a class implementing `BaseTool`. Register it and the co-worker can use it.

## Key Differences from Sim

| Sim | This System |
|-----|------------|
| 8,396 files, 586MB | ~25 files, ~200KB |
| Needs PostgreSQL, Redis, BullMQ | SQLite only |
| Visual drag-and-drop | Code/API driven |
| 208 pre-built tools | Add as you need |
| Licensed | 100% yours |
| Multi-tenant, SSO, dashboards | Focused on automation engine |

## File Count

```
$ find workflows -name "*.py" | wc -l
     22 files
```

That's the entire system.
