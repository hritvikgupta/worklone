"""
Utility functions for the SDK.
"""

import uuid
import re
import json
import time
from typing import Any
from datetime import datetime


def generate_id(prefix: str = "") -> str:
    uid = uuid.uuid4().hex[:12]
    if prefix:
        return f"{prefix}_{uid}"
    return uid


def now_iso() -> str:
    return datetime.now().isoformat()


def resolve_template(text: str, variables: dict) -> str:
    if not isinstance(text, str):
        return text

    def replacer(match):
        key = match.group(1).strip()
        parts = key.split(".")
        value = variables
        for part in parts:
            if isinstance(value, dict) and part in value:
                value = value[part]
            else:
                return match.group(0)
        return str(value) if value is not None else ""

    return re.sub(r"\{\{(.+?)\}\}", replacer, text)


def resolve_value(value: Any, variables: dict) -> Any:
    if isinstance(value, str):
        return resolve_template(value, variables)
    elif isinstance(value, dict):
        return {k: resolve_value(v, variables) for k, v in value.items()}
    elif isinstance(value, list):
        return [resolve_value(item, variables) for item in value]
    return value


def safe_json_parse(text: str) -> Any:
    try:
        return json.loads(text)
    except (json.JSONDecodeError, TypeError):
        return text


def evaluate_condition(condition: str, variables: dict) -> bool:
    if not condition or not condition.strip():
        return True
    resolved = resolve_template(condition, variables)
    resolved = resolved.strip().lower()
    if resolved in ("true", "1", "yes"):
        return True
    if resolved in ("false", "0", "no", ""):
        return False
    try:
        allowed_names = {"true": True, "false": False, "none": None, "null": None}
        return bool(eval(resolved, {"__builtins__": {}}, allowed_names))
    except Exception:
        return bool(resolved)


def measure_time(fn):
    def wrapper(*args, **kwargs):
        start = time.time()
        result = fn(*args, **kwargs)
        elapsed = time.time() - start
        return result, elapsed
    return wrapper


async def ameasure_time(fn):
    async def wrapper(*args, **kwargs):
        start = time.time()
        result = await fn(*args, **kwargs)
        elapsed = time.time() - start
        return result, elapsed
    return wrapper
