"""Rebuild data/catalog.json for the pick skill.

Scans three roots:
  ~/.claude/skills          -> source "active"   (invoke via Skill tool)
  ~/.claude/plugins         -> source "plugin"   (invoke via Skill tool, plugin:name)
  ~/.claude/skills-library  -> source "library"  (NOT in system listing; load by
                                                  reading its SKILL.md and following it)
Merges Traditional Chinese one-liners from data/zh_desc.json.
"""

import glob
import json
import os
import re

from pick_paths import CLAUDE_HOME as HOME
from pick_paths import catalog_write_path, load_zh_map

OUT = catalog_write_path()

CATS = [
    ("語言/框架開發", r"^(java|kotlin|rust|go|golang|swift|swiftui|django|laravel|springboot|cpp|csharp|dart|flutter|perl|python|nodejs|nestjs|jpa|compose|android|dotnet|clickhouse|postgres|database|docker|deployment|api|backend|frontend|e2e|tdd|regex|evm|defi)"),
    ("baoyu 系列", r"^baoyu-"),
    ("產業/商業流程", r"^(carrier|customs|energy|inventory|production|quality|returns|logistics|finance|healthcare|hipaa|customer|lead|sales|investor|market|strategy|product|project|team|knowledge|enterprise|email|messages|google-workspace|unified|terminal|jira|github)"),
    ("agent/harness/loop", r"^(agent|ai-|autonomous|continuous|blueprint|council|cost-aware|eval|harness|loop|multi|orchestr|prompt|iterative|search-first|scope|token|verification|claude-|mcp-|build-mcp|codex|command-|configure|connections)"),
    ("設計/視覺/內容", r"^(algorithmic|brand|brutalist|canvas|dataviz|frontend-design|image|imagegen|inline|liquid|manim|minimalist|mobile|motion|nutrient|output|redesign|remotion|stitch|taste|theme|ui-|video|visa|humanizer|article|content|crosspost|social|seo|soft|dashboard|prototype)"),
    ("coolkid 專用", r"^(coolkid|threads|ig-|ga4|voice-|bcek|family|pick)"),
]


def categorize(name):
    for label, pat in CATS:
        if re.match(pat, name):
            return label
    return "其他"


def short_of(zh, en, limit=34):
    """First clause of the user-language description (zh preferred), for chip labels."""
    src = zh or en
    for sep in ("：", "。", "；", " — ", "—", " - ", ". ", "，"):
        head, _, _ = src.partition(sep)
        if 4 <= len(head) <= limit:
            return head
    cut = src[:limit]
    if len(src) > limit and re.search(r"[A-Za-z]", src[limit - 1: limit + 1] or ""):
        cut = cut.rsplit(" ", 1)[0]  # ASCII text: don't cut mid-word
    return cut


def fm(md_path):
    try:
        head = open(md_path, "r", encoding="utf-8", errors="replace").read(8000)
    except OSError:
        return None, ""
    m = re.search(r"^---\s*\n(.*?)\n---", head, re.S)
    body = m.group(1) if m else ""
    nm = re.search(r"^name:\s*(.+)$", body, re.M)
    de = re.search(r"^description:\s*(.+?)(?=\n\w+:|\Z)", body, re.M | re.S)
    name = nm.group(1).strip().strip("\"'") if nm else None
    desc = " ".join((de.group(1) if de else "").split())
    desc = re.sub(r"^(?:>-?|\|-?)\s*", "", desc).strip("\"'")  # YAML block scalar markers
    return name, desc


def plugin_prefix(path):
    m = re.search(r"plugins[\\/](?:cache|marketplaces)[\\/][^\\/]+[\\/]([^\\/]+)[\\/]skills[\\/]", path)
    return m.group(1) if m else None


zh_map = load_zh_map()

entries = {}
scans = [
    (os.path.join(HOME, "skills", "*", "SKILL.md"), "active"),
    (os.path.join(HOME, "plugins", "**", "SKILL.md"), "plugin"),
    (os.path.join(HOME, "skills-library", "*", "SKILL.md"), "library"),
]
for pattern, source in scans:
    for p in glob.glob(pattern, recursive=True):
        name, desc = fm(p)
        name = name or os.path.basename(os.path.dirname(p))
        key = f"{source}:{name}"
        if key in entries:
            continue
        if source == "plugin":
            pref = plugin_prefix(p)
            invoke = f"{pref}:{name}" if pref else name
        elif source == "active":
            invoke = name
        else:
            invoke = None
        zh = zh_map.get(name, "")
        entries[key] = {
            "name": name,
            "cat": categorize(name),
            "source": source,
            "invoke": invoke,
            "path": p,
            "zh": zh,
            "en": desc[:160],
            "short": short_of(zh, desc),
        }

# active/plugin copy wins over a stale library copy of the same name
lib_dupes = [k for k in entries if k.startswith("library:") and (
    "active:" + k.split(":", 1)[1] in entries or "plugin:" + k.split(":", 1)[1] in entries)]
for k in lib_dupes:
    entries[k]["shadowed"] = True

cat = sorted(entries.values(), key=lambda e: (e["source"], e["cat"], e["name"]))
json.dump(cat, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

n = {"active": 0, "plugin": 0, "library": 0}
for e in cat:
    n[e["source"]] += 1
zh_hit = sum(1 for e in cat if e["zh"])
print(f"catalog.json 已更新: active={n['active']} plugin={n['plugin']} library={n['library']}")
print(f"含繁中說明: {zh_hit}/{len(cat)}  shadowed: {len(lib_dupes)}")
