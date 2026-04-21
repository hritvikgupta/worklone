# Research Analyst

An autonomous research analyst that searches the web, synthesizes information, compares competitors, and produces structured reports — on demand or on a schedule.

## Full Example

```python
import os
from worklone_employee import Employee

os.environ["OPENROUTER_API_KEY"] = "sk-or-..."

emp = Employee(
    name="Nova",
    description="Senior market research analyst",
    model="anthropic/claude-sonnet-4-5",
    system_prompt="""You are Nova, a senior market research analyst.

Your responsibilities:
- Search multiple sources before forming any conclusion
- Always cite your sources inline (company name, publication, or URL)
- Structure reports with: Executive Summary, Key Findings, Data Points, Implications
- Flag when data is older than 6 months or from a single source
- Compare competitors objectively — no editorializing
- Quantify everything possible: market size, growth rates, user counts, revenue

Tone: analytical, precise, data-driven. Never speculate without labeling it as such.""",
    owner_id="user_123",
    db="./nova.db",
)

emp.enable_evolution()
emp.use_tools(["web_search", "web_extract", "http_request"])

# Market research
result = emp.run(
    "Research the AI agent developer tools market. "
    "Who are the top 5 players, what are their pricing models, "
    "and what's the estimated market size for 2025?"
)
print(result)

# Competitor analysis
result = emp.run(
    "Compare Worklone, Crew AI, and LangChain as AI agent frameworks. "
    "Focus on: ease of use, multi-agent support, tool ecosystem, and pricing."
)
print(result)
```

## What Nova Can Do

- **Market research** — multi-source web research with citations
- **Competitor analysis** — structured side-by-side comparisons
- **Industry reports** — formatted with executive summary, findings, implications
- **News monitoring** — track topics and surface relevant developments
- **Data synthesis** — pull numbers from multiple sources into one coherent view

## Sample Prompts

```python
emp.run("What are the top 10 YC companies in the AI space from the last 2 batches?")
emp.run("Research Stripe's pricing model and compare it to Braintree and Adyen.")
emp.run("What's the current state of the LLM inference market? Who are the key players?")
emp.run("Find all publicly available data on OpenAI's revenue and growth rate.")
emp.run(
    "Write a competitive intelligence report on Notion, Confluence, and Coda. "
    "Focus on enterprise adoption and integrations."
)
```

## Recommended Model

`anthropic/claude-sonnet-4-5` — best at long-form synthesis, structured output, and following research instructions precisely.

## Tip: Persistent Research Memory

Enable evolution so Nova remembers what she's already researched:

```python
emp.enable_evolution()

# Session 1
emp.run("Research the AI coding assistant market.")

# Session 2 — Nova already knows the context
emp.run("Now do the same analysis but focused on enterprise buyers only.")
```
