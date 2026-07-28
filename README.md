# Coolkidlab

Coolkid AI Lab 的 Claude Code plugin 集。工具都來自 [coolkidlab.com](https://www.coolkidlab.com)
build-in-public 過程中的真實需求 — 每個工具背後都有對應的實戰連載可以讀。

## 安裝

```
/plugin marketplace add Coolkidlab-Yin/Coolkidlab
/plugin install article-overlap-checker@coolkidlab   # 或換成下面任一 plugin 名
```

## Plugins

兩類:**SEO 工具**(附腳本,裝了就能跑)與 **Workflow 教學 skill**(2026-07-28 新增 7 個,
來自 [coolkidlab.com/workflows](https://www.coolkidlab.com/workflows/) 的實戰 SOP —
裝了之後跟 Claude Code 說「我想做 XX」,它會照 skill 的步驟帶你把同款建起來)。

| Workflow skill | 一句話 | 獨立 repo |
|---|---|---|
| `threads-auto-poster` | Threads 自動發文 bot:排程+人在迴路選題+兩段式發文 | [repo](https://github.com/Coolkidlab-Yin/threads-auto-poster) |
| `ig-news-bot` | IG 新聞圖卡 bot:兩階 LLM 分工+Pillow 生圖 | [repo](https://github.com/Coolkidlab-Yin/ig-news-bot) |
| `family-line-bot` | 家族行程提醒 LINE bot:一句話建行程+cron 提醒 | [repo](https://github.com/Coolkidlab-Yin/family-line-bot) |
| `ga4-chatgpt-referral` | GA4 倒推 ChatGPT 引用來源的 4 招免費 SOP | [repo](https://github.com/Coolkidlab-Yin/ga4-chatgpt-referral) |
| `brand-profile-lockdown` | 讓 AI 當品牌顧問,定位鎖成 profile 檔 | [repo](https://github.com/Coolkidlab-Yin/brand-profile-lockdown) |
| `voice-profile-extraction` | 從寫作樣本萃取語氣指紋給 AI 用 | [repo](https://github.com/Coolkidlab-Yin/voice-profile-extraction) |
| `claude-code-checkpoint-system` | Claude Code 跨對話不失憶的斷點系統 | [repo](https://github.com/Coolkidlab-Yin/claude-code-checkpoint-system) |

教學 skill 只教方法與步驟,不含任何人的帳號金鑰或個人 voice/brand profile 內容。
交易類 workflow(市場掃描、交易日誌)依 Lab 的 YMYL 紅線不開源。

### article-overlap-checker — 文章撞稿檢查

掃你的網站(HTML 資料夾或 sitemap),用 TF-IDF 相似度回報三件事:

1. **撞稿候選** — 兩頁太像,搜尋引擎可能分不清誰該排名(keyword cannibalization)
2. **太接近** — 新文章選題的預警線
3. **孤島頁** — 跟全站都不像、缺內鏈脈絡的頁面

純 Python 標準庫、零依賴、中英混排通吃(CJK 字元 bigram)。0.33 秒掃 50 頁。

實戰背景:這工具在我自己的 75 頁網站上抓出過真實撞稿(兩篇比較文相似度 0.744),
也診斷出整個站的主題漂移 — 完整故事在
[連載 #25:帶最多流量的頁反而在拖累你想排的詞](https://www.coolkidlab.com/seo-journey/semantic-map-topic-drift.html)。

> 2026-07-18 更名:原名 semantic-map,為了讓人一看就知道用途改為 article-overlap-checker。

獨立 repo(不裝 plugin、想直接拿腳本用的話):[Coolkidlab-Yin/article-overlap-checker](https://github.com/Coolkidlab-Yin/article-overlap-checker)

### competitor-content-map — 對手內容地圖

把對手公開的 sitemap 當成「他主動攤開的內容版圖」,產出一張作戰地圖:

0. **先讀自己的站找主軸** — 第 0 步算出主打主題與 slug 語彙輪廓,空白候選標對齊度(貼近主軸/邊緣/偏離主軸⚠),避免照單全收造成主題漂移
1. **主題分桶** — 各對手把內容押在哪些領域
2. **跨站覆蓋矩陣 + 空白候選** — 大家都寫了什麼、還有什麼沒人寫透
3. **lastmod 新鮮度** — 誰在持續更新、誰在裝死(全站同日=假新鮮,工具會標)

純 Python 標準庫、零依賴。核心設計是三段分工:確定性的事腳本做、語意分群交給
AI(輸出自帶 prompt block,或 `--cc` 直接走 Claude Code 訂閱)、搜尋量兩邊都不碰 —
sitemap 裡沒這資料,AI 一報就是幽靈數字,需求請回 Keyword Planner / Ahrefs 驗證。

實戰背景:這是我規劃新主題前的固定前置動作 — 先看對手攤開的版圖,再決定寫什麼。

獨立 repo(不裝 plugin、想直接拿腳本用的話):[Coolkidlab-Yin/competitor-content-map](https://github.com/Coolkidlab-Yin/competitor-content-map)

## Credits

撞稿、主題漂移、語意集中度、扒對手 sitemap 找空白這些**觀念**,啟發自
[@darkseoking](https://www.threads.com/@darkseoking) 的 SEO 教學內容 — 值得追蹤的
繁中 SEO 創作者(sitemap 心法出自其開源的 akseolabs-seo/seo-coach,MIT)。
本工具集的**實作**(演算法選擇、閾值校準、CJK 處理、防編造分工)是 Coolkid AI Lab
在自己站台上實測的產物;閾值 0.62/0.55 來自 75 頁繁中站的實際分布,不是理論值。

觀念是公共的,實作是自己的,數據是站台的 — 三層分開標,是這個 Lab 的誠實原則。

## License

MIT
