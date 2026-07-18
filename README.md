# coolkid-plugins

Coolkid AI Lab 的 Claude Code plugin 集。工具都來自 [coolkidlab.com](https://www.coolkidlab.com)
build-in-public 過程中的真實需求 — 每個工具背後都有對應的實戰連載可以讀。

## 安裝

```
/plugin marketplace add WEIYIN-11/coolkid-plugins
/plugin install semantic-map@coolkid-plugins
/plugin install competitor-sitemap-map@coolkid-plugins
```

## Plugins

### semantic-map — 網站語意地圖

掃你的網站(HTML 資料夾或 sitemap),用 TF-IDF 相似度回報三件事:

1. **撞稿候選** — 兩頁太像,搜尋引擎可能分不清誰該排名(keyword cannibalization)
2. **太接近** — 新文章選題的預警線
3. **孤島頁** — 跟全站都不像、缺內鏈脈絡的頁面

純 Python 標準庫、零依賴、中英混排通吃(CJK 字元 bigram)。0.33 秒掃 50 頁。

實戰背景:這工具在我自己的 75 頁網站上抓出過真實撞稿(兩篇比較文相似度 0.744),
也診斷出整個站的主題漂移 — 完整故事在
[連載 #25:帶最多流量的頁反而在拖累你想排的詞](https://www.coolkidlab.com/seo-journey/semantic-map-topic-drift.html)。

### competitor-sitemap-map — 扒對手 sitemap 找內容空白

把對手公開的 sitemap 當成「他主動攤開的內容版圖」,產出一張作戰地圖:

1. **主題分桶** — 各對手把內容押在哪些領域
2. **跨站覆蓋矩陣 + 空白候選** — 大家都寫了什麼、還有什麼沒人寫透
3. **lastmod 新鮮度** — 誰在持續更新、誰在裝死(全站同日=假新鮮,工具會標)

純 Python 標準庫、零依賴。核心設計是三段分工:確定性的事腳本做、語意分群交給
AI(輸出自帶 prompt block,或 `--cc` 直接走 Claude Code 訂閱)、搜尋量兩邊都不碰 —
sitemap 裡沒這資料,AI 一報就是幽靈數字,需求請回 Keyword Planner / Ahrefs 驗證。

實戰背景:這是我規劃新主題前的固定前置動作 — 先看對手攤開的版圖,再決定寫什麼。

## Credits

撞稿、主題漂移、語意集中度、扒對手 sitemap 找空白這些**觀念**,啟發自
[@darkseoking](https://www.threads.com/@darkseoking) 的 SEO 教學內容 — 值得追蹤的
繁中 SEO 創作者(sitemap 心法出自其開源的 akseolabs-seo/seo-coach,MIT)。
本工具集的**實作**(演算法選擇、閾值校準、CJK 處理、防編造分工)是 Coolkid AI Lab
在自己站台上實測的產物;閾值 0.62/0.55 來自 75 頁繁中站的實際分布,不是理論值。

觀念是公共的,實作是自己的,數據是站台的 — 三層分開標,是這個 Lab 的誠實原則。

## License

MIT
