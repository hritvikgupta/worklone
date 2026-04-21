# Integrations Overview

The Worklone SDK ships with **406 pre-built tools** across 12 integrations. Every integration uses a **TokenStore pattern** — your app stores tokens in its own database, the SDK reads through your store per user. No credentials are ever stored on Worklone servers.

## Available Integrations

| Integration | Tools | Auth |
|------------|-------|------|
| Gmail | 22 | Google OAuth |
| Slack | 25 | OAuth / Bot Token |
| Linear | 78 | OAuth |
| GitHub | 83 | API Key (PAT) |
| Google Calendar | 11 | Google OAuth |
| Google Sheets | 14 | Google OAuth |
| Google Drive | 17 | Google OAuth |
| HubSpot | 39 | OAuth |
| Jira | 23 | Atlassian OAuth |
| Stripe | 50 | API Key |
| Salesforce | 35 | OAuth |
| Notion | 9 | API Key |

## TokenStore Pattern

Your app owns all tokens. You implement a simple store interface:

```python
from worklone_employee import TokenStore

class MyPostgresStore(TokenStore):
    async def get(self, user_id: str, provider: str) -> dict | None:
        row = await db.fetchrow(
            "SELECT tokens FROM oauth_tokens WHERE user_id=$1 AND provider=$2",
            user_id, provider
        )
        return row["tokens"] if row else None

    async def set(self, user_id: str, provider: str, tokens: dict) -> None:
        await db.execute(
            "INSERT INTO oauth_tokens (user_id, provider, tokens) VALUES ($1,$2,$3) "
            "ON CONFLICT (user_id, provider) DO UPDATE SET tokens=$3",
            user_id, provider, tokens
        )

    async def delete(self, user_id: str, provider: str) -> None:
        await db.execute(
            "DELETE FROM oauth_tokens WHERE user_id=$1 AND provider=$2",
            user_id, provider
        )
```

## Quick Setup

### OAuth Integrations (Gmail, Slack, Linear, etc.)

**Step 1 — First time per user (one-time OAuth flow):**

```python
from worklone_employee import Gmail

# Generate login URL and send to user
url = Gmail.get_auth_url(
    client_id="YOUR_GOOGLE_CLIENT_ID",
    client_secret="YOUR_GOOGLE_CLIENT_SECRET",
    redirect_uri="https://yourapp.com/oauth/callback"
)
# User visits URL → clicks Allow → Google redirects to your callback

# In your /oauth/callback route:
tokens = await Gmail.exchange_code(
    code=request.params["code"],
    client_id="YOUR_GOOGLE_CLIENT_ID",
    client_secret="YOUR_GOOGLE_CLIENT_SECRET",
    redirect_uri="https://yourapp.com/oauth/callback"
)
await store.set(current_user_id, "gmail", tokens)
```

**Step 2 — Every run after (fully automatic):**

```python
store = MyPostgresStore()
gmail = Gmail(
    client_id="YOUR_GOOGLE_CLIENT_ID",
    client_secret="YOUR_GOOGLE_CLIENT_SECRET",
    token_store=store,
)

emp = Employee(name="Aria", owner_id=user_id)
for tool in gmail.all():
    emp.add_tool(tool)

# owner_id flows into tool context → store.get(user_id, "gmail") → token
emp.run("Check my inbox for urgent emails")
```

### API Key Integrations (GitHub, Stripe, Notion)

No OAuth needed — one key for all users:

```python
from worklone_employee import Github, Stripe, Notion

github = Github(api_key="ghp_xxxxxxxxxxxx")
stripe = Stripe(api_key="sk_live_xxxxxxxxxxxx")
notion = Notion(api_key="secret_xxxxxxxxxxxx")

for tool in github.all():
    emp.add_tool(tool)
```

## Combining Multiple Integrations

```python
from worklone_employee import Employee, Gmail, Slack, Github, InMemoryTokenStore

store = MyPostgresStore()

gmail  = Gmail(client_id=..., client_secret=..., token_store=store)
slack  = Slack(client_id=..., client_secret=..., token_store=store)
github = Github(api_key="ghp_xxx")

emp = Employee(name="Aria", owner_id=user_id)

for tool in [*gmail.all(), *slack.all(), *github.all()]:
    emp.add_tool(tool)

emp.run("Check my Gmail, post a Slack summary, and create a GitHub issue for any bugs mentioned.")
```

## InMemoryTokenStore

For local development and testing, use the built-in in-memory store:

```python
from worklone_employee import InMemoryTokenStore

store = InMemoryTokenStore()
store.seed("user_123", "gmail", {
    "access_token": "ya29.xxx",
    "refresh_token": "1//xxx"
})

gmail = Gmail(client_id="...", client_secret="...", token_store=store)
```

This is not for production — data is lost when the process exits.
