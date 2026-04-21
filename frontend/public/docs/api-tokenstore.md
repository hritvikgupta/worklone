# TokenStore Reference

`TokenStore` is the interface your application implements to store and retrieve OAuth tokens for integration tools. The SDK never stores tokens itself — it reads and writes through your store on every tool call.

## Interface

```python
from worklone_employee import TokenStore

class MyStore(TokenStore):
    async def get(self, user_id: str, provider: str) -> dict | None:
        """Return tokens for this user+provider, or None if not found."""
        ...

    async def set(self, user_id: str, provider: str, tokens: dict) -> None:
        """Save or update tokens for this user+provider."""
        ...

    async def delete(self, user_id: str, provider: str) -> None:
        """Remove tokens for this user+provider."""
        ...
```

## Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `user_id` | `str` | Your application's user identifier |
| `provider` | `str` | Integration name: `"gmail"`, `"slack"`, `"linear"`, etc. |
| `tokens` | `dict` | Dict with at minimum `access_token` and `refresh_token` keys |

## Token Dict Structure

```python
{
    "access_token": "ya29.xxx",       # required — used for API calls
    "refresh_token": "1//xxx",        # required for OAuth — used to refresh
    "expires_in": 3600,               # optional
    "token_type": "Bearer",           # optional
    # Salesforce only:
    "instance_url": "https://xxx.salesforce.com"
}
```

## Implementations

### InMemoryTokenStore (built-in, dev only)

```python
from worklone_employee import InMemoryTokenStore

store = InMemoryTokenStore()
store.seed("alice", "gmail", {
    "access_token": "ya29.xxx",
    "refresh_token": "1//xxx"
})
```

Not for production — data is lost when the process exits.

### PostgreSQL Example

```python
import asyncpg
from worklone_employee import TokenStore

class PostgresTokenStore(TokenStore):
    def __init__(self, pool: asyncpg.Pool):
        self.pool = pool

    async def get(self, user_id: str, provider: str) -> dict | None:
        row = await self.pool.fetchrow(
            "SELECT tokens FROM oauth_tokens WHERE user_id=$1 AND provider=$2",
            user_id, provider
        )
        return dict(row["tokens"]) if row else None

    async def set(self, user_id: str, provider: str, tokens: dict) -> None:
        await self.pool.execute(
            """
            INSERT INTO oauth_tokens (user_id, provider, tokens)
            VALUES ($1, $2, $3)
            ON CONFLICT (user_id, provider) DO UPDATE SET tokens=$3
            """,
            user_id, provider, tokens
        )

    async def delete(self, user_id: str, provider: str) -> None:
        await self.pool.execute(
            "DELETE FROM oauth_tokens WHERE user_id=$1 AND provider=$2",
            user_id, provider
        )
```

### Redis Example

```python
import json
import redis.asyncio as redis
from worklone_employee import TokenStore

class RedisTokenStore(TokenStore):
    def __init__(self, client: redis.Redis):
        self.r = client

    def _key(self, user_id: str, provider: str) -> str:
        return f"tokens:{user_id}:{provider}"

    async def get(self, user_id: str, provider: str) -> dict | None:
        val = await self.r.get(self._key(user_id, provider))
        return json.loads(val) if val else None

    async def set(self, user_id: str, provider: str, tokens: dict) -> None:
        await self.r.set(self._key(user_id, provider), json.dumps(tokens))

    async def delete(self, user_id: str, provider: str) -> None:
        await self.r.delete(self._key(user_id, provider))
```

## How the SDK Uses Your Store

On every tool call, the SDK:

1. Reads `user_id` from the agent's context (set by `owner_id` on the Employee)
2. Calls `store.get(user_id, provider)` to get the current access token
3. Makes the API call with that token
4. If the API returns 401 (expired token), calls the provider's refresh endpoint
5. Calls `store.set(user_id, provider, new_tokens)` to persist the refreshed tokens
6. Retries the original API call with the new token

Your application code never needs to handle token expiry.
