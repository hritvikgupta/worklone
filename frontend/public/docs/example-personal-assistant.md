# Personal Assistant

An executive assistant that manages your inbox, calendar, and daily briefings. Reads emails, drafts replies, schedules meetings, and keeps you on top of priorities.

## Full Example

```python
import os
from worklone_employee import Employee, Gmail, GoogleCalendar, InMemoryTokenStore

os.environ["OPENROUTER_API_KEY"] = "sk-or-..."

store = InMemoryTokenStore()
store.seed("user_123", "gmail", {
    "access_token": "ya29...",
    "refresh_token": "1//..."
})
store.seed("user_123", "google_calendar", {
    "access_token": "ya29...",
    "refresh_token": "1//..."
})

gmail = Gmail(
    client_id="YOUR_GOOGLE_CLIENT_ID",
    client_secret="YOUR_GOOGLE_CLIENT_SECRET",
    token_store=store,
)
calendar = GoogleCalendar(
    client_id="YOUR_GOOGLE_CLIENT_ID",
    client_secret="YOUR_GOOGLE_CLIENT_SECRET",
    token_store=store,
)

emp = Employee(
    name="Aria",
    description="Executive personal assistant",
    model="anthropic/claude-sonnet-4-5",
    system_prompt="""You are Aria, a world-class executive personal assistant.

Your responsibilities:
- Monitor and triage incoming emails by urgency and sender importance
- Draft professional replies that match the user's tone
- Manage calendar — schedule, reschedule, and check for conflicts
- Give a concise daily briefing: top emails, today's meetings, urgent tasks
- Never send an email or accept a meeting without confirming with the user first

Always be concise. Surface only what matters. Protect the user's time.""",
    owner_id="user_123",
    db="./aria.db",
)

emp.enable_evolution()

for tool in [*gmail.all(), *calendar.all()]:
    emp.add_tool(tool)

# Daily briefing
result = emp.run("Give me my morning briefing — unread emails and today's calendar.")
print(result)

# Draft a reply
result = emp.run(
    "Find the email from the investor about the Q2 deck and draft a reply "
    "saying I'll send it by Thursday EOD."
)
print(result)
```

## What Aria Can Do

- **Inbox triage** — reads unread emails, flags urgent ones, groups by sender
- **Draft replies** — writes professional responses in your voice
- **Calendar management** — lists today's events, checks free slots, schedules meetings
- **Daily briefing** — top emails + calendar in one summary
- **Follow-up tracking** — identifies emails waiting on a reply

## Sample Prompts

```python
emp.run("What emails need my attention today?")
emp.run("Draft a reply to John's invoice email saying payment goes out Friday.")
emp.run("Do I have any conflicts on Thursday afternoon?")
emp.run("Schedule a 30-minute call with Alice next week, avoid Mondays.")
emp.run("Summarize everything I missed while I was traveling.")
```

## Recommended Model

`anthropic/claude-sonnet-4-5` — best at following nuanced instructions and writing in your voice.
