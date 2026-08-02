---
name: ga4-chatgpt-referral
description: >
  用 GA4 到達網頁與工作階段 referral、OpenAI 的 ChatGPT referral 標記與
  OAI-SearchBot、Bing Webmaster Tools AI Performance，以及無記憶反向搜尋，建立
  ChatGPT／AI 引用流量的證據表。當使用者在 GA4 看到 chatgpt.com、要查哪些頁面收到
  ChatGPT 流量、驗證內容是否可能被 AI 搜尋引用或建立 GEO 追蹤時使用；輸入為網域、日期範圍
  與可用平台資料，輸出為已觀測事實、旁證、推論信心與 30 天追蹤表，永遠不宣稱還原原始 prompt。
---

# GA4 ChatGPT referral 倒推來源

## 引導邊界

本 Skill 提供證據分級與調查順序，不假設每個帳號都有相同平台或資料。執行
Agent 應使用現有證據、補查當下官方來源，缺少的資料就降級信心，不硬湊完整答案。

## 適用與不適用

適用：GA4 已看到 `chatgpt.com` 來源、想定位到達頁與互動；檢查 ChatGPT 搜尋的可發現性；
建立可重複的 AI citation 旁證追蹤。

不適用：

- 還原使用者在 ChatGPT 輸入的原始 prompt、完整對話 URL 或個人身分。
- 只靠一次無痕搜尋證明「ChatGPT 一定會引用」或解釋排名機制。
- 把 Bing 的 AI citation、Google AI 搜尋曝光或第三方 bot crawl 當成 ChatGPT 直接證據。
- 在 GA4 未正常收資料時做歸因；先修資料收集與 consent 問題。

## 核心證據分級

| 等級 | 可接受證據 | 可說的話 |
|---|---|---|
| A 直接流量證據 | GA4 工作階段來源含 `chatgpt.com`，並定位到 landing page；OpenAI 官方說 referral URL 自動帶 `utm_source=chatgpt.com` | 「這個頁面收到 ChatGPT referral 工作階段」 |
| B 平台 citation 證據 | Bing AI Performance 顯示某 URL 被支援的 AI surfaces 引用 | 「該頁在 Microsoft/Bing/select partners 的支援範圍被引用」 |
| C 反向觀測 | 無登入／無記憶環境下，ChatGPT 搜尋回答當次列出本站 URL | 「這個測試條件下觀測到引用」 |
| D 推論 | 由 landing page 主題、平台訊號與重複測試推測可能問題類型 | 「最可能的引用情境是……，未確認原 prompt」 |

不要把 B、C、D 升格成 A，也不要把任何等級寫成原 prompt 的證據。

## 開始前輸入

先取得：

1. 網域、GA4 property、property 時區、要分析的起訖日期。
2. 至少一個起始訊號：`chatgpt.com` 工作階段來源、相關 landing page，或 OpenAI UTM referral。
3. GA4 唯讀權限；可選的 Bing Webmaster Tools 與 Search Console 唯讀權限。
4. 要追蹤的互動指標：sessions、engaged sessions、平均 engagement time、key events。
5. 匯出目的地：使用者指定的試算表／CSV；不得包含 client ID、user ID、IP 或事件級個資。

若使用者只提供截圖，要求日期範圍、時區、篩選條件與資料品質圖示一起入鏡，並先遮蔽帳號、
property ID 與任何個資。

## 執行模式

有已授權的瀏覽器或分析 connector 時，agent 直接做唯讀查詢、匯出彙總數字與建立證據表；
不要要求使用者重做 agent 能完成的點擊。沒有存取權時，逐步引導使用者操作，等取得每一步的
實際結果再繼續。不得修改 GA4 property、發布報表、改 robots.txt 或代表使用者登入。

## 四段 SOP

### 1. GA4：定位 ChatGPT 工作階段與到達頁

| 動作 | 為什麼 | 通過判準 |
|---|---|---|
| 開啟 `Reports > Acquisition > Traffic acquisition`，把主維度改為 `Session source / medium`，搜尋 `chatgpt` | Traffic acquisition 是 session scope，適合確認每次造訪來源 | 表中出現 `chatgpt.com` 相關列，且日期與 property 時區已記錄 |
| 加入次維度 `Landing page + query string`；或在 `Reports > Engagement > Landing page` 加 `Session source / medium` 次維度後篩選 `chatgpt` | 把來源連到第一個到達頁，而不是混用任意 page view | 每列有 landing page、sessions 與至少一個 engagement 指標 |
| 檢查右上角 data quality indicator，記錄 threshold、sampling、`(other)` 或資料處理警示 | 標準報表與 explorations 都可能受限制，不能假設換報表就繞過 | 警示狀態寫入證據表；有警示時把數字標成受限 |
| 若找不到資料，擴大日期範圍並等待 GA4 一般處理時間後重查；仍無資料就記為「未觀測」 | 低量、處理延遲、篩選或 consent 都可能造成差異 | 只在實際看到列時宣稱 referral；空白不等於沒有流量 |

**不得再使用的說法**：「探索被 threshold 擋時，改標準報表就能繞過」。Google 官方明確說
reports 與 explorations 都可能受 data threshold。標準報表可作交叉檢查，但不是保證繞過。

### 2. OpenAI：驗證可追蹤性與搜尋 crawler

| 動作 | 為什麼 | 通過判準 |
|---|---|---|
| 在 GA4 檢查 session source 是否為 `chatgpt.com`，並在可用的 URL／campaign 維度確認 `utm_source=chatgpt.com` 訊號 | OpenAI 官方說 ChatGPT 搜尋 referral URL 會自動帶此 UTM | 把 UTM 或 session source 記為直接流量證據；沒看到就不補造 |
| 讀取網站公開 `robots.txt`，確認 `OAI-SearchBot` 未被阻擋 | OpenAI 指出允許此 crawler 有助內容被 ChatGPT 搜尋發現、摘要與引用 | 記錄檢查日期與 allow/disallow；不自行修改 robots.txt |
| 將 `GPTBot` 與 `OAI-SearchBot` 分開記錄 | OpenAI 將潛在訓練控制與搜尋可發現性分開 | 報告不以 GPTBot 狀態推論搜尋引用，也不以 OAI-SearchBot 推論訓練 |

允許 crawler 只代表技術可發現性，不保證抓取、索引、引用或流量。

### 3. Bing Webmaster Tools：讀 AI Performance，但限制證據範圍

| 動作 | 為什麼 | 通過判準 |
|---|---|---|
| 開啟 Bing Webmaster Tools 的 `AI Performance`；若帳戶尚未顯示，記錄 public preview 未可用 | 2026 功能提供 AI citation 與 cited pages 等聚合訊號 | 記錄介面可用性、日期範圍與資料是否為 sample |
| 匯出 total citations、cited pages、page-level citation activity 與可見的 grounding queries | 這些是 Microsoft 官方定義的可觀測欄位 | 每個值保留 URL、日期範圍與匯出日期，不補缺值 |
| 將平台欄標成 `Microsoft Copilot / Bing AI summaries / select partners` | 官方支援範圍不是「所有 AI」，也未承諾等於 ChatGPT | 報告明確寫「Bing 平台旁證，非 ChatGPT 直接證據」 |

Bing Webmaster Tools 的 crawl / Site Explorer 是 Bingbot 的索引與抓取資料，不會替你顯示
`ClaudeBot` 或 `PerplexityBot` 的伺服器存取紀錄。要查第三方 crawler，必須在有合法權限的自家
server/CDN logs 依 user-agent 查證；沒有 logs 就標「不可觀測」。

### 4. 無記憶反向驗證：觀測可重現性

| 動作 | 為什麼 | 通過判準 |
|---|---|---|
| 使用無痕／全新 browser profile，登出 ChatGPT，清除先前對話與 memory 影響 | 降低個人化與既有對話污染；不能消除地區、時間與模型差異 | 測試環境、日期、地區／語言與 ChatGPT 模式已記錄 |
| 從 landing page 的問題空間設計 3–5 個不含品牌名、URL 或期待答案的真實問題 | 帶品牌名會變成導航測試，無法反映自然發現 | 每題可由一般使用者自然提出，且沒有提示本站 |
| 明確啟用可搜尋網路並逐題保存回答中的 cited URLs | 只有實際顯示的引用能作當次觀測 | 每題記錄「命中／未命中」、引用 URL、時間與可分享的非敏感證據 |
| 不同日期重複同一測試集，至少形成多次觀測後才談趨勢 | 回答、索引與檢索具有變動性，單次結果不可泛化 | 報告分開列每次觀測，不用單次命中計算不存在的引用率承諾 |

這仍是黑箱輸出觀測。即使命中，也只能知道「這次回答引用某 URL」，不能知道真實使用者曾輸入
什麼，不能證明所有使用者都會看到同一來源。

## 明確產出：30 天證據表

每列保留：

```text
observed_at | source_surface | evidence_grade | date_range | landing_or_cited_url |
sessions_or_citations | engagement | test_query_category | result | limitations | evidence_link
```

- `test_query_category` 寫問題類型摘要，不把推測冒充原 prompt。
- `sessions_or_citations` 保留平台原始定義；不要把 GA4 sessions 與 Bing citations 相加。
- `evidence_link` 只放使用者有權限的內部證據位置；不要建立公開分享連結。

通過判準：每個結論可回指至少一列，且句子使用與證據等級一致的「觀測／旁證／推論」措辭。

## 停止條件與排錯

- GA4 沒有資料品質圖示、日期或時區資訊：停止比較數字，先補齊查詢脈絡。
- Reports 或 Explorations 顯示 threshold：不得宣稱另一介面保證繞過；擴大日期、移除 demographic／audience 維度，或在已設定且有權限時評估 BigQuery 匯出。
- GA4 空白但 OpenAI UTM 已知存在：檢查 tag、consent、redirect 是否保留 query、日期處理延遲；結果仍只寫「GA4 未觀測」。
- Traffic acquisition 找不到：GA4 collection 可被自訂；請有 Editor 權限者加回報表，或用 Explore 建相同 session-scope 維度。不要擅自更改 property。
- Bing AI Performance 不可用或無資料：記為 public preview 未可用／未觀測，不改用 crawl stats 假裝 AI citation。
- 反向測試沒有引用：記為當次未命中，不等於網站永遠不會被引用。
- 任何步驟要求 prompt、使用者 ID、IP 或事件級個資：停止蒐集，改用彙總資料。

## 完成定義

- GA4 已列出日期、時區、`Session source / medium`、landing page、sessions 與資料品質狀態。
- OpenAI crawler／UTM 檢查有日期與可觀測結果，沒有把 crawler allow 寫成引用保證。
- Bing 結果只歸因到官方支援的 Microsoft/Bing/select partners surfaces。
- 無記憶測試保存題目類型、環境與每次 cited URL；未把單次結果泛化。
- 每個結論標 A–D 證據等級；推論與事實分開。
- 最終明示：**原始 prompt 永遠無法由這套方法還原**。

## 安全與侷限

- 全程採唯讀、最小權限；不要索取密碼、cookie、API key 或 GA4 client/user ID。
- 匯出與截圖先去識別；不要把分析資料上傳到未授權的第三方服務。
- HTTP `Referer` 可能因 referrer policy、瀏覽器、app webview、redirect 或使用者設定而缺失或只剩 origin；沒有 referral 不能證明沒有 ChatGPT 點擊。
- `utm_source=chatgpt.com` 是 OpenAI 對 ChatGPT 搜尋 referral 的官方標記，但實際 GA4 歸因仍受標記保留、tag 與 consent 影響。
- Bing AI Performance 是聚合且可能抽樣的 public preview；citation 不代表排名、權威或在回答中的位置。
- 無痕模式只能降低個人化污染，不能固定模型版本、索引、地區、語言或時間差異。

## 來源與時效

以下皆為一手官方文件，於 **2026-08-02** 查證：

- Google Analytics：Traffic acquisition report 及 session 維度：https://support.google.com/analytics/answer/12923437
- Google Analytics：Landing page report 與來源次維度：https://support.google.com/analytics/answer/12931766
- Google Analytics：reports / explorations data thresholds：https://support.google.com/analytics/answer/9383630
- Google Analytics：Explorations 的 sampling 與 threshold：https://support.google.com/analytics/answer/7579450
- OpenAI：Publishers and Developers FAQ（`OAI-SearchBot`、`utm_source=chatgpt.com`）：https://help.openai.com/en/articles/12627856-publishers-and-developers-faq
- Microsoft Bing：AI Performance public preview 與支援範圍：https://blogs.bing.com/webmaster/February-2026/Introducing-AI-Performance-in-Bing-Webmaster-Tools-Public-Preview
- Bing Webmaster Tools：Site Explorer 是 Bing 抓取／索引資料：https://www.bing.com/webmasters/help/site-explorer-c680da37
- W3C Referrer Policy 規格：https://www.w3.org/TR/referrer-policy/
- 獨立 repo README：https://github.com/Coolkidlab-Yin/ga4-chatgpt-referral
