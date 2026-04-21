# Installation

## Requirements

- Python 3.11 or higher
- An API key from any supported provider

## Install the SDK

```bash
pip install worklone-employee
```

## Supported Providers

The SDK works with multiple LLM providers. Set the API key for whichever you use:

### OpenRouter (recommended — access 200+ models with one key)

```bash
export OPENROUTER_API_KEY=sk-or-...
```

```python
emp = Employee(model="anthropic/claude-sonnet-4-5")   # Claude
emp = Employee(model="openai/gpt-4o")                  # GPT-4o via OpenRouter
emp = Employee(model="google/gemini-2.0-flash")        # Gemini
emp = Employee(model="meta-llama/llama-3.3-70b-instruct")  # Llama
```

Get a key at [openrouter.ai](https://openrouter.ai).

### OpenAI (direct)

```bash
export OPENAI_API_KEY=sk-...
```

```python
emp = Employee(model="gpt-4o")
emp = Employee(model="gpt-4o-mini")
emp = Employee(model="o1-preview")
```

### Groq (fast inference)

```bash
export GROQ_API_KEY=gsk_...
```

```python
emp = Employee(model="llama-3.3-70b-versatile")
emp = Employee(model="mixtral-8x7b-32768")
emp = Employee(model="gemma2-9b-it")
```

### NVIDIA NIM

```bash
export NVIDIA_API_KEY=nvapi-...
```

```python
emp = Employee(model="meta/llama-3.1-405b-instruct")
emp = Employee(model="minimaxai/minimax-m2.7")
```

## Setting Keys in Code

```python
import os

os.environ["OPENROUTER_API_KEY"] = "sk-or-..."
os.environ["OPENAI_API_KEY"] = "sk-..."
os.environ["GROQ_API_KEY"] = "gsk_..."
```

Or with a `.env` file:

```bash
OPENROUTER_API_KEY=sk-or-...
OPENAI_API_KEY=sk-...
GROQ_API_KEY=gsk_...
```

```python
from dotenv import load_dotenv
load_dotenv()
```

## Verify Installation

```python
from worklone_employee import Employee

emp = Employee(name="Aria", model="anthropic/claude-haiku-4-5")
print(emp.run("Say hello in one sentence."))
```

## Upgrading

```bash
pip install --upgrade worklone-employee
```
