"""Compact listings from catalog.json (keep context small — names only by default).

Usage:
  python list_skills.py --groups          grouped names, comma-separated
  python list_skills.py --cat <類別名>     names + zh one-liner for one category
  python list_skills.py --json            machine-readable {source: {cat: [names]}}
"""

import collections
import json
import sys

from pick_paths import catalog_read_path

SRC_LABEL = {"active": "現役", "plugin": "plugin", "library": "封存庫"}


def load():
    p = catalog_read_path()
    if not p:
        print("catalog.json 不存在，先跑 build_catalog.py")
        raise SystemExit(1)
    return json.load(open(p, encoding="utf-8"))


def main():
    cat = load()
    args = sys.argv[1:]
    if "--json" in args:
        out = collections.defaultdict(lambda: collections.defaultdict(list))
        for e in cat:
            if e.get("shadowed"):
                continue
            out[e["source"]][e["cat"]].append([e["name"], e.get("short", "")])
        print(json.dumps(out, ensure_ascii=False))
        return
    if "--cat" in args:
        want = args[args.index("--cat") + 1]
        for e in cat:
            if e["cat"] == want and not e.get("shadowed"):
                d = e["zh"] or e["en"][:70]
                print(f"[{SRC_LABEL[e['source']]}] {e['name']} — {d}")
        return
    groups = collections.defaultdict(list)
    for e in cat:
        if e.get("shadowed"):
            continue
        groups[(e["source"], e["cat"])].append(e["name"])
    order = {"active": 0, "plugin": 1, "library": 2}
    for (src, c), names in sorted(groups.items(), key=lambda x: (order[x[0][0]], x[0][1])):
        print(f"== {SRC_LABEL[src]}/{c} ({len(names)}) ==")
        print(", ".join(sorted(names)))


if __name__ == "__main__":
    main()
