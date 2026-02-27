"""Utility functions: uid generation, deep merge, etc."""

import json
import random
import string


def uid() -> str:
    """Generate an 11-char random lowercase alphanumeric UID (NocoBase FlowModel format)."""
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=11))


def safe_json(val):
    """Parse JSON string, or return as-is if already deserialized.

    FastMCP's pre_parse_json() auto-deserializes Optional[str] params
    that look like JSON. This helper handles both cases safely.
    """
    if val is None:
        return None
    if isinstance(val, (dict, list)):
        return val  # already deserialized by FastMCP
    if isinstance(val, str):
        return json.loads(val)
    return val


def deep_merge(base: dict, patch: dict) -> dict:
    """Deep merge patch into base dict (in-place). Returns base for chaining."""
    for k, v in patch.items():
        if k in base and isinstance(base[k], dict) and isinstance(v, dict):
            deep_merge(base[k], v)
        else:
            base[k] = v
    return base
