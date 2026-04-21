# Slack Integration

25 tools for sending messages, reading channels, managing reactions, and more.

## Setup

### Option A — Bot Token (Simplest)

Create a Slack App, add OAuth scopes, install to workspace, copy the bot token:

```python
from worklone_employee import Slack, InMemoryTokenStore

store = InMemoryTokenStore()
store.seed("user_123", "slack", {"access_token": "xoxb-your-bot-token"})

slack = Slack(
    client_id="",      # not needed for bot tokens
    client_secret="",
    token_store=store,
)

emp = Employee(name="Aria", owner_id="user_123")
for tool in slack.all():
    emp.add_tool(tool)

emp.run("Post 'Daily standup in 5 minutes' to the #general channel.")
```

### Option B — Per-User OAuth

For user-level access (posting as individual users, reading private channels):

```python
from worklone_employee import Slack

url = Slack.get_auth_url(
    client_id="YOUR_SLACK_CLIENT_ID",
    redirect_uri="https://yourapp.com/slack/callback",
    scopes=["channels:read", "chat:write", "channels:history"]
)
# User visits URL → installs app → redirected back with code

tokens = await Slack.exchange_code(
    code=request.params["code"],
    client_id="YOUR_SLACK_CLIENT_ID",
    client_secret="YOUR_SLACK_CLIENT_SECRET",
    redirect_uri="https://yourapp.com/slack/callback"
)
await store.set(user_id, "slack", tokens)
```

## Available Tools

| Tool | Description |
|------|-------------|
| `slack_message` | Send a message to a channel or DM |
| `Slack Message Reader` | Read messages from a channel |
| `slack_list_channels` | List all channels in the workspace |
| `slack_list_users` | List all workspace members |
| `slack_add_reaction` | Add an emoji reaction to a message |
| `slack_remove_reaction` | Remove an emoji reaction |
| `slack_delete_message` | Delete a message |
| `slack_update_message` | Edit an existing message |
| `slack_get_message` | Get a specific message by timestamp |
| `slack_get_thread` | Get all replies in a thread |
| `slack_get_channel_info` | Get channel metadata |
| `slack_get_user` | Get a user's profile |
| `slack_get_user_presence` | Check if a user is online |
| `slack_list_members` | List members of a channel |
| `slack_invite_to_conversation` | Invite users to a channel |
| `slack_create_conversation` | Create a new channel |
| `slack_ephemeral_message` | Send a message only visible to one user |
| `slack_download` | Download a file from Slack |

## Common Usage

```python
emp.run("Post the daily sales summary to #sales-team and tag @john.")
emp.run("Read the last 10 messages in #engineering and summarize what the team is working on.")
emp.run("React with a thumbs up to the latest message in #general.")
```
