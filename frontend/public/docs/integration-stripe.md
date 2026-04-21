# Stripe Integration

50 tools for managing customers, products, prices, invoices, subscriptions, and payment intents.

## Setup

```python
from worklone_employee import Employee, Stripe

stripe = Stripe(api_key="sk_live_xxxxxxxxxxxxxxxxxxxx")

emp = Employee(name="Aria", owner_id="user_123")
for tool in stripe.all():
    emp.add_tool(tool)
```

Use `sk_test_...` for test mode, `sk_live_...` for production.

## Available Tools (Selected)

| Tool | Description |
|------|-------------|
| `stripe_create_customer` | Create a new customer |
| `stripe_update_customer` | Update customer details |
| `stripe_list_customers` | List customers with filters |
| `stripe_search_customers` | Search customers |
| `stripe_create_product` | Create a product |
| `stripe_create_price` | Create a price for a product |
| `stripe_create_subscription` | Create a subscription |
| `stripe_cancel_subscription` | Cancel a subscription |
| `stripe_create_invoice` | Create an invoice |
| `stripe_finalize_invoice` | Finalize and send an invoice |
| `stripe_pay_invoice` | Pay an invoice |
| `stripe_create_payment_intent` | Create a payment intent |
| `stripe_capture_payment_intent` | Capture a payment |
| `stripe_list_charges` | List charges |
| `stripe_retrieve_subscription` | Get subscription details |

50 tools total — full Stripe API coverage.

## Common Usage

```python
emp.run("Create a Stripe customer for alice@company.com with name Alice Johnson.")
emp.run("List all active subscriptions and tell me which ones expire this month.")
emp.run("Create an invoice for customer cus_xxx for $499 and send it.")
```

## Safety Note

Always use human-in-the-loop when your employee might create charges or modify billing:

```python
emp = Employee(
    name="Aria",
    system_prompt=(
        "Before creating any Stripe charge, invoice, or subscription, "
        "you MUST call ask_user to get explicit approval."
    ),
)
```
