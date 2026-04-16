"""
OAuth provider configurations — single source of truth.
"""

OAUTH_PROVIDERS = {
    "google": {
        "name": "Gmail",
        "icon": "mail",
        "auth_url": "https://accounts.google.com/o/oauth2/v2/auth",
        "token_url": "https://oauth2.googleapis.com/token",
        "scopes": "https://www.googleapis.com/auth/gmail.modify",
    },
    "slack": {
        "name": "Slack",
        "icon": "message-circle",
        "auth_url": "https://slack.com/oauth/v2/authorize",
        "token_url": "https://slack.com/api/oauth.v2.access",
        "scopes": "channels:read,channels:history,groups:read,groups:history,chat:write,chat:write.public,im:write,im:history,im:read,users:read,files:write,files:read,reactions:write",
    },
    "notion": {
        "name": "Notion",
        "icon": "file-text",
        "auth_url": "https://api.notion.com/v1/oauth/authorize",
        "token_url": "https://api.notion.com/v1/oauth/token",
        "scopes": "",
    },
    "github": {
        "name": "GitHub",
        "icon": "github",
        "auth_url": "https://github.com/login/oauth/authorize",
        "token_url": "https://github.com/login/oauth/access_token",
        "scopes": "repo,user,read:org",
    },
    "jira": {
        "name": "Jira",
        "icon": "briefcase",
        "auth_url": "https://auth.atlassian.com/authorize",
        "token_url": "https://auth.atlassian.com/oauth/token",
        "scopes": "read:jira-work write:jira-work offline_access",
    },
    "salesforce": {
        "name": "Salesforce",
        "icon": "cloud",
        "auth_url": "https://login.salesforce.com/services/oauth2/authorize",
        "token_url": "https://login.salesforce.com/services/oauth2/token",
        "scopes": "api refresh_token",
    },
    "linear": {
        "name": "Linear",
        "icon": "git-commit",
        "auth_url": "https://linear.app/oauth/authorize",
        "token_url": "https://api.linear.app/oauth/token",
        "scopes": "read write",
    },
    "hubspot": {
        "name": "Hubspot",
        "icon": "share-2",
        "auth_url": "https://app.hubspot.com/oauth/authorize",
        "token_url": "https://api.hubapi.com/oauth/v1/token",
        "scopes": "contacts content reports",
    },
    "stripe": {
        "name": "Stripe",
        "icon": "credit-card",
        "auth_url": "https://connect.stripe.com/oauth/authorize",
        "token_url": "https://connect.stripe.com/oauth/token",
        "scopes": "read_write",
    },
    "google_drive": {
        "name": "Google Drive",
        "icon": "hard-drive",
        "auth_url": "https://accounts.google.com/o/oauth2/v2/auth",
        "token_url": "https://oauth2.googleapis.com/token",
        "scopes": "https://www.googleapis.com/auth/drive",
    },
    "google_calendar": {
        "name": "Google Calendar",
        "icon": "calendar",
        "auth_url": "https://accounts.google.com/o/oauth2/v2/auth",
        "token_url": "https://oauth2.googleapis.com/token",
        "scopes": "https://www.googleapis.com/auth/calendar",
    },
}
