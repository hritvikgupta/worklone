"""
Utility functions for the workflow engine.
"""

import uuid
import re
import json
import time
from typing import Any
from datetime import datetime


def generate_id(prefix: str = "") -> str:
    """Generate a unique ID."""
    uid = uuid.uuid4().hex[:12]
    if prefix:
        return f"{prefix}_{uid}"
    return uid


def now_iso() -> str:
    """Current time in ISO format."""
    return datetime.now().isoformat()


def resolve_template(text: str, variables: dict) -> str:
    """
    Resolve {{variable}} references in a string.
    
    Example: resolve_template("Hello {{name}}", {"name": "World"})
    Returns: "Hello World"
    """
    if not isinstance(text, str):
        return text
    
    def replacer(match):
        key = match.group(1).strip()
        # Support nested access: block_1.output.emails
        parts = key.split(".")
        value = variables
        for part in parts:
            if isinstance(value, dict) and part in value:
                value = value[part]
            else:
                return match.group(0)  # Return original if not found
        return str(value) if value is not None else ""
    
    return re.sub(r"\{\{(.+?)\}\}", replacer, text)


def resolve_value(value: Any, variables: dict) -> Any:
    """Resolve templates in any type (string, dict, list)."""
    if isinstance(value, str):
        return resolve_template(value, variables)
    elif isinstance(value, dict):
        return {k: resolve_value(v, variables) for k, v in value.items()}
    elif isinstance(value, list):
        return [resolve_value(item, variables) for item in value]
    return value


def safe_json_parse(text: str) -> Any:
    """Safely parse JSON, return original on failure."""
    try:
        return json.loads(text)
    except (json.JSONDecodeError, TypeError):
        return text


def evaluate_condition(condition: str, variables: dict) -> bool:
    """
    Evaluate a condition expression against variables.
    
    Supports:
    - Comparisons: {{x}} > 5, {{status}} == "active"
    - Boolean: {{enabled}}, !{{disabled}}
    - Truthiness
    """
    if not condition or not condition.strip():
        return True
    
    # Resolve all {{}} references first
    resolved = resolve_template(condition, variables)
    
    # Simple boolean evaluation
    resolved = resolved.strip().lower()
    if resolved in ("true", "1", "yes"):
        return True
    if resolved in ("false", "0", "no", ""):
        return False
    
    # Try Python expression evaluation (safe subset)
    try:
        # Only allow safe operations
        allowed_names = {"true": True, "false": False, "none": None, "null": None}
        return bool(eval(resolved, {"__builtins__": {}}, allowed_names))
    except Exception:
        return bool(resolved)


def measure_time(fn):
    """Decorator to measure execution time."""
    def wrapper(*args, **kwargs):
        start = time.time()
        result = fn(*args, **kwargs)
        elapsed = time.time() - start
        return result, elapsed
    return wrapper


async def ameasure_time(fn):
    """Async decorator to measure execution time."""
    async def wrapper(*args, **kwargs):
        start = time.time()
        result = await fn(*args, **kwargs)
        elapsed = time.time() - start
        return result, elapsed
    return wrapper
