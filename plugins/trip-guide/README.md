# trip-guide — 出國行前教練

帶完全不知道「該訂什麼、什麼時候訂」的人，把一趟出國旅遊從頭規劃完。

按 5 個時間層、17 個模組推進：出發前先確認 → 現在就要訂 → 前兩週 → 前三天 → 落地後。
用你的出發日往回推，算出每一項的**實際截止日**，最後給一份可以貼進待辦 App 的清單。

---

## 主文件在這裡

**這個工具的主體就是一份 markdown，只要拿到它就能用。**

| 用途 | 位置 |
|---|---|
| 給人看 | [`skills/trip-guide/SKILL.md`](skills/trip-guide/SKILL.md) |
| 給 AI 抓 | `https://raw.githubusercontent.com/Coolkidlab-Yin/Coolkidlab/master/plugins/trip-guide/skills/trip-guide/SKILL.md` |

其餘檔案在 [`skills/trip-guide/`](skills/trip-guide/) 底下：
`references/` 是 16 份判斷細節、`data/affiliate.json` 是推薦連結、`scripts/trip_checklist.py` 是零依賴的清單產生器。

---

## 三種用法

**手機（不用裝任何東西）**

1. 把上面那個 raw 網址丟給任何一個聊天 AI，跟它說「照這份文件帶我規劃出國」。
2. AI 說它讀不到網址的話，打開網址、全選、複製，整份貼進對話框。

接著講你要去哪、大概什麼時候、玩幾天、幾個人就可以開始。

**Gemini（建議存成 Gem）**

直接把主文件貼進 Gemini 聊天也能用，但實測多聊幾輪它會忘記規則。
穩的做法是建一個 Gem：Gemini 側欄 → 探索 Gem → 建立 Gem，
把 [`skills/trip-guide/GEM.md`](skills/trip-guide/GEM.md) 的內容貼進「指令」欄，存檔。
之後每次開那個 Gem 就是同一個教練，聊再多輪都不會掉。

**Claude Code（完整版）**

```
/plugin marketplace add Coolkidlab-Yin/Coolkidlab
/plugin install trip-guide@coolkidlab
```

裝好之後直接說「我要去日本要準備什麼」就會啟動。

**腳本單獨用**（Python 3，零依賴）

```bash
python skills/trip-guide/scripts/trip_checklist.py --to 福岡 --depart 2026-12-05 --days 4 --people 3 --kids --first-time --todo --for-user
```

---

## 邊界

- **不比價。** 要比哪天飛便宜，用 Google Flights 結果頁的日期網格，那件事它做得比這個工具好。
- **不代訂、不碰付款資料。**
- **不給簽證和入境規定的答案。** 只提醒「有這件事要辦」，確切規則一律要你自己去官方網站確認。
  那些規定改得很快，改了不會通知任何人，所以這個工具刻意不存任何一國的入境資料，連假也一樣。
- **會提醒 AI 講出自己缺什麼。** 只拿到 SKILL.md 而讀不到 `references/` 的時候，
  它應該出聲說缺什麼，而不是照樣輸出一份看起來完整的清單。

## 推薦連結

`data/affiliate.json` 裡有機票和住宿的 Trip.com 推廣連結，以及 Saily eSIM 的推薦碼，
清單裡出現時**一定同時附上揭露聲明**，而且每一項都會同時給替代方案。
把那個檔案的 `links` 和 `link_notes` 全部留空，導購就完全不會出現。

## License

MIT，見 [LICENSE](LICENSE)。
