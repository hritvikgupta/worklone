# Sessions & Persistence

Every employee conversation is stored in a local SQLite database. Sessions let you resume conversations, maintain context across runs, and keep evolution data between Python processes.

## Database Location

By default, data is stored at `~/.worklone/sdk.db`. Specify a custom path to keep data next to your project:

```python
emp = Employee(
    name="Aria",
    db="./data/aria.db",
    owner_id="user_123",
)
```

## Sessions

A session is a single conversation thread. Every `emp.run()` call is part of the active session.

### Auto-Generated Sessions

If you don't specify a `session_id`, one is generated automatically each time:

```python
emp = Employee(name="Aria", db="./aria.db")
emp.run("Hello")  # new session every run
```

### Named Sessions

Specify a `session_id` to resume the same conversation:

```python
SESSION = "alice-daily-briefing"

# First run
emp = Employee(name="Aria", db="./aria.db", session_id=SESSION)
emp.run("My name is Alice and I work in fintech.")

# Later — Aria remembers everything in the session
emp2 = Employee(name="Aria", db="./aria.db", session_id=SESSION)
result = emp2.run("What is my name?")
# → "Your name is Alice."
```

### Resetting a Session

Clear the conversation history without losing evolution data:

```python
emp.reset()
```

## Multi-User Persistence

Use `owner_id` to isolate data between users. Each user gets their own memory and skills:

```python
# Alice's employee
emp_alice = Employee(
    name="Aria",
    db="./aria.db",
    owner_id="alice",
)

# Bob's employee — completely separate memory
emp_bob = Employee(
    name="Aria",
    db="./aria.db",
    owner_id="bob",
)
```

## What Gets Stored

The SQLite database stores:

| Table | Contents |
|-------|----------|
| `chat_sessions` | Session metadata (id, owner, model, title) |
| `chat_messages` | Full conversation history per session |
| `user_memory` | Extracted facts per `owner_id` (from evolution) |
| `skills` | Learned procedures per employee + owner (from evolution) |

## Production Recommendations

For production deployments with many users:

- Use a **separate database file per user** to avoid locking issues
- Or set `db=":memory:"` to disable persistence entirely for stateless workers
- Store the `session_id` in your app's session store so you can reconnect to it

```python
# Stateless — no disk writes
emp = Employee(name="Aria", db=":memory:")

# Per-user file
emp = Employee(
    name="Aria",
    db=f"./data/users/{user_id}.db",
    owner_id=user_id,
)
```
