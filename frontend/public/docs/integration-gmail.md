# Gmail Integration

22 tools for reading, sending, searching, and managing Gmail.

## Setup

### 1. Create a Google OAuth App

1. Go to [Google Cloud Console](https://console.cloud.google.com/) → APIs & Services → Credentials
2. Create an OAuth 2.0 Client ID (Web application)
3. Add your redirect URI (e.g. `https://yourapp.com/oauth/callback`)
4. Enable the **Gmail API** in your project

### 2. First-Time Auth Per User

```python
from worklone_employee import Gmail

url = Gmail.get_auth_url(
    client_id="YOUR_CLIENT_ID.apps.googleusercontent.com",
    client_secret="GOCSPX-xxx",
    redirect_uri="https://yourapp.com/oauth/callback"
)
# Send this URL to your user — they click it, log in, allow access

# In your /oauth/callback route handler:
tokens = await Gmail.exchange_code(
    code=request.params["code"],
    client_id="YOUR_CLIENT_ID.apps.googleusercontent.com",
    client_secret="GOCSPX-xxx",
    redirect_uri="https://yourapp.com/oauth/callback"
)
# Save to your database
await store.set(user_id, "gmail", tokens)
```

### 3. Use in Your Employee

```python
from worklone_employee import Employee, Gmail

gmail = Gmail(
    client_id="YOUR_CLIENT_ID.apps.googleusercontent.com",
    client_secret="GOCSPX-xxx",
    token_store=store,
)

emp = Employee(name="Aria", owner_id=user_id)
for tool in gmail.all():
    emp.add_tool(tool)

emp.run("Check my inbox for emails from alice@company.com and summarize them.")
```

## Available Tools

| Tool | Description |
|------|-------------|
| `gmail_send` | Send an email |
| `Gmail Read` | Read emails from inbox or a specific folder |
| `gmail_search` | Search emails with Gmail query syntax |
| `gmail_draft` | Create an email draft |
| `gmail_list_threads` | List email threads |
| `gmail_list_labels` | List all Gmail labels |
| `gmail_mark_read` | Mark a message as read |
| `gmail_mark_unread` | Mark a message as unread |
| `gmail_archive` | Archive a message |
| `gmail_unarchive` | Move a message back to inbox |
| `gmail_delete` | Permanently delete a message |
| `gmail_add_label` | Add a label to a message |
| `gmail_remove_label` | Remove a label from a message |
| `gmail_move` | Move a message to a folder |
| `gmail_get_thread` | Get a full email thread |
| `gmail_trash_thread` | Move a thread to trash |
| `gmail_get_draft` | Get a specific draft |
| `gmail_list_drafts` | List all drafts |
| `gmail_delete_draft` | Delete a draft |
| `gmail_create_label` | Create a new label |
| `gmail_delete_label` | Delete a label |
| `gmail_untrash_thread` | Restore a thread from trash |

## Individual Tool Access

```python
# Add only the tools you need
emp.add_tool(gmail.send)
emp.add_tool(gmail.read)
emp.add_tool(gmail.search)
emp.add_tool(gmail.draft)
```

## Scopes

The default scope is `https://mail.google.com/` (full Gmail access). Pass custom scopes if needed:

```python
url = Gmail.get_auth_url(
    client_id="...",
    client_secret="...",
    redirect_uri="...",
    scopes=["https://www.googleapis.com/auth/gmail.readonly"]
)
```

## Token Refresh

Access tokens expire after 1 hour. The SDK automatically refreshes using the stored `refresh_token` — your store is updated with the new tokens transparently.
