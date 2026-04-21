# Linear Integration

78 tools for managing issues, projects, cycles, teams, labels, and more.

## Setup

```python
from worklone_employee import Linear, InMemoryTokenStore

store = InMemoryTokenStore()
store.seed("user_123", "linear", {"access_token": "lin_api_xxxxxxxxxxxx"})

linear = Linear(
    client_id="YOUR_LINEAR_CLIENT_ID",
    client_secret="YOUR_LINEAR_CLIENT_SECRET",
    token_store=store,
)

emp = Employee(name="Aria", owner_id="user_123")
for tool in linear.all():
    emp.add_tool(tool)
```

You can use a Linear personal API key directly as the `access_token`, or go through OAuth for user-level access.

## Available Tools (Selected)

| Tool | Description |
|------|-------------|
| `Linear Issue Writer` | Create a new issue |
| `linear_update_issue` | Update issue fields |
| `linear_archive_issue` | Archive an issue |
| `linear_delete_issue` | Delete an issue |
| `linear_read_issues` | List and filter issues |
| `linear_search_issues` | Search issues by text |
| `linear_get_issue` | Get issue details |
| `linear_create_comment` | Add a comment to an issue |
| `linear_create_project` | Create a project |
| `linear_list_projects` | List all projects |
| `linear_list_teams` | List all teams |
| `linear_list_users` | List team members |
| `linear_create_label` | Create a label |
| `linear_create_cycle` | Create a sprint cycle |
| `linear_get_active_cycle` | Get the current active cycle |

78 tools total — full Linear GraphQL API coverage.

## Common Usage

```python
emp.run("Create a Linear issue titled 'Update onboarding flow' assigned to the design team.")
emp.run("List all in-progress issues for the engineering team this cycle.")
emp.run("What issues are blocking the Q2 launch project?")
```
