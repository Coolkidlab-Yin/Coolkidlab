#!/usr/bin/env python3
"""把 marketplace(本 repo)的 plugin 內容單向同步到 coolkid-oss 的 9 個獨立公開 repo。

單一事實來源:coolkidlab-plugins(本 repo)。獨立 repo 是鏡像,不要直接改
(README.md / .gitignore 除外,那兩個是 repo 自管的)。
裁決紀錄:2026-08-04 本人裁定方案 A(marketplace 為準+腳本同步)。

用法:
    python scripts/sync_to_oss.py            # dry-run:列出會動哪些檔,不寫入
    python scripts/sync_to_oss.py --check    # 給 pre-push hook 用:有漂移就 exit 1
    python scripts/sync_to_oss.py --apply    # 實際寫入 oss 工作樹,不 commit
    python scripts/sync_to_oss.py --push     # 寫入+逐 repo commit+push
    python scripts/sync_to_oss.py --repo ig-bot-builder --push   # 只同步一個

exit code:0=無事/成功 1=有漂移(--check)或 git 失敗 2=掃到疑似 secret
"""

import argparse
import re
import subprocess
import sys
from pathlib import Path

MP_ROOT = Path(__file__).resolve().parent.parent
OSS_ROOT = MP_ROOT.parent / "coolkid-oss"

# layout 說明:
#   skills = oss repo 與 plugin 同構(skills/ 整棵鏡像)
#   flat   = 腳本型 repo,對外深連結指著根目錄的 .py,不搬家:
#            skills/<n>/scripts/* -> 根目錄, examples/ -> examples/, SKILL.md -> SKILL.md
#   pet    = windows-desktop-pet-builder 沿用它獨立發布時的佈局:
#            skills/<n>/ -> skill/<n>/(單數), docs/ 與 prompts/ 整棵鏡像
SYNC_MAP = {
    "article-overlap-checker": "flat",
    "brand-profile-lockdown": "skills",
    "claude-code-checkpoint-system": "skills",
    "competitor-content-map": "flat",
    "ga4-chatgpt-referral": "skills",
    "ig-bot-builder": "skills",
    "line-bot-builder": "skills",
    "skill-picker": "skills",
    "threads-bot-builder": "skills",
    "voice-profile-extraction": "skills",
    "windows-desktop-pet-builder": "pet",
}

EXCLUDE_NAMES = {"__pycache__"}
EXCLUDE_SUFFIXES = {".pyc"}
# oss 側永不刪除/覆蓋來源以外的這些檔
OSS_OWNED = {"README.md", ".gitignore", ".gitattributes"}

# 高信心 secret 樣式:命中就硬擋(exit 2)
SECRET_PATTERNS = [
    (re.compile(r"gh[pousr]_[A-Za-z0-9]{20,}"), "GitHub token"),
    (re.compile(r"github_pat_[A-Za-z0-9_]{20,}"), "GitHub fine-grained PAT"),
    (re.compile(r"\bsk-[A-Za-z0-9_-]{24,}"), "API key (sk-)"),
    (re.compile(r"\bAKIA[0-9A-Z]{16}\b"), "AWS access key"),
    (re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"), "private key"),
    (re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}"), "Slack token"),
    (re.compile(r"\bEAA[A-Za-z0-9]{30,}"), "Meta Graph token"),
    (re.compile(r"\bAIza[0-9A-Za-z_-]{35}\b"), "Google API key"),
    (re.compile(r"eyJhbGciOi[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{10,}"), "JWT"),
]
# 低信心樣式:只警告,不擋(教學文件常有佔位範例)
WARN_PATTERNS = [
    (re.compile(r"C:\\+Users\\+try19|/Users/try19|/home/\w+/"), "本機路徑外洩"),
]


def norm(data: bytes) -> bytes:
    """文字檔 CRLF→LF 正規化;比對與寫入都用這個,免得 EOL 造成假漂移"""
    if b"\0" in data:
        return data
    return data.replace(b"\r\n", b"\n")


def rel_files(root: Path):
    for p in sorted(root.rglob("*")):
        if not p.is_file():
            continue
        if any(part in EXCLUDE_NAMES for part in p.parts):
            continue
        if p.suffix in EXCLUDE_SUFFIXES:
            continue
        yield p


def desired_map(name: str, layout: str) -> dict:
    """回傳 {oss 相對路徑: 來源絕對路徑}"""
    plug = MP_ROOT / "plugins" / name
    inner = plug / "skills" / name
    out = {}
    if layout == "skills":
        for src in rel_files(plug / "skills"):
            out[str(Path("skills") / src.relative_to(plug / "skills"))] = src
    elif layout == "pet":
        for src in rel_files(plug / "skills"):
            out[str(Path("skill") / src.relative_to(plug / "skills"))] = src
        for extra in ("docs", "prompts"):
            if (plug / extra).is_dir():
                for src in rel_files(plug / extra):
                    out[str(Path(extra) / src.relative_to(plug / extra))] = src
    else:  # flat
        skill_md = inner / "SKILL.md"
        if skill_md.is_file():
            out["SKILL.md"] = skill_md
        scripts = inner / "scripts"
        if scripts.is_dir():
            for src in rel_files(scripts):
                out[str(src.relative_to(scripts))] = src
        examples = inner / "examples"
        if examples.is_dir():
            for src in rel_files(examples):
                out[str(Path("examples") / src.relative_to(examples))] = src
    lic = plug / "LICENSE"
    if lic.is_file():
        out["LICENSE"] = lic
    # README 目前由 oss repo 自管;哪天搬進 plugin 目錄,這裡就自動接手
    readme = plug / "README.md"
    if readme.is_file():
        out["README.md"] = readme
    return out


def managed_existing(name: str, layout: str, oss: Path):
    """oss 側屬於同步範圍、因此允許被刪的既有檔"""
    got = []
    if layout == "skills":
        roots = [oss / "skills"]
    elif layout == "pet":
        roots = [oss / "skill", oss / "docs", oss / "prompts"]
    else:
        roots = [oss / "examples"]
        got += [p for p in oss.glob("*.py") if p.is_file()]
        if (oss / "SKILL.md").is_file():
            got.append(oss / "SKILL.md")
    for r in roots:
        if r.is_dir():
            got += list(rel_files(r))
    return [p for p in got if p.name not in OSS_OWNED]


def scan_secrets(files: dict):
    """files: {label: Path}。回傳 (hard_hits, warns)"""
    hard, warns = [], []
    for label, path in files.items():
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError as e:
            hard.append((label, f"讀檔失敗: {e}"))
            continue
        for pat, what in SECRET_PATTERNS:
            m = pat.search(text)
            if m:
                hard.append((label, f"{what}: {m.group(0)[:12]}…"))
        for pat, what in WARN_PATTERNS:
            if pat.search(text):
                warns.append((label, what))
    return hard, warns


def git(repo: Path, *args, check=True):
    r = subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    if check and r.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} 失敗於 {repo.name}:\n{r.stderr.strip()}")
    return r


def diff_repo(name: str, layout: str):
    """回傳 (changed, deleted, missing_repo)"""
    oss = OSS_ROOT / name
    if not oss.is_dir():
        return [], [], True
    want = desired_map(name, layout)
    changed = []
    for rel, src in want.items():
        dst = oss / rel
        if not dst.is_file() or norm(dst.read_bytes()) != norm(src.read_bytes()):
            changed.append(rel)
    want_abs = {str((oss / rel).resolve()) for rel in want}
    deleted = [
        str(p.relative_to(oss))
        for p in managed_existing(name, layout, oss)
        if str(p.resolve()) not in want_abs
    ]
    return changed, deleted, False


def main():
    if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")

    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    mode = ap.add_mutually_exclusive_group()
    mode.add_argument("--check", action="store_true", help="有漂移就 exit 1(hook 用)")
    mode.add_argument("--apply", action="store_true", help="寫入 oss 工作樹,不 commit")
    mode.add_argument("--push", action="store_true", help="寫入+commit+push")
    ap.add_argument("--repo", help="只處理這一個(oss repo 名)")
    ap.add_argument("--trailer", help="附加在 commit message 結尾的一行(選用)")
    args = ap.parse_args()

    targets = SYNC_MAP
    if args.repo:
        if args.repo not in SYNC_MAP:
            print(f"✗ 不認得 {args.repo};可選:{', '.join(SYNC_MAP)}")
            return 1
        targets = {args.repo: SYNC_MAP[args.repo]}

    head = git(MP_ROOT, "log", "-1", "--format=%h %s").stdout.strip()
    mp_hash, mp_subject = head.split(" ", 1)

    drift, failures = {}, []
    for name, layout in targets.items():
        changed, deleted, missing = diff_repo(name, layout)
        if missing:
            failures.append(f"{name}: 本機找不到 {OSS_ROOT / name}(先 clone)")
            continue
        # --check/--push 同時把「同步了但沒 commit/沒 push」視為未完成
        # (例如前一輪寫入成功但 commit 失敗;--push 會接手把它收尾)
        pending = ""
        if (args.check or args.push) and not changed and not deleted:
            oss = OSS_ROOT / name
            if git(oss, "status", "--porcelain").stdout.strip():
                pending = "工作樹有未 commit 變更"
            else:
                r = git(oss, "rev-list", "--count", "@{u}..HEAD", check=False)
                if r.returncode == 0 and r.stdout.strip() not in ("", "0"):
                    pending = f"{r.stdout.strip()} 個 commit 未 push"
        if changed or deleted or pending:
            drift[name] = (changed, deleted, pending)

    if failures:
        print("✗ 前置失敗:")
        for f in failures:
            print(f"  - {f}")
        return 1

    if not drift:
        print(f"✓ {len(targets)} 組全部與 marketplace {mp_hash} 一致,無事可做")
        return 0

    if args.check:
        print(f"✗ {len(drift)} 個 oss 副本與 marketplace 有漂移/未推:")
        for name, (c, d, p) in drift.items():
            detail = p or f"{len(c)} 改 {len(d)} 刪"
            print(f"  - {name}: {detail}")
        print("  跑 python scripts/sync_to_oss.py --push 收斂後再推。")
        return 1

    # dry-run / apply / push 共用的變更清單
    for name, (changed, deleted, _) in drift.items():
        print(f"── {name}")
        for rel in changed:
            print(f"   寫入 {rel}")
        for rel in deleted:
            print(f"   刪除 {rel}")

    if not (args.apply or args.push):
        print("\n(dry-run,未寫入;--apply 寫入,--push 寫入+commit+push)")
        return 0

    # secrets 掃描:掃所有即將寫出去的檔(兩邊都是公開 repo)
    to_scan = {}
    for name, (changed, _d, _p) in drift.items():
        want = desired_map(name, SYNC_MAP[name])
        for rel in changed:
            to_scan[f"{name}/{rel}"] = want[rel]
    hard, warns = scan_secrets(to_scan)
    for label, what in warns:
        print(f"⚠ {label}: {what}(請人工確認)")
    if hard:
        print("✗ 掃到疑似 secret,中止,一個都沒寫:")
        for label, what in hard:
            print(f"  - {label}: {what}")
        return 2

    ok = True
    for name, (changed, deleted, _p) in drift.items():
        oss = OSS_ROOT / name
        want = desired_map(name, SYNC_MAP[name])
        try:
            for rel in changed:
                dst = oss / rel
                dst.parent.mkdir(parents=True, exist_ok=True)
                dst.write_bytes(norm(want[rel].read_bytes()))
            for rel in deleted:
                (oss / rel).unlink()
            # 清掉因刪檔而空掉的目錄
            for d in sorted((p for p in oss.rglob("*") if p.is_dir()), reverse=True):
                if ".git" not in d.parts and not any(d.iterdir()):
                    d.rmdir()
            if args.push:
                git(oss, "add", "-A")
                if git(oss, "status", "--porcelain").stdout.strip():
                    msg = f"sync: 對齊 marketplace {mp_hash} ({mp_subject})"
                    if args.trailer:
                        msg += f"\n\n{args.trailer}"
                    git(oss, "commit", "-m", msg)
                git(oss, "push")
                print(f"✓ {name} 已同步並 push")
            else:
                print(f"✓ {name} 已寫入(未 commit)")
        except (RuntimeError, OSError) as e:
            ok = False
            print(f"✗ {name}: {e}")

    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
