"""Utility functions: uid generation, deep merge, etc."""

import random
import string


def uid() -> str:
    """Generate an 11-char random lowercase alphanumeric UID (NocoBase FlowModel format)."""
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=11))


def deep_merge(base: dict, patch: dict) -> dict:
    """Deep merge patch into base dict (in-place). Returns base for chaining."""
    for k, v in patch.items():
        if k in base and isinstance(base[k], dict) and isinstance(v, dict):
            deep_merge(base[k], v)
        else:
            base[k] = v
    return base
