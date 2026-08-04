"""Shared path resolution for pick scripts.

Works in three install modes:
- personal skill dir (~/.claude/skills/pick)         -> data lives in <skill>/data
- git clone copied into ~/.claude/skills             -> same
- plugin install (marketplace cache, may be wiped     -> generated catalog falls back
  or read-only on update)                                to ~/.claude/pick-data

PICK_DATA_DIR env var overrides everything.
"""

import json
import os

SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOCAL_DATA = os.path.join(SKILL_DIR, "data")
FALLBACK_DATA = os.path.join(os.path.expanduser("~"), ".claude", "pick-data")
CLAUDE_HOME = os.path.join(os.path.expanduser("~"), ".claude")


def _override():
    return os.environ.get("PICK_DATA_DIR")


def catalog_write_path():
    """Where build_catalog.py should write catalog.json."""
    if _override():
        os.makedirs(_override(), exist_ok=True)
        return os.path.join(_override(), "catalog.json")
    try:
        os.makedirs(LOCAL_DATA, exist_ok=True)
        probe = os.path.join(LOCAL_DATA, ".write_probe")
        with open(probe, "w", encoding="utf-8") as fh:
            fh.write("")
        os.remove(probe)
        return os.path.join(LOCAL_DATA, "catalog.json")
    except OSError:
        os.makedirs(FALLBACK_DATA, exist_ok=True)
        return os.path.join(FALLBACK_DATA, "catalog.json")


def catalog_read_path():
    """First existing catalog.json among override -> local -> fallback."""
    candidates = []
    if _override():
        candidates.append(os.path.join(_override(), "catalog.json"))
    candidates.append(os.path.join(LOCAL_DATA, "catalog.json"))
    candidates.append(os.path.join(FALLBACK_DATA, "catalog.json"))
    for p in candidates:
        if os.path.isfile(p):
            return p
    return None


def load_zh_map():
    """Merge shipped zh_desc.json with the user's override layer (override wins)."""
    merged = {}
    for p in (os.path.join(LOCAL_DATA, "zh_desc.json"),
              os.path.join(FALLBACK_DATA, "zh_desc.json")):
        if os.path.isfile(p):
            try:
                merged.update(json.load(open(p, encoding="utf-8")))
            except (OSError, ValueError):
                pass
    return merged
