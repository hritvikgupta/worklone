# Self-Learning System

Worklone employees don't just execute tasks — they **learn and improve** over time. The self-learning system (called the **Evolution System**) automatically captures knowledge from every interaction and uses it to make employees smarter.

---

## How It Works

```
Conversation → Background Review → LLM Analysis → Memory/Skills Created → Next Conversation
```

The evolution system runs **fire-and-forget** in a background thread pool (max 2 workers). It never blocks the main chat loop — learning happens silently while the employee continues working.

---

## Two Types of Learning

### 1. User Memory (Declarative Knowledge)

**What it stores:** Facts about a specific user.

| Category | Examples |
|----------|----------|
| Work style | "Prefers concise responses", "Works in EST timezone" |
| Preferences | "Uses Slack for communication", "Prefers GitHub over GitLab" |
| Goals | "Launching a SaaS product in Q2", "Hiring 5 engineers" |
| Communication patterns | "Likes bullet points", "Prefers data-driven decisions" |
| Domain expertise | "Expert in fintech", "Familiar with React but not Vue" |

**When it updates:** Every 8 conversation turns.

**How it works:**
1. Background thread reviews the full conversation
2. LLM analyzes the conversation for new facts
3. New facts are **merged** into existing memory (old facts preserved unless contradicted)
4. Memory is stored in `employee_user_memory` table

**Example:**

After this conversation:
> User: "I prefer to use RICE scoring for prioritization, not MoSCoW."
> User: "Also, I'm based in EST and prefer morning meetings."

The memory system stores:
```json
{
  "user_id": "user-123",
  "employee_id": "emp-456",
  "facts": [
    "Prefers RICE scoring for feature prioritization over MoSCoW",
    "Based in EST timezone",
    "Prefers morning meetings"
  ]
}
```

Next time the employee helps with prioritization, it will automatically use RICE scoring.

---

### 2. Learned Skills (Procedural Knowledge)

**What it stores:** Multi-step procedures discovered through trial-and-error.

| Category | Examples |
|----------|----------|
| Tool sequences | "To deploy to staging: build → push → run migration → restart" |
| API patterns | "Salesforce requires OAuth token refresh before each batch" |
| Workflows | "Creating a PR requires: branch → code → test → PR → review" |
| Non-obvious discoveries | "GitHub API rate limits can be bypassed with personal access tokens" |

**When it updates:** Every 10 tool iterations.

**How it works:**
1. Background thread reviews tool usage patterns
2. LLM identifies non-trivial, multi-step procedures worth saving
3. Writes them as markdown skill documents
4. Skills are versioned and stored in `employee_learned_skills` table

**Example:**

After an employee successfully:
1. Searches GitHub for similar issues
2. Creates a new issue with labels
3. Assigns it to the right person
4. Links it to a milestone

The system creates a learned skill:

```markdown
# Creating GitHub Issues with Full Context

When creating a GitHub issue for bug reports:

1. Search existing issues first to avoid duplicates
2. Create issue with labels: `bug`, `priority:high`
3. Assign to the team lead
4. Link to the current milestone
5. Add a comment with reproduction steps

Tools used: github_search_issues, github_create_issue, github_assign_issue
```

**Next time** the employee needs to create a bug report, it references this skill and follows the exact procedure — no trial-and-error needed.

---

## How Learning is Triggered

### Automatic Triggers

| Trigger | Condition | Review Type |
|---------|-----------|-------------|
| Conversation turns | Every 8 turns | User Memory |
| Tool iterations | Every 10 iterations | Learned Skills |

### Background Processing

Reviews run in a `ThreadPoolExecutor`:

```python
executor = ThreadPoolExecutor(max_workers=2)

# Fire-and-forget — never blocks main loop
executor.submit(review_user_memory, conversation, memory)
executor.submit(review_learned_skills, tool_calls, skills)
```

If the executor is busy, new reviews are queued. The main chat loop is never affected.

---

## How Learning is Used

### In System Prompts

Learned knowledge is automatically injected into the employee's system prompt:

```
You are Alex, a Sales Development Rep.

## User Context
- User prefers concise responses with bullet points
- User works in EST timezone
- User uses RICE scoring for prioritization

## Learned Skills
### Creating GitHub Issues with Full Context
When creating a GitHub issue for bug reports:
1. Search existing issues first...
...
```

This means the employee **remembers** and **applies** knowledge without being told.

### Skill Versioning

Skills are versioned to track evolution:

| Version | Change |
|---------|--------|
| v1 | Initial skill created |
| v2 | Updated with new API endpoint |
| v3 | Added error handling step |

Old versions are preserved for reference.

---

## LLM Prompts for Learning

### Memory Review Prompt

The LLM is instructed to look for:

- Work style preferences
- Domain expertise and knowledge
- Recurring goals or themes
- Communication patterns
- Explicit preferences ("I prefer...", "Always...", "Never...")

### Skill Review Prompt

The LLM is instructed to look for:

- Trial-and-error approaches that worked
- Multi-step procedures (3+ steps)
- Non-obvious tool/API discoveries
- Procedures worth repeating

### JSON Output Parsing

Both reviews expect JSON output from the LLM. Parsing is loose — handles:
- Fenced code blocks (```json ... ```)
- Direct JSON objects
- First `{...}` object found

---

## Storage Schema

### User Memory Table

```sql
CREATE TABLE employee_user_memory (
    id TEXT PRIMARY KEY,
    employee_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    facts TEXT,           -- JSON array of facts
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);
```

### Learned Skills Table

```sql
CREATE TABLE employee_learned_skills (
    id TEXT PRIMARY KEY,
    employee_id TEXT NOT NULL,
    name TEXT,
    content TEXT,         -- Markdown skill document
    version INTEGER,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);
```

---

## Learning Lifecycle

```
┌─────────────────────────────────────────────────────────────┐
│                    Learning Lifecycle                        │
│                                                              │
│  1. Employee interacts with user                            │
│         │                                                    │
│         ▼                                                    │
│  2. Conversation & tool usage recorded                      │
│         │                                                    │
│         ▼                                                    │
│  3. Background thread triggers review (every 8/10)          │
│         │                                                    │
│         ▼                                                    │
│  4. LLM analyzes for memory facts or learnable skills       │
│         │                                                    │
│         ▼                                                    │
│  5. New memory/skills stored in SQLite                      │
│         │                                                    │
│         ▼                                                    │
│  6. Next conversation includes updated memory/skills        │
│         │                                                    │
│         ▼                                                    │
│  7. Employee performs better with context                   │
│         │                                                    │
│         ▼                                                    │
│  8. Cycle repeats — continuous improvement                  │
└─────────────────────────────────────────────────────────────┘
```

---

## Benefits

| Benefit | Description |
|---------|-------------|
| **Personalization** | Employees adapt to each user's preferences |
| **Efficiency** | Learned skills eliminate repeated trial-and-error |
| **Consistency** | Procedures are followed the same way every time |
| **Autonomy** | Less human intervention needed over time |
| **Scalability** | Knowledge is captured and shared automatically |

---

## Configuration

Learning is enabled by default. No configuration needed.

### Customizing Review Frequency

The review thresholds (8 turns for memory, 10 iterations for skills) are hardcoded but can be modified in the evolution system source code:

```python
# backend/core/agents/evolution/evolution_system.py
MEMORY_REVIEW_INTERVAL = 8   # Review memory every N turns
SKILL_REVIEW_INTERVAL = 10   # Review skills every N iterations
```

### Disabling Learning

To disable learning for a specific employee, remove the evolution system from their agent pipeline. This is not recommended as it reduces the employee's effectiveness over time.

---

## Future Enhancements

- **Vector memory** — semantic search over long-term knowledge
- **Cross-employee learning** — skills learned by one employee shared with all
- **Skill validation** — test learned skills before applying them
- **Human review** — let users approve/reject learned skills
- **Skill marketplace** — share skills across Worklone instances
