# Evolution & Memory

Evolution gives your AI employee the ability to learn from conversations. It extracts facts about users, detects successful task patterns, and applies that knowledge automatically in future sessions.

## Enabling Evolution

```python
emp = Employee(
    name="Aria",
    model="anthropic/claude-sonnet-4-5",
    db="./aria.db",
    owner_id="user_123",
)

emp.enable_evolution()
```

## Memory Evolution

Every 8 conversation turns, the employee triggers a background memory review:

1. **Analysis** — reviews recent conversation history
2. **Extraction** — identifies key facts: user name, preferences, context, constraints
3. **Storage** — saves facts to the database linked to `owner_id`

On the next session, stored memories are injected automatically into the system prompt.

```python
# First session
emp = Employee(name="Aria", db="./aria.db", owner_id="alice")
emp.enable_evolution()
emp.run("My name is Alice. I work in fintech and prefer concise answers.")
# After 8 turns, Aria extracts and saves facts

# New session
emp2 = Employee(name="Aria", db="./aria.db", owner_id="alice")
emp2.enable_evolution()
result = emp2.run("What do you know about me?")
# → "Your name is Alice. You work in fintech and prefer concise answers."
```

## Skill Evolution

Every 10 tool calls, the employee runs a background skill review:

1. **Pattern Recognition** — analyzes tool sequences that successfully solved complex tasks
2. **Proceduralization** — converts the pattern into a documented procedure
3. **Storage** — saves the skill with a proficiency level

Skills are injected into future sessions, reducing reasoning overhead for known task types.

## Static Skills

Assign skills manually without waiting for evolution:

```python
emp.add_skill(
    skill_name="Weekly Sales Report",
    category="analytics",
    proficiency_level=90,
    description="Query the sales database, compute week-over-week metrics, and post to #sales-team Slack."
)
```

## Multi-User Isolation

Memory and skills are scoped to `owner_id`. Two users with the same employee name have completely separate memories:

```python
emp_alice = Employee(name="Aria", db="./aria.db", owner_id="alice")
emp_bob   = Employee(name="Aria", db="./aria.db", owner_id="bob")
# alice's memory never leaks to bob
```

## Persistence

Evolution data persists in the SQLite database across process restarts. Use `db=":memory:"` to disable persistence for stateless deployments.

## Background Processing

Evolution reviews run in background threads — they do not block `emp.run()`. Memory appears automatically in sessions after 8+ conversation turns.
