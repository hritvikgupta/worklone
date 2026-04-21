# HubSpot Integration

39 tools for managing contacts, companies, deals, tickets, and more across the HubSpot CRM.

## Setup

```python
from worklone_employee import Employee, Hubspot, InMemoryTokenStore

store = InMemoryTokenStore()
store.seed("user_123", "hubspot", {"access_token": "your_hubspot_access_token"})

hubspot = Hubspot(
    client_id="YOUR_HUBSPOT_CLIENT_ID",
    client_secret="YOUR_HUBSPOT_CLIENT_SECRET",
    token_store=store,
)

emp = Employee(name="Aria", owner_id="user_123")
for tool in hubspot.all():
    emp.add_tool(tool)
```

## Available Tools (Selected)

| Tool | Description |
|------|-------------|
| `hubspot_create_contact` | Create a new contact |
| `hubspot_get_contact` | Get contact details |
| `hubspot_update_contact` | Update contact fields |
| `hubspot_search_contacts` | Search contacts |
| `hubspot_list_contacts` | List contacts |
| `hubspot_create_company` | Create a company |
| `hubspot_search_companies` | Search companies |
| `hubspot_create_deal` | Create a deal |
| `hubspot_update_deal` | Update deal stage or fields |
| `hubspot_list_deals` | List deals |
| `hubspot_search_deals` | Search deals |
| `hubspot_create_ticket` | Create a support ticket |
| `hubspot_update_ticket` | Update a ticket |
| `hubspot_list_tickets` | List tickets |
| `hubspot_get_users` | Get HubSpot users/owners |

39 tools total — full HubSpot CRM API coverage.

## Common Usage

```python
emp.run("Create a HubSpot contact for John Smith at john@acme.com from Acme Corp.")
emp.run("List all deals in the 'Proposal Sent' stage and sort by amount.")
emp.run("Update deal deal_id_123 to stage 'Closed Won' with amount $25,000.")
emp.run("Search for all contacts from domain acme.com.")
```
