---
name: ig-bot-builder
description: >
  引導使用者規劃或在既有 repo 實作一個可預覽、可去重、需人工批准的
  Instagram 圖文發布 bot。當需求涉及 IG 自動發文、圖卡或輪播、內容來源、
  Meta 憑證、公開圖片 URL、container/publish、排程或發布故障時使用；
  主題與技術棧不限，由執行 Agent 依現場需求補完。
---

# Instagram bot 建造器

## 定位：提供骨架，不窮舉用途

這份 Skill 教 Agent 找出選材、圖像、批准、發布與復原的共同結構，不替每個
產業預寫完整解法。列出的新聞、教學、作品、商品只是例子；使用者的真實情境
由執行 Agent 讀 repo、問必要問題、查官方文件後補完。

需要 Meta 憑證、圖片發布或輪播細節時讀
[platform-setup.md](references/platform-setup.md)；需要一個可信填法時讀
[recipes.md](references/recipes.md)。

## 先選工作模式

- **教學規劃**：交付決策卡、架構、風險、成本與驗收，不聲稱已建立 bot。
- **repo 實作**：讀現有程式與規範，逐階段實作、測試、預覽與回讀。

未明確要求改 repo 時先規劃。建立 App、啟用公開圖床、部署、付費與真實發文
是不同外部副作用；每一項都要在發生前顯示影響並取得相應批准。

## 開始前的輸入與執行契約

確認使用者已提供或選定：

1. 帳號、受眾、內容目的與成功指標。
2. 內容來源、授權、freshness 與去重鍵。
3. 圖片來源：自有圖片、程式排版、授權素材或其他。
4. 固定頻率、事件觸發或手動啟動；素材不足時是否安靜跳過。
5. 人工批准點、文案/視覺規則、商業揭露與敏感主題。
6. 現有 repo、語言、部署、儲存、排程與通知能力。

例子只用來打開思路：事件快訊、知識輪播、作品排程、商品更新；永遠保留
「其他」。將答案收斂成：

> 目標｜來源｜圖像策略｜觸發｜去重鍵｜人工 gate｜紅線

不要預設一定需要 LLM、RSS、Pillow、特定圖床或特定模型。素材與文案已存在時，
多加 AI 只會增加成本與故障點。只有候選遠多於發布量時，才考慮低成本篩選與
高能力寫稿分工。

Credentials 只確認名稱與是否備妥，不收值。最小集合通常是
IG_ACCESS_TOKEN、IG_USER_ID；其他模型、儲存或圖床 credential 由 Agent
依實際架構決定。建立 .env.example 空欄位，實值只放環境變數或 secret store。

## 預期產出

檔名依 repo 慣例調整，但責任需分開：

~~~text
config             # 來源、帳號、時區、規則；不含 secret
collector          # 取得素材並保留來源/抓取時間
selector           # 可選；明確規則與跳過理由
renderer           # 圖片處理或現成圖校驗
workflow           # 狀態、去重、approval
media host adapter # 只有平台需要公開 URL 時存在
publisher          # Meta API 邊界
previews/logs      # 預覽、決策、遮罩錯誤
tests              # 去重、輪詢、錯誤、視覺與 dry-run
~~~

每個候選至少保存來源、發布/抓取時間、內容 hash、選擇理由與權利狀態；
每個 run 保存 approval、container id、status history、publish id、HTTP/Meta
錯誤與重試。不得保存 token、私密原圖或完整敏感內容到 log。

## 引導流程

### 1. 定義最小 pipeline

使用「取得素材 → 品質/權利判斷 → 去重 → 文案/圖片 → 人工 gate →
上傳/發布 → 回讀」作為骨架。哪一段可省略由使用者資料決定，不為了完整而
增加無用元件。沒有合格素材時正常結束為 skipped。

**通過判準**：每段都有輸入、輸出、停止條件；Agent 能說明為何需要或省略。

### 2. 建立狀態、去重與節流

用穩定業務鍵加 account/slot/content hash 防重入。建議狀態：

~~~text
collected -> selected -> rendered -> pending_approval -> approved
          -> hosting -> container_ready -> published
          -> skipped / failed
~~~

配額規則至少回答：單次最多幾則、同類冷卻多久、素材不合格時如何安靜、
並行 runner 如何取得原子 lease。--force 不得略過授權、去重、批准或配額。

**通過判準**：同一素材連跑兩次只發布一次；重疊排程不會洗版。

### 3. 驗證視覺與公開圖片邊界

依使用者需求補完 renderer。若圖片含文字，先產生一張代表性預覽並在手機尺寸
檢查字型、裁切、對比與可讀性；若使用自有圖片，檢查尺寸、順序與授權。

平台需要公開 URL 時，先讀 [platform-setup.md](references/platform-setup.md)。
不要把私人或未發布敏感圖片上傳到公開服務。publisher 只接受經核准、能匿名
抓取、回傳正確 MIME、期限足夠的 URL。

**通過判準**：視覺 smoke 與無登入 fetch 都有證據；公開期限涵蓋發布與回讀。

### 4. 實作 Meta publisher

由 platform adapter 隔離登入路線、container、狀態輪詢與 publish。完整讀
[platform-setup.md](references/platform-setup.md)，執行時重查 API version、
scope、媒體限制與配額，不從模型記憶猜。

所有請求設定 timeout；先檢查 HTTP/content type/JSON error；只對官方定義的
暫時性錯誤做 bounded exponential backoff。輪詢要有總 timeout 與 terminal
failure，只有官方可發布狀態才進 publish。

**通過判準**：mock 涵蓋非 JSON、4xx、429、5xx、timeout、缺 id、
處理中後成功與永久失敗。

### 5. 排程、批准與營運

以排程器實際身分跑 dry-run，驗證時區、工作目錄、PATH、secret、字型與單例鎖。
背景環境無法問人時，建立 pending preview 並通知；沒有批准不得建立公開資源、
上傳圖片、建立 container 或發布。

發布前顯示確切帳號、完整圖/輪播、caption、來源、資料時間、揭露、公開託管
期限與成本。批准只適用這一篇。發布後用 publish id 與 IG App 回讀。

**通過判準**：可觀察 runs、skips、approval latency、publish、retry、
token days-to-expiry；告警不含 credential 或完整草稿。

## Dry-run 與批准 gate

dry-run 可真實讀公開來源、選材、去重、寫稿與生圖，但不得上傳公開圖、
建立 Meta container 或發文。輸出 preview、caption、來源、跳過理由、
權利/揭露檢查、預估成本與遮罩後的 would_publish payload。

只有使用者明確批准「以這個帳號發布這一組圖文」後，才能做一次真實 smoke；
沒有批准就標示「完成至 dry-run」。

## 安全、隱私、成本與限制

- 最小化 scope；App Secret 只在 server-side；.env 與 preview 權限需受控。
- 圖片、字型、logo、新聞摘要與人物肖像都要有可用權利。
- 價格、庫存、活動時間與 YMYL 內容在發布前由人複核；不保證結果。
- 定義 raw source、草稿、圖片、帳號識別的 retention 與刪除方式。
- 從官方價格/配額頁估算模型、圖床、儲存、排程與發布成本，不保證免費。

常見故障依序查：來源與 freshness → 去重/lease → renderer/字型 →
公開 URL/MIME → token/IG user id → container status → publish/回讀。
保存原始 error code/type，不把 token 錯誤誤判成一般 HTTP status。

## 完成定義

- **教學規劃**：決策卡、最小 pipeline、credential 名稱、圖片權利、
  dry-run、批准、故障、成本/隱私與驗收齊全。
- **repo 實作**：測試、手機尺寸 visual smoke、無登入 image fetch、
  scheduler dry-run、去重/並行、container polling 與 token/配額告警有證據。
  只有經批准的一篇在 IG App 可見且 publish id 落 log，才算全線完成。

## 官方來源與時效

平台 UI、登入路線、API version、scope、媒體限制、配額與價格會改。實作前
完整讀 [platform-setup.md](references/platform-setup.md)，重查官方連結並記錄
日期；每次發布前重抓來源，超過使用者 freshness window 就跳過。
