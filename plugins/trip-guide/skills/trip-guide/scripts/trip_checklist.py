"""出國行前清單：把「該辦什麼」展開成帶實際日期的時間軸。

不知道該訂什麼的人，缺的不是價格，是「現在到底輪到哪一項」。這支腳本把 17 個
模組按五個時間層排開，用使用者的出發日算出每一項的實際截止日期。

**不連網、不帶任何會過期的資料。** 簽證規則、連假日期都不在這支腳本裡——
那些改得很快，存了就會爛掉，而且爛掉的時候沒有人會發現。
腳本只負責提醒「有這件事要辦」和把日期算對；**答案由執行它的 AI 去查**。

零依賴，只用 Python 標準庫。

    python trip_checklist.py --to 韓國 --depart 2026-10-13 --days 5
    python trip_checklist.py --to 東京 --depart 2026-12-20 --days 6 --people 2 --first-time
"""

from __future__ import annotations

import argparse
import sys
import json
import re
from datetime import date, timedelta
from pathlib import Path
from urllib.parse import parse_qsl, quote, urlencode, urlsplit, urlunsplit

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
AFFILIATE_PATH = DATA_DIR / "affiliate.json"

# (模組編號, 標題, 幾天前要辦, 導購分類, 一句話說明)
# lead=None 代表「越早越好」，lead=0 代表落地後再說。
TIERS: list[tuple[str, list[tuple[str, str, int | None, str, str]]] ] = [
    # Tier 0 三項也要有分類，不然 --booked 抑制不掉——
    # 一個開口就說「護照我確認過了」的人，每份清單第一行還是戳他一次。
    ("Tier 0 — 出發前先確認（沒過這關，訂什麼都白訂）", [
        ("M1", "護照效期夠不夠", None, "passport",
         "多數國家對入境當天的剩餘效期有門檻，不是「還沒過期就好」。門檻幾個月要查"),
        ("M2", "簽證／入境許可", None, "visa",
         "免簽不等於什麼都不用辦，很多國家改成線上事前許可。規則以官方為準。"
         "**有轉機的話，轉機國是另一套規定，要分開查**"),
        ("M3", "撞不撞連假", None, "holiday",
         "連假會讓住宿翻倍、票券賣光"),
    ]),
    ("Tier 1 — 現在就要訂（會賣完、會漲）", [
        ("M4", "機票", 60, "flights",
         "這裡不比價；要比哪天便宜用 Google Flights 的「日期網格」。"
         "**有轉機就先問兩件事：同一張票嗎？想不想出機場？**"),
        ("M5", "住宿", 45, "hotels",
         "位置比價格重要，離車站 10 分鐘和 30 分鐘五天下來差很多"),
        ("M6", "要預約的票券", 30, "tickets",
         "有些東西不是貴，是根本買不到——樂園快速通關、熱門展覽、需抽選的餐廳"),
    ]),
    ("Tier 2 — 出發前 2 週", [
        ("M7", "交通票券／周遊券", 14, "transport",
         "划不划算看行程，不是買了一定賺"),
        ("M8", "租車＋國際駕照", 14, "carrental",
         "國際駕照要在台灣先辦，出國之後辦不了。去監理站，流程要查"),
        ("M9", "旅遊保險", 14, "insurance",
         "信用卡附的旅平險通常只保搭乘期間，不保旅程中生病"),
    ]),
    ("Tier 3 — 出發前 3 天", [
        ("M10", "eSIM／網卡", 3, "esim",
         "出發前買、落地開；先確認手機支不支援 eSIM、有沒有鎖網"),
        ("M11", "線上入境表", 3, "",
         "很多國家改成線上填，而且有時間窗、太早填無效。窗口多長要查"),
        ("M12", "換匯與海外刷卡", 3, "",
         "不用換一大包現金，但要有一點；刷卡先確認海外手續費與開通狀態"),
    ]),
    ("Tier 4 — 落地後再說", [
        ("M13", "交通卡", 0, "",
         "多數地方落地買就好，有些手機可以直接加卡"),
        ("M14", "行李寄放", 0, "",
         "早班機到、晚班機走的那兩天，行李放哪很影響體感"),
        ("M15", "退稅", 0, "",
         "買之前就要問店家能不能退，事後補不了"),
    ]),
]

# 這幾條以前只有一行標題，細節全在 references/11-scenarios.md。
# 實測發現：一個嚴格照「用到才讀 reference」的 session 可能整趟沒讀那個檔，
# 於是「藥不要放託運」這種會出人命的資訊整個消失。
# 安全類的東西不能掛在「模型今天有沒有想到要讀那個檔」上，所以直接寫進輸出。
OPTIONAL = {
    "kids": ("M16", "帶小孩", [
        "**小孩也要有自己的護照、自己的簽證／入境許可、自己的入境表**——不是跟著大人就好",
        "**未成年護照的效期比大人短**，別看到「還沒過期」就放心，去查清楚剩幾年",
        "未滿 2 歲是嬰兒票（不佔位），要事先跟航空公司登記，機位有限",
        "推車多半可以帶到登機門再託運，但要先問",
        "**訂房要看「可住人數」和「兒童入住政策」**——很多標準雙人房不給 3 個人住，"
        "或要加床費、要事先申請。訂房網站的人數欄「大人」和「兒童」是分開算的，別全填成大人",
        "**行程排少一點**，小孩的節奏比大人慢很多",
    ]),
    "seniors": ("M16", "帶長輩", [
        "**藥放隨身不要託運**，行李被送去別的城市就沒藥吃",
        "**多帶幾天份**——班機取消、延誤、改期都會讓藥斷掉",
        "**請醫生開處方箋，最好有英文診斷書**，過海關才說得清",
        "**有些藥在某些國家是管制品**，出發前要查",
        "保險**看年齡上限**，而且**既往症要打客服問清楚**（但別因為有既往症就整包不買）",
        "**輪椅／機場協助可以事先跟航空公司申請，免費，但要提前訂**——"
        "跟特殊餐（低鹽、軟食）、優先登機是同一通電話講完",
        "住宿看「離車站步行幾分鐘」＋**有沒有電梯**；地鐵站不是每站都有電梯，要先查",
        "**行程排少一點**，能坐下來休息的點要排進去",
        "跨時區的話，**服藥時間怎麼調要問醫生**",
    ]),
    "solo": ("M16", "一個人去", [
        "**外交部「旅外國人動態登錄」建議做**——免費，出事的時候他們找得到你",
        "住宿位置比省錢重要，看的是**晚上走回去那段路有沒有燈、有沒有人**",
        "行程和住宿地址**留一份給台灣的家人朋友**",
        "有些餐廳不收單人訂位，非去不可的先問",
    ]),
    "first_time": ("M17", "第一次出國", [
        "國際線建議起飛前 **2.5–3 小時**到機場",
        "轉機跟著 Transfer 指標走，**不要走到入境**，走錯要重過安檢",
        "**同一張票的託運行李會直掛到終點**——轉機時間再長也拿不到，"
        "藥、換洗、充電線、外套要放隨身",
        "落地順序：入境指標 → 證照查驗 → 提領行李 → 海關 → 出關",
    ]),
}

# TIERS 裡的名稱是「模組標題」，拿來當待辦事項會變成問句——
# 「護照效期夠不夠」貼進待辦 App，三天後他不知道自己要幹嘛。
# 待辦要動詞開頭、帶關鍵限定。這裡是同一件事的兩種寫法。
TODO_TEXT = {
    "M1": "查護照到期日，再查目的地要求剩幾個月",
    "M2": "查目的地要辦哪種入境許可，順便看要幾個工作天；有轉機的話轉機國另外查一次",
    "M3": "",                     # 這件事是 agent 做的，不要丟回給使用者
    "M4": "訂機票",
    "M5": "訂住宿，挑走路 5 分鐘到車站的",
    "M6": "訂要預約的票券，沒有非去不可的就刪掉這行",
    "M7": "查周遊券划不划算，不划算就不要買",
    "M8": "辦國際駕照，出國就辦不了",
    "M9": "買旅遊保險",
    "M10": "買 eSIM 或網卡",
    "M11": "填線上入境表 ← 不要提前填，有時間窗",
    "M12": "確認信用卡海外交易已開通，換一點現金",
    "M13": "落地買交通卡",
    "M14": "退房後行李先問飯店能不能寄放",
    "M15": "要退稅就在買的當下跟店員說，事後補不了",
}

# 退稅不是「落地後」做的事，是「買東西的當下」。寫成落地後等於沒講。
TODO_WHEN = {"M15": "買東西時"}

# Tier 0 是「確認」不是「購買」，這三類永遠不掛連結。以前這件事只是碰巧成立——
# affiliate.json 剛好沒填這三個 key。哪天談成一個簽證代辦的聯盟方案填進去，
# 預設指令就會對護照還沒確認的人噴導購連結，正好是這道閘門要防的事。
TIER0_CATS = {"passport", "visa", "holiday"}

# 這七條會出事，而且散在各個 reference 裡。以前它們掛在 --first-time 和 --seniors 上，
# 等於「安全內容要看 agent 記不記得帶那個旗標」——沒被標成新手的成年人整趟拿不到
# 「行動電源不能託運」，而住宿地址和館處電話在任何參數組合下都不會出現。
# 現在無條件印。行動電源機上禁用、回台肉品、現金申報是 2026-08-17 上網對過的缺口：
# 台灣航空 2025 起航程中全程禁用禁充電行動電源；肉品是台灣旅客最常踩的海關重罰；
# 現金超過門檻沒申報是「超額直接沒收」（財政部關務署）。
# 三條都只寫機制不寫數值（幾顆、幾 Wh、罰多少、門檻幾萬都會變）。
MUST_SAY = [
    "**行動電源只能手提，不能託運**（櫃檯被攔很常見）；**多數航空機上不能用也不能充電**，"
    "能帶幾顆、多大容量看你的航空公司",
    "**藥放隨身、多帶幾天份**，處方箋最好有英文版",
    "**登機門會變**，要看螢幕不要只看登機證",
    "**住宿地址存在手機裡**（入境表和海關問的是地址，不是飯店名字）",
    "**駐外館處的急難電話出發前存好**",
    "**肉製品、生鮮蔬果不能帶回台灣**——買伴手禮前想到這條，被海關查到罰得很重",
    "**大額現金出入境要申報**——台灣和目的地各有門檻，超過沒申報，超額會被直接沒收；"
    "要帶多少之前，兩邊的規定都查一次",
]

# 抑制的理由要分類講。以前只有一段寫死的租車文案，--days 1 抑制住宿時
# 會在「住宿」底下印出一段講租車的話。
AUTO_REASON = {
    "carrental": "你沒說要租車，所以這項不推。真的要租再跟我說，"
                 "**但國際駕照無論如何都建議先辦**——出國就辦不了",
    "hotels": "當天來回沒有過夜，這項不適用",
}

# --booked 的合法值。靜默吃掉錯字是最糟的：輸出跟沒帶參數時一模一樣。
VALID_CATS = {"passport", "visa", "holiday", "flights", "hotels", "tickets",
              "transport", "carrental", "insurance", "esim"}

_SLOT = re.compile(r"\{(\w+)\}")


def fill_url(template: str, values: dict[str, str]) -> str:
    """把 {dest} 這種佔位符換成實際值。換不出來的整個查詢參數丟掉。

    丟掉而不是留空，是因為 `?city=&checkin=` 這種空參數多半會把搜尋弄壞。
    少一個參數還是一條能用的網址，空參數不是。
    """
    if not _SLOT.search(template):
        return template
    parts = urlsplit(template)
    if any(not values.get(m.group(1)) for m in _SLOT.finditer(parts.path)):
        return ""
    path = _SLOT.sub(lambda m: quote(values.get(m.group(1), ""), safe=""), parts.path)
    kept = []
    for key, raw in parse_qsl(parts.query, keep_blank_values=True):
        if any(not values.get(m.group(1)) for m in _SLOT.finditer(raw)):
            continue
        kept.append((key, _SLOT.sub(lambda m: values.get(m.group(1), ""), raw)))
    return urlunsplit((parts.scheme, parts.netloc, path, urlencode(kept), parts.fragment))


def load_affiliate() -> tuple[dict[str, str], str, dict[str, str]]:
    try:
        # utf-8-sig：被 Out-File -Encoding UTF8 動過的檔會帶 BOM，用 utf-8 讀會丟
        # JSONDecodeError 然後被下面吞掉，症狀是「導購整組無聲消失」而不是報錯。
        cfg = json.loads(AFFILIATE_PATH.read_text(encoding="utf-8-sig"))
    except (FileNotFoundError, json.JSONDecodeError):
        return {}, "", {}
    raw = cfg.get("links") if isinstance(cfg, dict) else None
    links = ({k: v.strip() for k, v in raw.items() if isinstance(v, str) and v.strip()}
             if isinstance(raw, dict) else {})
    disclosure = cfg.get("disclosure", "") if isinstance(cfg, dict) else ""
    # 揭露跟連結綁死：沒有揭露就一條連結都不出。
    # 00-boundaries.md 寫「不可能只出連結不出揭露」,那句話以前是靠人守的。
    if not str(disclosure).strip():
        return {}, "", {}
    # link_notes：該類推廣要使用者自己動手時（例如結帳輸推薦碼）印在連結後的操作句。
    raw_notes = cfg.get("link_notes") if isinstance(cfg, dict) else None
    link_notes = ({k: v.strip() for k, v in raw_notes.items()
                   if isinstance(v, str) and v.strip()}
                  if isinstance(raw_notes, dict) else {})
    return links, str(disclosure), link_notes


# 這支腳本以前自己帶一份連假資料（台灣＋日本）。拿掉了，理由跟入境規定同一條：
#
#   資料會過期，過期時沒有任何跡象讓人發現；而且只收兩個地區，
#   去韓國、泰國、歐洲的人看到表上沒有 🎌，會以為系統查過了。
#
# 現在改成：**連假由執行這份文件的 AI 去查**（它查得到最新的，而且不限國家），
# 查到之後用 --holiday 告訴腳本，腳本只負責把提前量加倍這個「機制」做對。
#
# 機制留著、資料交出去。這是這個 skill 一貫的分界線。


def lead_of(code: str, lead: int | None, from_hit: bool, to_hit: bool) -> int | None:
    """撞連假就把提前量加倍——但只加該加的那一項。

    出發地的連假推高的是**機票**（大家同時出境）；目的地的連假推高的是
    **住宿與票券**（當地都在放假）。整批加倍會叫人為了一個不存在的漲價提前訂房。

    文件寫了「撞連假提前一倍」，以前腳本只印一行警告、日期完全沒動，
    兩條路差過 58 天。規則寫在文件裡而工具不執行，等於沒有規則。
    """
    if lead is None or lead == 0:
        return lead
    if code == "M4" and from_hit:
        return lead * 2
    if code in ("M5", "M6") and to_hit:
        return lead * 2
    return lead


def _deadline(depart: date, lead: int | None) -> str:
    if lead is None:
        return "**現在就去確認**"
    if lead == 0:
        return "落地後"
    day = depart - timedelta(days=lead)
    left = (day - date.today()).days
    if left < 0:
        return f"**已經過了建議時點（{lead} 天前），盡快處理**"
    if left == 0:
        # 以前是 <=，截止日剛好今天會被報成「已經過了」，而 02-timing.md 規定
        # 看到那句就要切換成「來不及」的講法——等於叫還來得及的人放棄。
        return f"{day.isoformat()}（**今天最後一天**）"
    return f"{day.isoformat()}（還有 {left} 天）"


def _short(text: str) -> str:
    """待辦要掃得到，所以砍掉補述。

    以前連「（」也砍，但動作常常在括號後面（「未滿 2 歲是嬰兒票（不佔位），
    要事先跟航空公司登記」），砍完剩一句沒有動作的陳述句。
    """
    for sep in ("——", "；"):
        text = text.split(sep)[0]
    return text.replace("**", "").strip("，。 ")


def build_todo(args: argparse.Namespace, told: set[str],
               from_hit: bool, to_hit: bool) -> str:
    """一行一件事、日期在前的待辦清單，設計成直接貼進待辦 App。

    刻意不放連結、不放理由：連結會變成一面牆，理由在對話裡已經講過。
    這份是給他事後照著打勾用的，不是拿來讀的。

    只有使用者**明說**不用的項目才拿掉（`told`）。自動抑制的那些是「不推薦連結」，
    不是「這件事不用做」——國際駕照就掛在租車那一項底下，
    一起消失的話會漏掉整份清單裡唯一完全無法補救的東西。
    """
    depart = date.fromisoformat(args.depart)
    lines = [f"{args.to}行前 to-do（{depart.month}/{depart.day} 出發）", ""]
    if from_hit or to_hit:
        lines += ["※ 撞到連假，相關項目的提前量已經加倍", ""]

    def when(lead: int | None) -> str:
        if lead is None:
            return "現在　"
        if lead == 0:
            return "落地後"
        d = depart - timedelta(days=lead)
        return "現在　" if d <= date.today() else f"{d.month:02d}/{d.day:02d}"

    per_head = "，每個人各一份" if args.people > 1 else ""
    for _, items in (TIERS if args.tier == "all" else TIERS[:int(args.tier) + 1]):
        for code, _, lead0, cat, _ in items:
            lead = lead_of(code, lead0, from_hit, to_hit)
            if cat and cat in told and code != "M8":
                continue          # M8 例外見 docstring：唯一出國就補不回來的一項
            text = TODO_TEXT.get(code, "")
            if not text:
                continue          # M3 之類「這是 agent 的工作」的項目不進待辦
            if code in ("M1", "M2", "M11") and per_head:
                text += per_head  # 護照、入境許可、入境表都是一人一份，最會漏
            lines.append(f"□ {TODO_WHEN.get(code, when(lead))}　{text}")

    if args.holiday == "none":
        # 這是「現在」的項目，掛在整份最底下就掃不到（日期在最前面才是這份表的賣點）。
        # 出發地要用 --from，寫死「台灣」的話，人在東京出發那行就是錯的指示。
        lines.insert(min(2, len(lines)),
                     f"□ 現在　　查{args.to}和{args.frm}那幾天有沒有連假")

    for key in ("kids", "seniors", "solo", "first_time"):
        if getattr(args, key):
            _, name, notes = OPTIONAL[key]
            lines += ["", f"— {name} —"]
            lines += [f"□ 　　　　{_short(n)}" for n in notes]

    lines += ["", "— 不管怎樣都要記得 —"]
    lines += [f"□ 　　　　{_short(n)}" for n in MUST_SAY]
    return "\n".join(lines) + "\n"


def build(args: argparse.Namespace) -> str:
    depart = date.fromisoformat(args.depart)
    back = depart + timedelta(days=args.days - 1)
    # 連假由 AI 查，查到之後用 --holiday 告訴腳本是哪一邊撞到。
    from_hit = args.holiday in ("from", "both")
    to_hit = args.holiday in ("to", "both")
    links, disclosure, link_notes = load_affiliate()
    # {days} 和 {nights} 一定要分開。保險是按「天」投保的，餵 nights 進去會少保一天,
    # 而少的正好是回程那天——最容易延誤、最需要不便險的那天。實測踩過。
    slots = {"dest": args.to, "depart": depart.isoformat(), "back": back.isoformat(),
             "days": str(args.days), "nights": str(max(0, args.days - 1)),
             "people": str(args.people)}
    # 帶小孩的時候不要把總人數當成大人數送出去。訂房站的 adult= 只算大人，小孩走 children=，
    # 而這支腳本只知道總人數、不知道怎麼拆。送 adult=3 給「2 大 1 小」是用錯的房型條件在搜，
    # 還會篩掉一批房。整個不送，讓使用者在頁面上自己選，比送一個錯的安全。
    if args.kids:
        slots.pop("people")

    # 腳本手上已經有這些訊號，就不該把用不到的東西掛連結出去。
    # 「不要為了有連結就多推一項他不需要的東西」以前只寫在 00-boundaries.md，
    # 靠 agent 自律；實測發現只要照「全部列給我」的例外倒表，那條線就破了。
    told = {c.strip() for c in (args.booked or "").split(",") if c.strip()}
    unknown = told - VALID_CATS
    if unknown:
        print(f"⚠ --booked 認不得：{'、'.join(sorted(unknown))}"
              f"（可用：{'、'.join(sorted(VALID_CATS))}）", file=sys.stderr)
    auto = set(TIER0_CATS)
    if not args.driving:
        auto.add("carrental")      # 沒說要租車就不要推租車
    if args.days <= 1:
        # checkin == checkout 的訂房網址，Trip.com 會**靜默**丟掉整組日期，
        # 使用者拿到的是他上次搜尋或系統預設的日期，而且畫面沒有任何提示。
        auto.add("hotels")
    skip = told | auto

    if args.todo:
        return build_todo(args, told, from_hit, to_hit)

    tiers = TIERS if args.tier == "all" else TIERS[:int(args.tier) + 1]

    out = [
        f"# {args.to} 行前清單",
        "",
        f"{args.frm} 出發 · {depart.isoformat()} → {back.isoformat()} · "
        f"{args.days} 天 · {args.people} 人",
        "",
    ]
    # 出發地的連假推高的是機票和機場人潮；目的地的連假才推高住宿與票券。
    # 混在一起講，會讓人為了一個不存在的住宿漲價提前訂房。
    if from_hit:
        out += ["> 🎌 **出發那幾天撞到出發地的連假**　"
                "機票會貴、機場會擠。已經把機票的提前量加倍。", ""]
    if to_hit:
        out += ["> 🎌 **目的地那幾天在放假**　"
                "住宿與票券會貴而且賣得快。已經把住宿與票券的提前量加倍。", ""]
    if args.holiday == "none":
        out += ["> ⚠ **這張表沒有查過任何連假。** 這支腳本不帶連假資料——"
                "資料會過期，而且過期時沒有人會發現。"
                "**出發地和目的地的假期請自己查一次。**", ""]
    if args.holiday == "none" and not args.for_user:
        out += ["> （查到之後用 `--holiday from|to|both` 重跑，提前量會自動加倍。）", ""]
    if args.tier != "all" and not args.for_user:
        out += [f"> 這張只有到 Tier {args.tier}。"
                "**前面的關卡沒過之前，後面的不要推給使用者。**", ""]

    used_links = False
    for title, items in tiers:
        out += [f"## {title}", ""]
        for code, name, lead, cat, note in items:
            out.append(f"### {code}　{name}")
            out.append("")
            out.append(f"- {note}")
            lead = lead_of(code, lead, from_hit, to_hit)
            out.append(f"- **時間**：{_deadline(depart, lead)}")
            if cat in told:
                out.append("- （你說這項已經處理了／用不到，跳過）")
            elif cat in auto and cat in AUTO_REASON:
                out.append(f"- （{AUTO_REASON[cat]}）")
            url = "" if (args.no_links or not cat or cat in skip) else \
                fill_url(links.get(cat, ""), slots)
            if url:
                # 揭露跟著每一條連結走。放在整份最尾端等於沒有——
                # 使用者看到第四條連結時根本不知道那是分潤。
                extra = link_notes.get(cat, "")
                tail = f"　{extra}" if extra else ""
                out.append(f"- [去看看]({url}){tail}　*{disclosure}*")
                used_links = True
            out.append("")

    extras = [OPTIONAL[k] for k in ("kids", "seniors", "solo", "first_time")
              if getattr(args, k)]
    if extras:
        out += ["## Tier 5 — 你這趟的額外項目", "",
                "**這一段跟 Tier 沒關係，現在就要知道。** 裡面有幾條是出發前才處理就來不及的。",
                ""]
        for code, name, notes in extras:
            out += [f"### {code}　{name}", ""]
            out += [f"- {n}" for n in notes]
            out.append("")

    out += ["---", "", "## 不管怎樣都要記得的七件事", ""]
    out += [f"- {n}" for n in MUST_SAY]
    out.append("")

    if args.people > 1:
        out += ["---", "",
                f"**⚠ 你們有 {args.people} 個人：護照、簽證／入境許可、線上入境表"
                "都是「一人一份」，不是一家一份。**", ""]
    if used_links and not args.for_user:
        out += ["---", "",
                "上面標了連結的項目是推薦連結，用不用都可以，"
                "**每一項我都該同時告訴你替代方案**——沒講的話直接問我。", ""]
    if args.for_user:
        return "\n".join(out) + "\n"
    out += [
        "---",
        "",
        "**簽證與入境規定改得很快，這張清單只提醒「有這件事要辦」，"
        "確切規則一律以官方網站為準。**",
        "",
        "**這張表不含任何價格。** 價格每天都在變，要比哪天飛便宜，"
        "用 Google Flights 結果頁的「日期網格」按鈕。",
    ]
    return "\n".join(out) + "\n"


def main() -> int:
    p = argparse.ArgumentParser(
        prog="trip_checklist.py",
        description="把出國該辦的事展開成帶實際日期的清單")
    p.add_argument("--to", required=True, help="目的地，國家或城市，純文字即可")
    p.add_argument("--depart", required=True, help="出發日 2026-10-13")
    p.add_argument("--days", type=int, required=True, help="幾天")
    p.add_argument("--people", type=int, default=1, help="幾個人（預設 1）")
    p.add_argument("--from", dest="frm", default="台北", help="出發地（預設 台北）")
    p.add_argument("--solo", action="store_true",
                   help="一個人去（--people 1 會自動帶入）")
    p.add_argument("--first-time", dest="first_time", action="store_true",
                   help="第一次出國")
    p.add_argument("--kids", action="store_true", help="帶小孩")
    p.add_argument("--seniors", action="store_true", help="帶長輩")
    p.add_argument("--driving", action="store_true", help="要租車（國際駕照提前提醒）")
    # 預設只出 Tier 0，是刻意的：文件的鐵律是「Tier 0 沒過之前不要推薦任何要花錢的
    # 東西」，但那條以前只靠 agent 自律。實測發現只要一手滑把整份 stdout 貼出去，
    # 護照過期的使用者就會拿到七個「去看看」按鈕。所以把閘門做進工具裡。
    p.add_argument("--tier", default="0", choices=["0", "1", "2", "3", "4", "all"],
                   help="出到第幾層（預設只出 Tier 0；確認過了再往下開）")
    p.add_argument("--no-links", dest="no_links", action="store_true",
                   help="不要帶推薦連結")
    p.add_argument("--booked", default="",
                   help="已經訂好／用不到的品類，逗號分隔，會跳過不推薦。"
                        "例如 flights,hotels,transport")
    p.add_argument("--holiday", default="none",
                   choices=["none", "from", "to", "both"],
                   help="這趟撞到誰的連假（你自己查，腳本不帶資料）。"
                        "from=出發地→機票提前量加倍；to=目的地→住宿與票券加倍；both=兩邊")
    p.add_argument("--for-user", dest="for_user", action="store_true",
                   help="拿掉只有 agent 需要看的自律提醒與方法論尾註，直接給使用者看")
    p.add_argument("--todo", action="store_true",
                   help="改出可以直接貼進待辦 App 的清單（一行一件事、無連結）")
    p.add_argument("--out", help="寫進檔案（預設直接印出來）")
    args = p.parse_args()

    if args.days < 1:
        raise SystemExit("--days 至少要 1")
    if args.days > 365:
        raise SystemExit(f"--days 收到 {args.days}，超出這份清單的設計範圍。"
                         "是不是跟 --depart 打反了？")
    if args.people < 1:
        raise SystemExit(f"--people 至少要 1，收到 {args.people}")
    # 一個人去就是一個人去，不該取決於 agent 記不記得多帶一個旗標。
    # 旅外登錄是零成本、出事時決定性的一項。
    if args.people == 1:
        args.solo = True
    try:
        dep = date.fromisoformat(args.depart)
    except ValueError:
        raise SystemExit(f"--depart 要像 2026-10-13，收到 '{args.depart}'") from None
    if dep < date.today():
        # 不擋的話會產出一份格式完全正常、日期全是過去式的清單，
        # 還附上帶著過去日期的訂房連結，而使用者不會發現。
        raise SystemExit(f"--depart 是過去的日期（{args.depart}，今天 {date.today()}）。"
                         "確認是不是打錯年份；要規劃改期就用新的出發日重跑。")

    text = build(args)
    # to-do 模式沒有模組標題（它用 TODO_TEXT），租車的提醒在 build_todo 裡另外處理。
    if args.driving and not args.todo and "carrental" not in (args.booked or ""):
        old = "### M8　租車＋國際駕照"
        if old in text:
            text = text.replace(old, old + "　⚠ 你這趟要租車，這項不要拖")
        elif args.tier in ("2", "3", "4", "all"):
            raise SystemExit("內部錯誤：--driving 找不到 M8 標題，TIERS 的文字被改過了")
    if args.out:
        path = Path(args.out)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        print(f"已寫入 {path.resolve()}")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
