"""Keyword-rank skills in catalog.json against a task description.

Usage: python rank_skills.py "任務描述" [top_n]
Crude scoring (name x4, zh x2, en x1, ascii words + CJK bigrams); the model
applies real judgment on this shortlist afterwards.
"""

import json
import re
import sys

from pick_paths import catalog_read_path

SRC_LABEL = {"active": "現役", "plugin": "plugin", "library": "封存庫"}


def terms_of(text):
    text = text.lower()
    words = re.findall(r"[a-z0-9][a-z0-9_.-]{1,}", text)
    cjk = re.findall(r"[一-鿿]", text)
    bigrams = ["".join(p) for p in zip(cjk, cjk[1:])]
    return set(words) | set(bigrams)


def main():
    if len(sys.argv) < 2 or not sys.argv[1].strip():
        print('用法: python rank_skills.py "任務描述" [top_n]')
        raise SystemExit(1)
    query = sys.argv[1]
    top_n = int(sys.argv[2]) if len(sys.argv) > 2 else 12
    catalog = catalog_read_path()
    if not catalog:
        print("catalog.json 不存在，先跑 build_catalog.py")
        raise SystemExit(1)
    cat = json.load(open(catalog, encoding="utf-8"))
    q = terms_of(query)
    scored = []
    for e in cat:
        if e.get("shadowed"):
            continue
        name = e["name"].lower()
        zh = e["zh"].lower()
        en = e["en"].lower()
        s = 0
        for t in q:
            if t in name:
                s += 4
            if zh and t in zh:
                s += 2
            if en and t in en:
                s += 1
        if s:
            scored.append((s, e))
    scored.sort(key=lambda x: (-x[0], x[1]["name"]))
    if not scored:
        print("(無關鍵字命中；改用 list_skills.py --groups 瀏覽)")
        return
    for s, e in scored[:top_n]:
        d = (e["zh"] or e["en"])[:70]
        print(f"{s:>3}  {e['name']} [{SRC_LABEL[e['source']]}] — {d}")


if __name__ == "__main__":
    main()
