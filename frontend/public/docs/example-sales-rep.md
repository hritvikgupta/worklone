# Sales Rep

An autonomous sales development rep that researches prospects, manages the CRM, drafts outreach emails, and tracks deal progress across HubSpot and Gmail.

## Full Example

```python
import os
from worklone_employee import Employee, Gmail, Hubspot, InMemoryTokenStore

os.environ["OPENROUTER_API_KEY"] = "sk-or-..."

store = InMemoryTokenStore()
store.seed("rep_001", "gmail", {"access_token": "ya29...", "refresh_token": "1//..."})
store.seed("rep_001", "hubspot", {"access_token": "pat-na1-..."})

gmail   = Gmail(client_id="...", client_secret="...", token_store=store)
hubspot = Hubspot(client_id="...", client_secret="...", token_store=store)

emp = Employee(
    name="Max",
    description="Senior sales development representative",
    model="anthropic/claude-sonnet-4-5",
    system_prompt="""You are Max, a senior SDR (Sales Development Representative).

Your responsibilities:
- Research prospects using web search before any outreach
- Create and update HubSpot contacts, companies, and deals accurately
- Draft personalized cold emails based on prospect's role, company, and pain points
- Track deal stages and flag stalled opportunities
- Never send an email without showing the draft to the user first
- Log all outreach in HubSpot immediately after sending

Tone: confident, concise, value-focused. No fluff. Every message should have one clear CTA.""",
    owner_id="rep_001",
    db="./max.db",
)

emp.enable_evolution()
emp.use_tools(["web_search"])

for tool in [*gmail.all(), *hubspot.all()]:
    emp.add_tool(tool)

# Research and create a contact
result = emp.run(
    "Research TechCorp Inc and their CTO Sarah Johnson. "
    "Create a HubSpot contact for her and draft a cold email about our AI employee platform."
)
print(result)

# Pipeline review
result = emp.run(
    "Show me all deals in 'Proposal Sent' stage that haven't had activity in 7 days."
)
print(result)
```

## What Max Can Do

- **Prospect research** — web searches company, role, recent news before outreach
- **CRM management** — creates and updates HubSpot contacts, companies, deals
- **Email drafting** — personalized cold emails with clear CTAs
- **Pipeline review** — identifies stalled deals, summarizes deal stages
- **Follow-up sequences** — drafts multi-touch follow-up emails

## Sample Prompts

```python
emp.run("Find 5 fintech CTOs in New York and create HubSpot contacts for each.")
emp.run("Draft a follow-up email to anyone who opened my proposal but didn't reply.")
emp.run("Update deal D-2231 to Closed Won with $45,000 ARR.")
emp.run("Which of my deals are most likely to close this quarter?")
emp.run("Generate a weekly pipeline report — deals by stage and total ARR.")
```

## Recommended Model

`anthropic/claude-sonnet-4-5` — strong at research synthesis and writing persuasive copy.
