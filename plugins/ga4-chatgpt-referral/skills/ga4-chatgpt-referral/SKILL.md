---
name: ga4-chatgpt-referral
description: >
  GA4 看到 chatgpt.com referral 之後的倒推來源 SOP。當使用者說「GA4 出現
  chatgpt.com 的流量」「想知道 ChatGPT 為什麼引用我的文章」「想追蹤 AI
  引用流量」,或在做 GEO(生成式引擎優化)歸因、想驗證自己的內容有沒有
  被 ChatGPT / AI 搜尋引用時使用。核心是 4 招免費工具側面推導:GA4 探索
  報表、GSC 反向、Bing Webmaster Tools、反向 ChatGPT 無痕驗證。
---

# GA4 ChatGPT referral 倒推來源(ga4-chatgpt-referral)

## 什麼時候用

- GA4 報表突然出現來自 `chatgpt.com` 的 referral,想知道「對方在 ChatGPT 問了什麼才被導過來」
- 想建立一套持續追蹤「哪些內容被 AI 引用」的免費工具流
- 在做 GEO 歸因:想倒推自己的哪些主題容易被 ChatGPT 搜尋引用

適用對象是非工程師也能跑的免費工具組合(GA4 + Google Search Console + Bing Webmaster Tools + ChatGPT 本身),不需要付費分析工具。

## 原理:referral 能告訴你什麼、不能告訴你什麼

**能告訴你的**:瀏覽器送出的 HTTP Referer header 會讓 GA4 知道這筆流量「來自 chatgpt.com」,搭配到達網頁維度,可以知道 AI 來的訪客落在哪一頁、停多久、觸發了哪些事件。

**不能告訴你的**:瀏覽器的 Referrer-Policy 預設是 `strict-origin-when-cross-origin` —— 跨站只傳 host(chatgpt.com),沒有完整 path、沒有 query。這是業界標準,**拿不到也繞不過**,你永遠看不到使用者在 ChatGPT 裡問了什麼 prompt。

所以這套 SOP 做的是**側面推導**,不是直接觀測。帶使用者操作時,不要承諾「找出那個 prompt」,只能承諾「縮小範圍、推出最可能的引用情境」。

另外,chatgpt.com referral 跟一般 referral 技術上完全一樣(都是 HTTP Referer header)。差別在「來源是 AI 對話」這件事改變了優化策略 —— 不能像 Google search 那樣盯 keyword,要倒推「ChatGPT 為什麼引用我」,常見關聯因素是 quotable block、FAQPage schema、數字精確且有來源標註。

## 開始前先問環境

依序確認,缺哪個就先補哪個:

1. GA4 是否已正常收資料
2. 有沒有接 Google Search Console
3. Bing Webmaster Tools 註冊了沒

確認完再進 SOP,每做完一招停下來跟使用者確認結果,再進下一招。

## 4 招 SOP

### 招一:GA4 探索報表 —— 看 AI 訪客落在哪頁

GA4 → 探索 → 建空白報表:

- **維度**:工作階段來源/媒介、到達網頁、事件名稱
- **指標**:工作階段、平均參與時間
- **篩選**:「工作階段來源/媒介」完全比對 `chatgpt.com / referral`

跑出來就能看到每一筆 AI 來的訪客落在哪一頁、停多久、觸發哪些事件。

**流量小的站注意**:單筆(或極少量)referral 在探索報表會被 GA4 的隱私閾值直接擋成「無資料」。遇到這情況不要去 debug 篩選條件 —— 改走**標準報表:報表 → 客戶開發 → 流量開發**,搜尋 `chatgpt`,就能繞過閾值看到資料。

### 招二:Google Search Console 反向 —— 推哪些主題容易被引用

用 `site:` 加上使用者的網域,搭配曾出現 AI Overviews 的查詢,反推哪些主題容易被 AI 引用。這招看的是「Google 端的 AI 露出訊號」,跟 chatgpt.com referral 不是同一條管道,只能當旁證。

### 招三:Bing Webmaster Tools —— ChatGPT 搜尋的資料源

ChatGPT 搜尋的資料源大半來自 Bing,所以 Bing 端的收錄與爬取狀態是重要訊號:

1. 註冊 Bing Webmaster Tools
2. 用 **Import from GSC** 把 Search Console 資料匯入(不用重新驗證網站)
3. 等收錄後,看 crawl stats

Bing 的 crawl stats 還能看到「哪個 bot 抓了哪頁」—— 包括 ClaudeBot(Anthropic 爬蟲)、PerplexityBot 這些 AI 爬蟲,因為它們會被 Bing 的 search index pipeline 看到。Google Search Console 看不到這份資料,Bing 反而有。

### 招四:反向 ChatGPT 驗證 —— 自己扮演路人查一次

反過來自己用 ChatGPT 的搜尋模式,下「真實使用者會問的問題」,看回答的引用來源有沒有使用者的網域。

操作紅線(每一條都會讓結果失真,帶使用者跑時要主動提醒):

- **一定要開無痕視窗**。平常登入著 ChatGPT,memory 會記得你是誰、偏好你的站,結果失真。
- **query 不帶品牌名**,要像真的路人在問。
- **用會觸發 retrieval 的 prompt**,例如「`<主題>` latest research 2026」「`<關鍵字>` case study with sources」。ChatGPT 只有在用 web search 時才會引用來源,純對話模式不會。
- **連續測幾週看趨勢**。單次命中或沒中都不準。

### 收尾:30 天追蹤

四招建完不是結束。把每筆 chatgpt.com referral 的「日期、到達網頁、停留時間」記成一張簡單的表(試算表就夠),累積 30 天後回頭看:哪些主題被 AI 持續引用、哪些只中過一次。持續被引用的主題就是「AI 覺得你可信的領域」— 下一批內容往那裡加碼,比猜題有依據。

## 我踩過的坑

1. **想抓使用者的 prompt 或完整網址** —— Referrer-Policy 的限制,拿不到也繞不過。別浪費時間找繞道,直接做側面推導。
2. **單筆 referral 在探索報表顯示「無資料」** —— 不是設定錯,是隱私閾值。改走「報表 → 客戶開發 → 流量開發」。
3. **登入狀態下做反向驗證** —— ChatGPT memory 會偏向你自己的站,命中了也不代表路人查得到。
4. **query 帶品牌名** —— 等於作弊,測不出自然引用。
5. **單次驗證就下結論** —— 命中或沒中都是雜訊,趨勢才是訊號。

## 誠實邊界(哪些是推測、不是實證)

這一節照實告訴使用者,不要把推測講成事實:

- **「ChatGPT 搜尋資料源大半來自 Bing」是業界普遍認知,不是官方公開的保證**。Bing 端訊號是強旁證,不是引用的直接證據。
- **招二(GSC / AI Overviews)是相關性推導**:某主題出現在 AI Overviews 不等於 ChatGPT 也引用了它,兩個是不同系統。
- **「為什麼被引用」的歸因(quotable block、FAQPage schema、數字精確)是觀察到的關聯,不是經過控制變因的實驗結論**。
- **免費三件套(GA4 + GSC + Bing)的歸因精度是經驗估計**,適合流量小、預算為零的個人站;中大型站或隱私優先的 EU 站,可評估 Plausible 這類付費工具。
- 這整套 SOP 的產出是「最可能的引用情境」,**永遠無法還原真實 prompt**。回報結果時用「推測」「旁證」這類詞,不要寫成「已確認」。
