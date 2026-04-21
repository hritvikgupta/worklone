# Human-in-the-Loop

Human-in-the-loop lets your employee pause mid-task and wait for a human to approve or reject an action before continuing. This is critical for high-stakes operations like sending emails, creating charges, or modifying production data.

## How It Works

When the employee calls the `ask_user` tool, execution pauses and your registered callback fires. You handle the approval however you want — show a UI, send a Slack message, log it — then return an approval response.

## Registering a Callback

```python
from worklone_employee import Employee

emp = Employee(
    name="Aria",
    model="anthropic/claude-sonnet-4-5",
    system_prompt="For any action that affects external systems, always ask_user for approval first.",
)

@emp.on_approval_needed
def handle_approval(event: dict) -> dict:
    print(f"\nApproval needed:")
    print(f"  Message : {event.get('message', '')}")

    plan = event.get("plan", {})
    tasks = plan.get("tasks", [])
    if tasks:
        print(f"  Plan ({len(tasks)} steps):")
        for task in tasks:
            print(f"    • {task.get('title', '')}")

    answer = input("\nApprove? (y/n): ").strip().lower()
    return {"approved": answer == "y", "message": "User reviewed the plan."}

result = emp.run("Search for the latest AI news and send a summary to the team Slack.")
```

## Event Structure

The `event` dict passed to your callback:

```python
{
    "message": "I'm about to send a Slack message. Please approve.",
    "plan": {
        "tasks": [
            {"title": "Search the web for AI news"},
            {"title": "Summarize findings"},
            {"title": "Post to #general Slack channel"},
        ]
    }
}
```

## Return Value

Your callback must return a dict:

```python
# Approve
return {"approved": True, "message": "Looks good, proceed."}

# Reject
return {"approved": False, "message": "Do not send the Slack message."}
```

When rejected, the employee receives the message and decides how to respond — typically stopping the current plan or trying an alternative.

## Auto-Approve Mode

For testing or non-sensitive environments, skip approvals automatically:

```python
emp = Employee(
    name="Aria",
    model="anthropic/claude-haiku-4-5",
    auto_approve=True,
)
```

## Async Callbacks

Your callback can be async:

```python
@emp.on_approval_needed
async def handle_approval(event: dict) -> dict:
    # Send a push notification, wait for user response, etc.
    approved = await send_approval_request_to_mobile(event)
    return {"approved": approved}
```

## Best Practices

Use human-in-the-loop whenever the employee might:

- **Send messages** — email, Slack, SMS
- **Modify data** — update CRM records, write to databases
- **Charge money** — create Stripe charges or invoices
- **Run shell commands** — in production environments
- **Delete anything** — files, records, messages

The system prompt is the best place to enforce this:

```python
emp = Employee(
    system_prompt=(
        "Before taking any action that affects external systems "
        "(sending messages, modifying data, charging money), "
        "you MUST call ask_user to show the plan and get approval. "
        "Never call execution tools before the user has approved."
    )
)
```
