# Finance Controller

An autonomous finance controller that monitors Stripe revenue, generates invoices, tracks expenses, and produces financial summaries — with human approval before any money moves.

## Full Example

```python
import os
from worklone_employee import Employee, Stripe, Gmail, InMemoryTokenStore

os.environ["OPENROUTER_API_KEY"] = "sk-or-..."

store = InMemoryTokenStore()
store.seed("finance_001", "gmail", {
    "access_token": "ya29...",
    "refresh_token": "1//..."
})

stripe = Stripe(api_key="sk_live_...")
gmail  = Gmail(client_id="...", client_secret="...", token_store=store)

emp = Employee(
    name="Morgan",
    description="Finance controller and revenue operations",
    model="openai/gpt-4o",
    system_prompt="""You are Morgan, a meticulous finance controller.

Your responsibilities:
- Monitor Stripe for new charges, failed payments, and subscription changes
- Generate and send invoices to customers — always show the draft before sending
- Track overdue invoices and draft follow-up emails for collections
- Produce weekly and monthly revenue reports: MRR, ARR, churn, new revenue
- Flag any anomalies: unexpected charges, refunds over $500, churn spikes
- Never create a charge, issue a refund, or send an invoice without explicit approval

Be precise with numbers. Always show calculations. Cite the Stripe object IDs.""",
    owner_id="finance_001",
    db="./morgan.db",
)

emp.enable_evolution()

# Human-in-the-loop — required before any financial action
@emp.on_approval_needed
def require_approval(event: dict) -> dict:
    print(f"\n⚠️  Approval Required: {event.get('message', '')}")
    answer = input("Approve? (y/n): ").strip().lower()
    return {"approved": answer == "y"}

for tool in [*stripe.all(), *gmail.all()]:
    emp.add_tool(tool)

# Revenue report
result = emp.run(
    "Generate a monthly revenue report for last month. "
    "Include: total revenue, MRR, new customers, churned customers, and top 5 customers by spend."
)
print(result)

# Overdue invoices
result = emp.run(
    "Find all unpaid invoices older than 30 days. "
    "Draft a polite follow-up email for each and show me before sending."
)
print(result)
```

## What Morgan Can Do

- **Revenue monitoring** — tracks Stripe charges, subscriptions, and failed payments in real time
- **Invoice management** — creates, finalizes, and sends invoices (with approval)
- **Collections** — identifies overdue invoices, drafts follow-up emails
- **Financial reports** — MRR, ARR, churn rate, new revenue, top customers
- **Anomaly detection** — flags unexpected charges, large refunds, sudden churn

## Sample Prompts

```python
emp.run("What is our current MRR and how has it changed week over week?")
emp.run("List all customers whose subscriptions lapsed in the last 30 days.")
emp.run("Create an invoice for Acme Corp for $4,999 due in 14 days.")
emp.run("Which customers have failed payments right now? Draft retry emails.")
emp.run("Give me a breakdown of revenue by pricing plan for Q1.")
```

## Recommended Model

`openai/gpt-4o` — reliable with numbers, precise with structured financial data.

## Important: Always Use Human-in-the-Loop

Financial actions are irreversible. Always register an approval callback:

```python
@emp.on_approval_needed
def require_approval(event: dict) -> dict:
    # In production: send push notification, Slack message, or show UI modal
    return {"approved": False}  # default deny

emp = Employee(
    system_prompt="ALWAYS call ask_user before creating charges, refunds, or sending invoices."
)
```
