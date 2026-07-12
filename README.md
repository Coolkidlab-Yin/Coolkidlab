# coolkid-plugins

Coolkid AI Lab 的 Claude Code plugin 集。工具都來自 [coolkidlab.com](https://www.coolkidlab.com)
build-in-public 過程中的真實需求 — 每個工具背後都有對應的實戰連載可以讀。

## 安裝

```
/plugin marketplace add WEIYIN-11/coolkid-plugins
/plugin install semantic-map@coolkid-plugins
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

## Credits

撞稿、主題漂移、語意集中度這些**觀念**,啟發自 [@darkseoking](https://www.threads.com/@darkseoking)
的 SEO 教學內容 — 值得追蹤的繁中 SEO 創作者。本工具的**實作**(演算法選擇、
閾值校準、CJK 處理)是 Coolkid AI Lab 在自己站台上實測的產物;閾值 0.62/0.55
來自 75 頁繁中站的實際分布,不是理論值。

觀念是公共的,實作是自己的,數據是站台的 — 三層分開標,是這個 Lab 的誠實原則。

## License

MIT
