---
name: competitor-content-map
description: >
  扒對手 sitemap 做內容作戰地圖。當使用者想知道「對手網站都寫了哪些主題」
  「這個行業還有什麼內容空白能卡位」「對手最近在更新什麼」,或提到
  競品內容分析/對手 sitemap/內容缺口(content gap)/選題卡位 時使用。
  輸入是對手域名清單,輸出是主題分桶、跨站覆蓋矩陣、空白候選、lastmod
  新鮮度訊號的 Markdown 作戰地圖。
---

# 對手內容地圖(competitor-content-map)

## 什麼時候用

- 規劃新主題前,想知道各家對手把內容押在哪些領域
- 想找「全行業都沒寫透」的卡位空白
- 想看對手最近在更新什麼(lastmod 新鮮度訊號)

## 怎麼跑

工具在 `scripts/competitor_sitemap_map.py`,純 Python 標準庫,無需安裝任何東西:

```bash
# 基本:給對手域名。⚠ --out 收的是「輸出資料夾」不是檔名 ——
# 給 map.md 會建出一個叫 map.md 的資料夾;該名稱若已是檔案則直接報錯
python scripts/competitor_sitemap_map.py --vs rival1.com rival2.com --out ./maps

# 加上自己的站,覆蓋矩陣會多一欄「你有沒有寫」
python scripts/competitor_sitemap_map.py --you www.your-site.com --vs rival1.com rival2.com --out ./maps

# 域名多時用設定檔:一行一個域名,# 開頭為註解,行尾加 ` you` 標記自己的站
# 先複製範本:cp examples/competitors.txt.example competitors.txt
python scripts/competitor_sitemap_map.py --config competitors.txt --out ./maps

# 讓 AI 接手語意分群:--cc 走 Claude Code 訂閱(不必另外辦 API key,
# 但要有 claude CLI 且已登入),--ai 走 API(需 pip install anthropic + API key)
python scripts/competitor_sitemap_map.py --vs rival1.com --cc --out ./maps
```

省略 `--out` 時預設寫到 skill 目錄下的 `outputs/sitemap-maps/`。
檔名帶到秒的時間戳,同一個資料夾可以一直累積。

## 三段分工(核心原則:別讓 AI 編數字)

1. **確定性的事腳本做**:抓 sitemap.xml / robots.txt / sitemap index、解 .xml.gz、
   去重、依 URL 路徑粗分桶、算 lastmod 新鮮度、跨站比對找空白。而且是**先讀自己
   再掃對手** — 第 0 步先算出你自己站的主軸輪廓,空白候選才有對齊基準,不會被帶去
   主題漂移。
2. **語意判斷交給 AI**:主題分群與空白候選的歸類 — 輸出自帶一段可直接貼給
   Claude/ChatGPT 的 prompt block。
3. **搜尋量與競爭度兩邊都不碰**:sitemap 裡根本沒有這資料,AI 一報就是幽靈數字;
   需求要回 Google Keyword Planner / Ahrefs 免費工具驗證。

## 三個關卡(回報給使用者時要帶到)

1. AI 報的搜尋量一個字都別信 — 去 Keyword Planner / Ahrefs 驗證。
2. lastmod 全站同一天 = sitemap 產生器自動填的假新鮮,別被騙。
3. 對手掛 100 篇 blog 不代表 100 篇有排名,數量多別焦慮。

## 侷限(誠實告知使用者)

- 只看得到對手「願意放進 sitemap」的版圖;沒掛 sitemap 的站抓不到(工具會回報)。
- URL 路徑分桶是粗分,語意精度靠後段 AI 分群補;AI 分群結果的「優先序」
  仍是推測,不是數據。
