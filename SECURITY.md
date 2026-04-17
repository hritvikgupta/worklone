# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| latest  | :white_check_mark: |

## Reporting a Vulnerability

We take the security of Worklone seriously. If you believe you have found a security vulnerability, please report it to us as described below.

**Please do NOT report security vulnerabilities through public GitHub issues.**

Instead, please report them via email to **[YOUR_SECURITY_EMAIL]**. You should receive a response within 48 hours. If for some reason you do not, please follow up via email to ensure we received your original message.

Please include the following information:

- Type of issue (e.g., buffer overflow, SQL injection, cross-site scripting, etc.)
- Full paths of source file(s) related to the manifestation of the issue
- The location of the affected source code (tag/branch/commit or direct URL)
- Any special configuration required to reproduce the issue
- Step-by-step instructions to reproduce the issue
- Proof-of-concept or exploit code (if possible)
- Impact of the issue, including how an attacker might exploit it

## Preferred Practices

- Store API keys and credentials in `.env` files, never commit them to the repository
- Use HTTPS in production deployments
- Regularly rotate API keys and tokens
- Review and restrict CORS origins to only trusted domains
- Keep dependencies updated (`pip install --upgrade -r requirements.txt` and `npm update`)
- Use strong passwords for user accounts
- Never expose the Worklone backend directly to the internet without authentication

## Security Measures in Worklone

- **Authentication**: Session-based auth with token expiration, API key management
- **Data isolation**: All records scoped to `owner_id` for multi-tenant safety
- **Password hashing**: Salted SHA-256 for user passwords
- **Input validation**: Pydantic models for all API request/response schemas
- **No external data leakage**: 100% self-hosted, no telemetry or data collection
