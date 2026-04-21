# HR Recruiter

An autonomous recruiter that screens candidates, drafts outreach emails, schedules interviews via Google Calendar, and tracks applicants — all without manual effort.

## Full Example

```python
import os
from worklone_employee import Employee, Gmail, GoogleCalendar, InMemoryTokenStore

os.environ["OPENROUTER_API_KEY"] = "sk-or-..."

store = InMemoryTokenStore()
store.seed("recruiter_001", "gmail", {
    "access_token": "ya29...",
    "refresh_token": "1//..."
})
store.seed("recruiter_001", "google_calendar", {
    "access_token": "ya29...",
    "refresh_token": "1//..."
})

gmail    = Gmail(client_id="...", client_secret="...", token_store=store)
calendar = GoogleCalendar(client_id="...", client_secret="...", token_store=store)

emp = Employee(
    name="Riley",
    description="Senior technical recruiter",
    model="anthropic/claude-haiku-4-5",
    system_prompt="""You are Riley, a senior technical recruiter at a fast-growing startup.

Your responsibilities:
- Screen candidate emails and categorize: strong fit, possible fit, not a fit
- Draft personalized outreach to strong candidates — reference their specific background
- Schedule technical screens and team interviews via Google Calendar
- Send confirmation emails with interview details, prep resources, and what to expect
- Follow up with candidates who haven't responded within 5 days
- Keep the hiring manager updated with a weekly pipeline summary

Tone: warm, professional, enthusiastic about the company. Make candidates feel valued.
Never share salary ranges or equity details — redirect to the hiring manager.""",
    owner_id="recruiter_001",
    db="./riley.db",
)

emp.enable_evolution()

for tool in [*gmail.all(), *calendar.all()]:
    emp.add_tool(tool)

# Screen inbound applications
result = emp.run(
    "Check my inbox for new job applications received in the last 48 hours. "
    "Categorize them by fit for a senior backend engineer role "
    "and draft outreach emails for the top candidates."
)
print(result)

# Schedule interviews
result = emp.run(
    "Schedule a 45-minute technical screen with candidate Alice Chen "
    "for next Tuesday or Wednesday afternoon. "
    "Send her a calendar invite with the Zoom link and prep instructions."
)
print(result)
```

## What Riley Can Do

- **Application screening** — reads inbound emails, scores fit against job requirements
- **Candidate outreach** — personalized messages referencing specific background
- **Interview scheduling** — checks availability, creates calendar invites, sends confirmations
- **Follow-up sequences** — pings non-responders automatically
- **Pipeline summaries** — weekly digest of candidates by stage

## Sample Prompts

```python
emp.run("Which candidates applied for the ML engineer role this week? Rank them by fit.")
emp.run("Draft a rejection email for the 3 candidates who weren't a strong fit.")
emp.run("Send interview prep resources to everyone scheduled for a screen next week.")
emp.run("Which candidates haven't responded to our outreach in over a week?")
emp.run("Generate a weekly recruiter report: applications received, screens scheduled, offers extended.")
```

## Recommended Model

`anthropic/claude-haiku-4-5` — fast enough for high-volume screening, smart enough for personalized outreach.
