"""Competitor sitemap battle-map builder.

把對手公開的 sitemap 當成「他主動攤開的內容版圖」來扒，產出一張作戰地圖：
各對手主題群、跨站覆蓋矩陣、你的空白候選、lastmod 新鮮度訊號，外加一段
「貼給 AI 做語意分群」的 prompt block。

設計分工（這支腳本的核心原則 — 別讓 AI 編數字）:
    確定性的事 → 腳本做：抓 sitemap.xml / robots.txt / sitemap index、解 .xml.gz、
                  去重、依 URL 路徑粗分桶、算 lastmod 新鮮度、跨站比對找空白。
    語意判斷    → 交給 AI（貼 block 進 Claude/ChatGPT；或 --cc 走訂閱；或 --ai 走 API）。
    搜尋量/競爭度 → 兩邊都不碰。sitemap 裡根本沒這資料，AI 一報就是幽靈數字。
                   必須回 Google Keyword Planner / Ahrefs 免費工具驗證。

來源招數來自 @darkseoking（akseolabs-seo/seo-coach）。三個關卡會印在輸出裡：
    1. AI 報的搜尋量一個字都別信，去 Keyword Planner / Ahrefs 驗證。
    2. lastmod 全站同日 = sitemap generator 自動填的假新鮮，別被騙。
    3. 對手掛 100 篇 blog 不代表 100 篇有排名，數量多別焦慮。

Usage:
    python scripts/competitor_sitemap_map.py --vs rival1.com rival2.com rival3.com
    python scripts/competitor_sitemap_map.py --you www.your-site.com --vs rival1.com rival2.com
    python scripts/competitor_sitemap_map.py --config scripts/competitors.txt
    python scripts/competitor_sitemap_map.py --vs rival1.com --cc   # 訂閱跑分群，免 API key（推薦）
    python scripts/competitor_sitemap_map.py --vs rival1.com --ai   # 改走 API，需 ANTHROPIC_API_KEY

--config 檔：一行一個域名，# 開頭為註解，行尾加 ` you` 標記自己的站。

Exit codes:
    0 — 至少一個站抓到 URL，地圖已產出
    1 — 全部站都抓不到 sitemap（網路 / robots 阻擋 / 域名錯）
    2 — 參數錯誤
"""
from __future__ import annotations

import argparse
import gzip
import json
import os
import re
import shutil
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Force UTF-8 stdout — Windows default cp950 chokes on ✓ / ⚠ / Chinese chars.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "outputs" / "sitemap-maps"

USER_AGENT = "Mozilla/5.0 (compatible; competitor-sitemap-map/1.0; +https://github.com/WEIYIN-11/coolkid-plugins)"
TIMEOUT = 20  # seconds per request
MAX_SITEMAPS_PER_DOMAIN = 50  # safety cap on sitemap-index fan-out
MAX_URLS_PER_DOMAIN = 20000  # safety cap on URL collection

# 兩字母語系前綴（/en/ /zh/ /ja/…）+ 常見地區碼 → 分桶時跳過，取下一段才是真主題。
LOCALE_SEG = re.compile(r"^([a-z]{2}([-_][a-z]{2,4})?|zh-(hans|hant|tw|cn|hk))$", re.I)

TW = timezone(timedelta(hours=8))


# ─────────────────────────────────────────────────────────────
# Data containers
# ─────────────────────────────────────────────────────────────
@dataclass
class SiteData:
    domain: str
    is_you: bool = False
    urls: list[tuple[str, str | None]] = field(default_factory=list)  # (loc, lastmod)
    sitemaps_used: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    @property
    def buckets(self) -> Counter:
        c: Counter = Counter()
        for loc, _ in self.urls:
            c[bucket_of(loc)] += 1
        return c


# ─────────────────────────────────────────────────────────────
# Fetch + sitemap discovery
# ─────────────────────────────────────────────────────────────
def fetch(url: str) -> bytes | None:
    """GET url, transparently gunzip .gz / gzip-encoded bodies. None on any failure."""
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            raw = resp.read()
            enc = (resp.headers.get("Content-Encoding") or "").lower()
        if url.endswith(".gz") or enc == "gzip" or raw[:2] == b"\x1f\x8b":
            try:
                raw = gzip.decompress(raw)
            except OSError:
                pass
        return raw
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError, ValueError):
        return None


def normalize_domain(d: str) -> str:
    d = d.strip()
    if not d:
        return ""
    if not re.match(r"^https?://", d):
        d = "https://" + d
    parsed = urllib.parse.urlparse(d)
    return f"{parsed.scheme}://{parsed.netloc}"


def discover_sitemaps(base: str) -> tuple[list[str], list[str]]:
    """Return (sitemap_urls, notes). Try /sitemap.xml, fall back to robots.txt."""
    notes: list[str] = []
    candidate = base + "/sitemap.xml"
    if fetch(candidate) is not None:
        notes.append("/sitemap.xml 直接打得開")
        found = [candidate]
    else:
        found = []
        notes.append("/sitemap.xml 打不開，翻 robots.txt")

    robots = fetch(base + "/robots.txt")
    if robots:
        for line in robots.decode("utf-8", "ignore").splitlines():
            m = re.match(r"\s*sitemap\s*:\s*(\S+)", line, re.I)
            if m:
                sm = m.group(1).strip()
                if sm not in found:
                    found.append(sm)
        if any("sitemap:" in line.lower() for line in robots.decode("utf-8", "ignore").splitlines()):
            notes.append("robots.txt 末尾有列 Sitemap")
    elif not found:
        notes.append("robots.txt 也抓不到")

    return found, notes


def parse_sitemap(xml_bytes: bytes) -> tuple[bool, list[tuple[str, str | None]]]:
    """Return (is_index, entries). entries = [(loc, lastmod)]. Namespace-agnostic."""
    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError:
        return False, []

    def local(tag: str) -> str:
        return tag.rsplit("}", 1)[-1].lower()

    is_index = local(root.tag) == "sitemapindex"
    entries: list[tuple[str, str | None]] = []
    for child in root:
        loc = lastmod = None
        for sub in child:
            name = local(sub.tag)
            if name == "loc" and sub.text:
                loc = sub.text.strip()
            elif name == "lastmod" and sub.text:
                lastmod = sub.text.strip()
        if loc:
            entries.append((loc, lastmod))
    return is_index, entries


def crawl_domain(domain: str, is_you: bool) -> SiteData:
    base = normalize_domain(domain)
    data = SiteData(domain=base, is_you=is_you)
    if not base:
        data.errors.append("空域名")
        return data

    queue, notes = discover_sitemaps(base)
    data.errors.extend(notes)
    if not queue:
        return data

    seen_sitemaps: set[str] = set()
    seen_locs: set[str] = set()
    while queue and len(data.sitemaps_used) < MAX_SITEMAPS_PER_DOMAIN:
        sm = queue.pop(0)
        if sm in seen_sitemaps:
            continue
        seen_sitemaps.add(sm)
        body = fetch(sm)
        if body is None:
            data.errors.append(f"抓不到 {sm}")
            continue
        is_index, entries = parse_sitemap(body)
        data.sitemaps_used.append(sm)
        if is_index:
            for loc, _ in entries:
                if loc not in seen_sitemaps:
                    queue.append(loc)
        else:
            for loc, lastmod in entries:
                if loc in seen_locs:
                    continue
                seen_locs.add(loc)
                data.urls.append((loc, lastmod))
                if len(data.urls) >= MAX_URLS_PER_DOMAIN:
                    data.errors.append(f"URL 超過 {MAX_URLS_PER_DOMAIN} 上限，截斷")
                    return data
    return data


# ─────────────────────────────────────────────────────────────
# Classification + analysis (deterministic only)
# ─────────────────────────────────────────────────────────────
def bucket_of(loc: str) -> str:
    """粗分桶：取第一個有意義的路徑段（跳過語系前綴）。語意分群交給 AI。"""
    path = urllib.parse.urlparse(loc).path.strip("/")
    if not path:
        return "(首頁/root)"
    segs = path.split("/")
    if LOCALE_SEG.match(segs[0]) and len(segs) > 1:
        segs = segs[1:]
    seg = segs[0]
    if len(segs) == 1:  # 單層 → 多半是文章/落地頁本體，不是分類
        return "(頂層頁)"
    return seg or "(頂層頁)"


def parse_date(s: str | None) -> datetime | None:
    if not s:
        return None
    s = s.strip()
    for fmt in ("%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
        try:
            d = datetime.strptime(s[:19] if "T" in s and len(s) >= 19 else s, fmt.replace("%z", ""))
            return d.replace(tzinfo=TW) if d.tzinfo is None else d
        except ValueError:
            continue
    # 帶時區 offset 的 ISO（+08:00）
    try:
        return datetime.fromisoformat(s)
    except ValueError:
        return None


def freshness_signal(data: SiteData) -> list[str]:
    """lastmod 分析。回傳人話訊號清單。"""
    out: list[str] = []
    dates = [parse_date(lm) for _, lm in data.urls]
    dates = [d for d in dates if d]
    total = len(data.urls)
    if not dates:
        out.append("sitemap 沒帶 lastmod，看不出更新節奏")
        return out

    distinct = {d.date() for d in dates}
    if len(distinct) == 1 and len(dates) >= 10:
        out.append(
            f"⚠ 全站 {len(dates)} 個 lastmod 同一天（{next(iter(distinct))}）"
            "→ 多半是 generator 自動填的假新鮮，別被騙"
        )
        return out

    now = datetime.now(TW)
    recent30 = sum(1 for d in dates if (now - d).days <= 30)
    recent90 = sum(1 for d in dates if (now - d).days <= 90)
    if recent30:
        out.append(f"近 30 天有 {recent30} 頁更新（佔抓到日期的 {recent30}/{len(dates)}）")
    if recent90:
        out.append(f"近 90 天有 {recent90} 頁更新")

    # 哪個桶最近密集更新 → 對手可能正主打那塊
    bucket_recent: Counter = Counter()
    for (loc, lm) in data.urls:
        d = parse_date(lm)
        if d and (now - d).days <= 60:
            bucket_recent[bucket_of(loc)] += 1
    hot = [f"{b}（{n}）" for b, n in bucket_recent.most_common(3) if n >= 3]
    if hot:
        out.append("近 60 天密集更新的主題（對手可能正重點打）：" + "、".join(hot))
    out.append(f"（基準：抓到 {total} 個 URL，其中 {len(dates)} 個帶 lastmod）")
    return out


def build_gap_view(sites: list[SiteData]) -> dict:
    """跨站覆蓋矩陣 + 空白候選。純計數，誠實標註限制。"""
    you = next((s for s in sites if s.is_you), None)
    rivals = [s for s in sites if not s.is_you]

    all_buckets: set[str] = set()
    for s in sites:
        all_buckets.update(s.buckets.keys())

    matrix: dict[str, dict[str, int]] = {}
    for b in sorted(all_buckets):
        matrix[b] = {s.domain: s.buckets.get(b, 0) for s in sites}

    you_buckets = set(you.buckets.keys()) if you else set()
    rival_union: Counter = Counter()
    for s in rivals:
        rival_union.update(s.buckets)

    # 對手有、你沒有
    you_missing = []
    if you:
        for b, total in rival_union.most_common():
            if b not in you_buckets and b not in ("(首頁/root)", "(頂層頁)"):
                holders = [s.domain for s in rivals if s.buckets.get(b)]
                you_missing.append({"bucket": b, "rival_total": total, "held_by": holders})

    # 全行業薄弱：某桶在「有它的站」裡計數都很低（沒人寫透）
    thin = []
    for b in all_buckets:
        if b in ("(首頁/root)", "(頂層頁)"):
            continue
        counts = [s.buckets[b] for s in sites if s.buckets.get(b)]
        if counts and max(counts) <= 3 and len(counts) >= 1:
            thin.append({"bucket": b, "max_count": max(counts), "present_in": len(counts)})

    # 對手主導：某站在某桶數量明顯壓過其他站
    dominated = []
    for b in all_buckets:
        if b in ("(首頁/root)", "(頂層頁)"):
            continue
        per = sorted(((s.buckets.get(b, 0), s.domain) for s in sites), reverse=True)
        if per and per[0][0] >= 5 and (len(per) == 1 or per[0][0] >= 2 * max(1, per[1][0])):
            dominated.append({"bucket": b, "leader": per[0][1], "count": per[0][0]})

    return {
        "matrix": matrix,
        "you_missing": you_missing[:25],
        "thin_everywhere": sorted(thin, key=lambda x: x["max_count"])[:25],
        "dominated": sorted(dominated, key=lambda x: -x["count"])[:25],
        "has_you": you is not None,
    }


# ─────────────────────────────────────────────────────────────
# Rendering
# ─────────────────────────────────────────────────────────────
WARN_BLOCK = """\
> ## ⚠ 三個 sitemap 騙不了你、也告訴不了你的關卡（別跳過）
>
> 1. **搜尋量是幽靈數字**：sitemap 裡沒有搜尋量、沒有競爭度。任何 AI（含我）
>    排出來的「低競爭高購買意向」優先序都是腦補，**當草稿、別當聖旨**。下面
>    篩出來的空白主題，逐一丟進 **Google Keyword Planner**（免費，可能要先開
>    Ads 帳戶）或 **Ahrefs 免費關鍵字工具** 驗證真有人搜，再決定寫不寫。
> 2. **lastmod 全站同日 = 假新鮮**：若新鮮度訊號顯示全站 lastmod 同一天，
>    那是 generator 自動填的，不代表對手在動，別被騙。
> 3. **100 篇 blog ≠ 100 篇有排名**：對手 sitemap 掛幾百頁，很可能九成躺在
>    第 2、3 頁裝死。你扒來的是版圖跟方向，不是內容本身。照抄只能排在它屁股
>    後面；只有寫得更深、塞滿你的實測數據，才爬得上去。
"""


def render_markdown(sites: list[SiteData], gap: dict, ts: str) -> str:
    L: list[str] = []
    L.append("# 對手 Sitemap 作戰地圖")
    L.append("")
    L.append(f"> 產出時間：{ts}　|　來源招數：@darkseoking sitemap 扒對手法")
    L.append("")
    doms = "、".join(
        f"`{s.domain}`{'（你）' if s.is_you else ''}" for s in sites
    )
    L.append(f"**比對站台**：{doms}")
    L.append("")
    L.append(WARN_BLOCK)
    L.append("")

    # 1. 抓取結果
    L.append("## 1. 抓取結果")
    L.append("")
    L.append("| 站台 | 抓到 URL | 用到的 sitemap | 備註 |")
    L.append("|------|---------:|---------------:|------|")
    for s in sites:
        note = "; ".join(s.errors[:2]) if s.errors else "ok"
        tag = "（你）" if s.is_you else ""
        L.append(f"| `{s.domain}`{tag} | {len(s.urls)} | {len(s.sitemaps_used)} | {note} |")
    L.append("")

    # 2. 各站主題版圖
    L.append("## 2. 各站主題版圖（依 URL 路徑粗分桶 — 語意分群見第 7 段）")
    L.append("")
    for s in sites:
        if not s.urls:
            continue
        tag = "（你）" if s.is_you else ""
        top = s.buckets.most_common(12)
        line = "、".join(f"{b} `{n}`" for b, n in top)
        L.append(f"- **`{s.domain}`{tag}**：{line}")
    L.append("")

    # 3. 跨站覆蓋矩陣
    L.append("## 3. 跨站覆蓋矩陣")
    L.append("")
    header = "| 主題桶 | " + " | ".join(
        f"{'★' if s.is_you else ''}{s.domain.split('//')[-1]}" for s in sites
    ) + " |"
    L.append(header)
    L.append("|" + "---|" * (len(sites) + 1))
    # 只列前 30 個最熱的桶，避免爆表
    bucket_tot = Counter()
    for b, row in gap["matrix"].items():
        bucket_tot[b] = sum(row.values())
    for b, _ in bucket_tot.most_common(30):
        row = gap["matrix"][b]
        cells = " | ".join(str(row[s.domain]) or "·" for s in sites)
        L.append(f"| {b} | {cells} |")
    L.append("")

    # 4. 對手主導 + 空白
    L.append("## 4. 對手主導領域")
    L.append("")
    if gap["dominated"]:
        for d in gap["dominated"]:
            L.append(f"- **{d['bucket']}** — `{d['leader']}` 壓制（{d['count']} 頁），其他站明顯少")
    else:
        L.append("- （沒有單站明顯壓制的桶）")
    L.append("")

    L.append("## 5. 你的空白候選（⚠ 全部需 Keyword Planner / Ahrefs 驗證後才動筆）")
    L.append("")
    if gap["has_you"] and gap["you_missing"]:
        L.append("**A. 對手有、你沒有**（對手押了你還沒卡位）：")
        for m in gap["you_missing"][:15]:
            L.append(f"- `{m['bucket']}` — 對手共 {m['rival_total']} 頁（{'、'.join(m['held_by'])}）")
        L.append("")
    elif not gap["has_you"]:
        L.append("> 沒傳 `--you`，跳過「對手有你沒有」比對。加上自己的站再跑一次更準。")
        L.append("")
    if gap["thin_everywhere"]:
        L.append("**B. 全行業薄弱**（沒人寫透，最值錢的卡位點 — 但 sitemap 看不出有沒有需求）：")
        for t in gap["thin_everywhere"][:15]:
            L.append(f"- `{t['bucket']}` — 最多的站也只 {t['max_count']} 頁（{t['present_in']} 站有碰）")
        L.append("")

    # 6. 新鮮度
    L.append("## 6. 新鮮度訊號（lastmod）")
    L.append("")
    for s in sites:
        if not s.urls:
            continue
        tag = "（你）" if s.is_you else ""
        L.append(f"**`{s.domain}`{tag}**")
        for sig in freshness_signal(s):
            L.append(f"- {sig}")
        L.append("")

    # 7. 貼給 AI 的 block
    L.append("## 7. 📋 貼這段給 Claude / ChatGPT 做語意分群")
    L.append("")
    L.append("> 路徑分桶只是粗活；真正的主題群要靠語意。把下面整段貼進 AI，"
             "它只負責歸納主題、指出對手主導與全行業空白 —— "
             "**叫它別碰搜尋量/競爭度**，那些它只會編。")
    L.append("")
    L.append("```text")
    L.append(render_ai_prompt(sites))
    L.append("```")
    L.append("")
    L.append("---")
    L.append("")
    L.append("## 完整循環（照這個跑，別在第一步就停）")
    L.append("")
    L.append("1. **腳本**：扒 sitemap → 上面的版圖 + 粗分桶（已完成）")
    L.append("2. **AI**：貼第 7 段 → 語意主題群 + 空白清單（搜尋量丟一邊）")
    L.append("3. **驗證**：空白逐一進 Keyword Planner / Ahrefs → 篩掉幽靈主題")
    L.append("4. **寫**：圍著真有需求的空白，寫一篇比對手更深、塞滿實測數據的文")
    L.append("5. **等**：給 Google 60–90 天 → 看 GSC 哪篇冒頭 → 繞著它補強")
    L.append("")
    return "\n".join(L)


def render_ai_prompt(sites: list[SiteData]) -> str:
    lines: list[str] = []
    lines.append("你是 SEO 內容策略分析師。下面是我和幾個對手的 sitemap URL 清單。")
    lines.append("請只做這三件事，其他別碰：")
    lines.append("1. 把每個站的 URL 歸納成語意主題群（不是看路徑，是看內容主題）。")
    lines.append("2. 指出每個對手『主導』哪些主題領域。")
    lines.append("3. 指出哪些主題是『全行業都還沒寫透』的空白。")
    lines.append("")
    lines.append("硬規則：")
    lines.append("- 絕對不要編搜尋量、搜尋意圖強度、競爭度、KD 這類數字 —— sitemap 裡")
    lines.append("  根本沒有，你一報就是幻覺。需求驗證我會自己拿去 Keyword Planner 做。")
    lines.append("- 不要排六個月內容月曆，只給我『值得驗證的主題清單』。")
    lines.append("- 對手頁數多不代表有排名，別用數量幫我做結論。")
    lines.append("")
    for s in sites:
        tag = " (這是我自己的站)" if s.is_you else ""
        lines.append(f"### {s.domain}{tag} — {len(s.urls)} 個 URL")
        # 控制長度：每站最多列 400 條
        for loc, _ in s.urls[:400]:
            lines.append(loc)
        if len(s.urls) > 400:
            lines.append(f"...（還有 {len(s.urls) - 400} 條，已截斷）")
        lines.append("")
    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────
# Optional: auto-cluster via Claude Code subscription (no API key)
# ─────────────────────────────────────────────────────────────
def run_cc_clustering(prompt: str) -> str | None:
    """走 Claude Code CLI（`claude -p`）做語意分群 —— 用的是你訂閱的登入身分，
    不需要 ANTHROPIC_API_KEY、不按 token 計費。失敗回 None，腳本照常完成。"""
    exe = shutil.which("claude")
    if not exe:
        print("  · 找不到 claude CLI（Claude Code 未裝或不在 PATH），跳過自動分群")
        return None
    try:
        proc = subprocess.run(
            [exe, "-p"],
            input=prompt,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=300,
        )
    except subprocess.TimeoutExpired:
        print("  · claude -p 逾時（300s），跳過")
        return None
    except OSError as exc:
        print(f"  · claude CLI 呼叫失敗（{exc.__class__.__name__}），跳過")
        return None
    if proc.returncode != 0:
        print(f"  · claude -p 回非零（{proc.returncode}）：{(proc.stderr or '')[:200]}")
        return None
    out = (proc.stdout or "").strip()
    return out or None


# ─────────────────────────────────────────────────────────────
# Optional: auto-call Anthropic API for the clustering step
# ─────────────────────────────────────────────────────────────
def run_ai_clustering(prompt: str) -> str | None:
    """需 ANTHROPIC_API_KEY 與 anthropic 套件。失敗回 None，腳本照常完成。"""
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        print("  · --ai 已開但沒有 ANTHROPIC_API_KEY，跳過自動分群（貼第 7 段手動做即可）")
        return None
    try:
        import anthropic  # lazy import
    except ImportError:
        print("  · 沒裝 anthropic 套件（python -m pip install anthropic），跳過自動分群")
        return None
    try:
        client = anthropic.Anthropic(api_key=key)
        msg = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=4000,
            messages=[{"role": "user", "content": prompt}],
        )
        return "".join(b.text for b in msg.content if getattr(b, "type", "") == "text")
    except Exception as exc:  # noqa: BLE001 - 任何 API 失敗都不該炸整支腳本
        print(f"  · AI 分群呼叫失敗（{exc.__class__.__name__}），跳過")
        return None


# ─────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────
def load_config(path: Path) -> tuple[list[str], str | None]:
    rivals: list[str] = []
    you: str | None = None
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        dom = parts[0]
        if len(parts) > 1 and parts[1].lower() == "you":
            you = dom
        else:
            rivals.append(dom)
    return rivals, you


def main() -> int:
    ap = argparse.ArgumentParser(description="對手 sitemap 作戰地圖產生器")
    ap.add_argument("--vs", nargs="*", default=[], help="對手域名（空白分隔）")
    ap.add_argument("--you", default=None, help="你自己的站（用來算空白）")
    ap.add_argument("--config", default=None, help="域名清單檔（一行一個，行尾 ` you` 標記自己）")
    ap.add_argument("--cc", action="store_true", help="用 Claude Code 訂閱（claude -p）做語意分群，免 API key（推薦）")
    ap.add_argument("--ai", action="store_true", help="改呼叫 Anthropic API 做語意分群（需 ANTHROPIC_API_KEY，另計費）")
    ap.add_argument("--out", default=None, help="輸出目錄（預設 outputs/sitemap-maps/）")
    args = ap.parse_args()

    rivals = list(args.vs)
    you = args.you
    if args.config:
        cfg_rivals, cfg_you = load_config(Path(args.config))
        rivals.extend(cfg_rivals)
        you = you or cfg_you

    if not rivals and not you:
        ap.print_help()
        print("\n[錯誤] 至少給一個 --vs 域名或 --config 檔", file=sys.stderr)
        return 2

    out_dir = Path(args.out) if args.out else OUT_DIR
    out_dir.mkdir(parents=True, exist_ok=True)

    targets: list[tuple[str, bool]] = []
    if you:
        targets.append((you, True))
    targets.extend((r, False) for r in rivals)

    print(f"扒 {len(targets)} 個站的 sitemap…")
    sites: list[SiteData] = []
    for dom, is_you in targets:
        print(f"  → {dom}{' (你)' if is_you else ''}")
        data = crawl_domain(dom, is_you)
        print(f"     抓到 {len(data.urls)} 個 URL，{len(data.sitemaps_used)} 個 sitemap")
        sites.append(data)

    if not any(s.urls for s in sites):
        print("\n[失敗] 所有站都抓不到 URL。檢查域名 / 網路 / 對方 robots 是否阻擋。", file=sys.stderr)
        return 1

    gap = build_gap_view(sites)
    ts = datetime.now(TW).strftime("%Y-%m-%d %H:%M (UTC+8)")
    md = render_markdown(sites, gap, ts)

    ai_out: str | None = None
    engine = ""
    if args.cc:
        print("用 Claude Code 訂閱（claude -p）做語意分群…")
        ai_out = run_cc_clustering(render_ai_prompt(sites))
        engine = "Claude Code 訂閱 (claude -p)"
    elif args.ai:
        print("呼叫 Anthropic API 做語意分群…")
        ai_out = run_ai_clustering(render_ai_prompt(sites))
        engine = "claude-sonnet-4-6 (API)"
    if ai_out:
        md += f"\n\n---\n\n## 8. AI 語意分群結果（{engine}）\n\n"
        md += "> ⚠ 以下主題清單仍需 Keyword Planner / Ahrefs 驗證搜尋量後才動筆。\n\n"
        md += ai_out + "\n"

    stamp = datetime.now(TW).strftime("%Y%m%d-%H%M")
    md_path = out_dir / f"map-{stamp}.md"
    json_path = out_dir / f"data-{stamp}.json"
    md_path.write_text(md, encoding="utf-8")
    json_path.write_text(
        json.dumps(
            {
                "generated_at": ts,
                "sites": [
                    {
                        "domain": s.domain,
                        "is_you": s.is_you,
                        "url_count": len(s.urls),
                        "sitemaps_used": s.sitemaps_used,
                        "errors": s.errors,
                        "buckets": dict(s.buckets.most_common()),
                        "urls": [{"loc": loc, "lastmod": lm} for loc, lm in s.urls],
                    }
                    for s in sites
                ],
                "gap": gap,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    print("\n地圖產出：")
    print(f"  Markdown: {md_path}")
    print(f"  JSON    : {json_path}")
    print("\n下一步：打開 .md，把第 7 段貼進 Claude/ChatGPT 做語意分群，")
    print("        再把空白主題丟 Keyword Planner / Ahrefs 驗證搜尋量。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
