"""Load + deep-merge one or more YAML/JSON data stores.

Multiple sources are read in order and merged: scalars and dicts from later
files override earlier ones; lists of records (``projects``, ``personnel``,
``past_performance``, ``categories``) are concatenated and de-duplicated by
``id`` (later wins). This lets a stable ``firm.yaml`` coexist with a per-year
``opportunity_FY2027.yaml`` (one possibly living in OneDrive).
"""

from __future__ import annotations

import json
from pathlib import Path

import yaml

# Lists merged by record id rather than replaced wholesale.
LIST_KEYS = {"categories", "personnel", "projects", "past_performance"}


def _load_one(path: Path) -> dict:
    text = Path(path).read_text(encoding="utf-8")
    if str(path).lower().endswith(".json"):
        return json.loads(text) or {}
    return yaml.safe_load(text) or {}


def _merge_lists(a: list, b: list) -> list:
    out = list(a)
    by_id = {r.get("id"): i for i, r in enumerate(out) if isinstance(r, dict) and "id" in r}
    for rec in b:
        rid = rec.get("id") if isinstance(rec, dict) else None
        if rid is not None and rid in by_id:
            out[by_id[rid]] = rec       # later wins
        else:
            out.append(rec)
            if rid is not None:
                by_id[rid] = len(out) - 1
    return out


def _deep_merge(base: dict, override: dict) -> dict:
    out = dict(base)
    for key, val in (override or {}).items():
        if key in LIST_KEYS and isinstance(val, list) and isinstance(out.get(key), list):
            out[key] = _merge_lists(out[key], val)
        elif isinstance(val, dict) and isinstance(out.get(key), dict):
            out[key] = _deep_merge(out[key], val)
        else:
            out[key] = val
    return out


def load(paths) -> dict:
    """Load and merge the given store paths (skipping any that don't exist)."""
    store: dict = {}
    for p in paths:
        if Path(p).exists():
            store = _deep_merge(store, _load_one(p))
    return store
