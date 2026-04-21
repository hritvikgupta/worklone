# Engineering Lead

An autonomous engineering lead that triages GitHub issues, reviews PRs, manages Linear sprints, and posts updates to Slack. Keeps your engineering team unblocked and your backlog clean.

## Full Example

```python
import os
from worklone_employee import Employee, Github, Linear, Slack, InMemoryTokenStore

os.environ["OPENROUTER_API_KEY"] = "sk-or-..."

store = InMemoryTokenStore()
store.seed("eng_lead", "linear", {"access_token": "lin_api_..."})
store.seed("eng_lead", "slack",  {"access_token": "xoxb-..."})

github = Github(api_key="ghp_...")
linear = Linear(client_id="...", client_secret="...", token_store=store)
slack  = Slack(client_id="...",  client_secret="...", token_store=store)

emp = Employee(
    name="Kai",
    description="Senior engineering team lead",
    model="openai/gpt-4o",
    system_prompt="""You are Kai, a senior engineering lead.

Your responsibilities:
- Triage new GitHub issues: label, assign to the right engineer, estimate priority
- Review open PRs: check for missing description, unresolved comments, failing CI
- Manage Linear sprint: flag overdue issues, update statuses, surface blockers
- Post daily standup summary to Slack #engineering channel
- Escalate P0 bugs immediately via Slack DM to the on-call engineer
- Keep the backlog clean — archive stale issues older than 90 days

Be direct. Use bullet points. Every action should be logged.""",
    owner_id="eng_lead",
    db="./kai.db",
)

emp.enable_evolution()

for tool in [*github.all(), *linear.all(), *slack.all()]:
    emp.add_tool(tool)

# Morning sprint review
result = emp.run(
    "Check GitHub for new issues in acme/backend opened in the last 24h, "
    "triage them with labels and priority, then post a summary to #engineering."
)
print(result)

# PR review
result = emp.run(
    "List all open PRs in acme/backend that have been open more than 3 days "
    "and haven't been reviewed. Add a comment asking for review."
)
print(result)
```

## What Kai Can Do

- **Issue triage** — labels, assigns, and prioritizes new GitHub issues automatically
- **PR management** — flags stale PRs, missing descriptions, failing checks
- **Sprint health** — surfaces overdue Linear issues and blockers
- **Standup posts** — generates and posts daily summaries to Slack
- **On-call escalation** — DMs engineers for P0 issues immediately

## Sample Prompts

```python
emp.run("Triage all unlabeled issues in acme/backend and assign them by domain.")
emp.run("Which PRs have merge conflicts right now?")
emp.run("Post the sprint progress update to #engineering — what's done, in progress, blocked.")
emp.run("Create a Linear issue for the login timeout bug reported in Slack #bugs.")
emp.run("Summarize what the team shipped this week across all repos.")
```

## Recommended Model

`openai/gpt-4o` — strong at structured analysis, code context, and concise technical summaries.
