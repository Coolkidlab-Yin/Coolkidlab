---
name: line-bot-builder
description: >
  引導使用者規劃或在既有 repo 實作一個可靠、可驗證的 LINE Messaging API
  bot。當需求涉及客服、預約、提醒、內部工具、純推播、webhook 驗簽、
  對話狀態、逐收件人去重、排程或 LINE 憑證故障時使用；用途與技術棧不限，
  由執行 Agent 依現場需求補完。
---

# LINE bot 建造器

## 定位：先選必要元件，再由 Agent 補完

這份 Skill 不列完所有 LINE bot 可能，也不強迫每個專案都有 webhook、LLM、
資料庫或 UI 元件。它只提供決策順序、可靠性底線與完成證據。執行 Agent 應讀
現有 repo 與官方文件，選擇使用者真正需要的最小元件。

需要 LINE 憑證、webhook、signature 或 retry key 時讀
[platform-setup.md](references/platform-setup.md)；需要可信案例時讀
[recipes.md](references/recipes.md)。

## 先選工作模式

- **教學規劃**：交付需求卡、元件圖、資料流、風險與驗收，不假裝已建立服務。
- **repo 實作**：讀規範與現有程式，逐階段實作、測試、dry-run、部署回讀。

未明確要求改 repo 時先規劃。建立 LINE channel、公開 webhook、建立雲端資源、
升級付費或對真實使用者 push 都是分開的外部副作用；各自在發生前取得批准。

## 開始前的輸入與執行契約

確認下列欄位，已提供的不要重問：

1. 使用者是誰，bot 要完成哪個工作。
2. 是否接收訊息、是否主動推播；純推播型不需要 webhook。
3. 輸入/回覆型態、多輪流程、歧義與轉人工策略。
4. 要保存的最小資料、敏感程度、retention 與刪除方式。
5. 是否需要 LLM，以及哪些欄位會傳到第三方。
6. 時區、排程、送達期望、失敗/死信政策與可接受延遲。
7. 現有 repo、語言、DB、部署、secret store 與通知能力。

例子只用來打開思路：客服、預約、提醒、純通知；永遠保留「其他」。將答案
收斂成：

> 目標｜使用者｜收訊息？｜主動推播？｜資料｜LLM？｜風險

### LLM 決策

固定指令、表單式預約、狀態查詢與通知通常先用 deterministic rule/state
machine。只有自由問法或長尾知識真的需要時才接 LLM，並先定義 grounding、
fallback、延遲、成本、個資遮罩與人工轉接。常見折衷是主流程走規則，
LLM 只處理規則接不住且允許傳出的內容。

Credentials 只確認名稱與是否備妥，不收值：
LINE_CHANNEL_ACCESS_TOKEN；有 inbound webhook 才需要 LINE_CHANNEL_SECRET。
資料庫、cron 或 LLM credential 依架構補充。建立 .env.example 空欄位，
實值放環境變數或 secret store。

## 預期產出

檔名依 repo 調整，但責任需清楚：

~~~text
config             # 時區、政策、資料保留；不含 secret
api/webhook        # 有收訊息才建立；raw body 先驗簽
domain/router      # keyword/state/rule/fallback
domain/dialog      # 需要多輪才建立，可取消、可 timeout
delivery/outbox    # 主動推播才建立，逐收件人狀態
workers/scheduler  # claim、lease、retry、dead letter
storage/migrations # 只有需要持久資料才建立
logs/tests         # 遮罩 log、安全與可靠性證據
~~~

log 保存 request/run/event/delivery id、狀態、耗時、provider request id 與遮罩錯誤；
不記 channel secret/token、完整訊息、邀請碼或不必要的 LINE user id。

## 引導流程

### 1. 選最小元件與資料流

依需求選元件，不照抄全套：

- **純推播**：recipient/內容來源 + outbox + publisher + scheduler；跳過 webhook。
- **收訊息**：webhook + signature + event idempotency + router。
- **多輪流程**：再加可取消、可逾時的 state machine 與草稿資料。涉及時段、
  庫存等有限資源時，最終確認必須用 transaction、唯一約束或等價的原子操作；
  不可把草稿狀態當成預約成功。
- **主動推播**：再加逐收件人 outbox、claim/lease、retry/dead letter。

畫出資料如何進入、在哪裡驗證、保存什麼、何時產生副作用、如何刪除。

**通過判準**：每個元件都有需求理由；純推播方案不被 webhook Verify 阻擋。

### 2. 實作 inbound webhook（只有收訊息才做）

完整讀 [platform-setup.md](references/platform-setup.md)。在 JSON parse 前以原始
body 與 x-line-signature 驗簽；缺失或錯誤立即拒絕。使用 webhookEventId 或
官方穩定事件鍵去重，快速入列後回 2xx；接受官方 Verify 可能送來的空 events。

**通過判準**：測試正確/錯誤/缺失 signature、被修改 body、duplicate event、
空 events 與耗時工作不阻塞回應。

### 3. 實作路由與狀態

優先處理明確命令與取消，再查對話狀態，接著做規則解析，最後才進 fallback。
歧義不落正式資料；多輪草稿要有 owner、expiry 與取消路徑。介面元件由 Agent
依使用者與當下 LINE 規格選，不在 Skill 窮舉 JSON 模板。預約或客服若有有限
選項，至少評估 quick reply、卡片、圖文選單或等價元件；若仍採純文字，
要用真實使用者 smoke 證明不會讓人猜格式。

**通過判準**：正常、歧義、取消、timeout、越權、重複事件與跨使用者狀態皆測試。

### 4. 實作逐收件人 outbox（有主動推播才做）

不要用一個全域 notified flag 代表所有人成功，也不要因部分失敗重送整批。
每個 recipient/delivery 一列，具有唯一 idempotency key 與狀態：

~~~text
pending -> leased -> sent
                  -> retry_wait -> dead_letter
~~~

同一 transaction 產生業務資料與 outbox；worker 原子 claim 並設 lease。
成功者不重送，只有暫時失敗者用相同 provider retry key 做 bounded backoff；
永久 4xx 直接 dead-letter。LINE 支援 retry key 的端點才使用。

**通過判準**：三位收件者分別成功、timeout、永久 4xx 時，成功者只收一次，
timeout 者可安全重試，永久錯誤者進 dead-letter；兩個 worker 不重複 claim。

### 5. 保護 scheduler/worker

公開派送端點需驗證、限制重放並做單例/lease；不要只靠猜得到的固定 header。
若採 HMAC，簽入 method、path、body hash、timestamp、nonce，限制 clock skew，
nonce 保存至窗口過期。若 scheduler 平台有更合適的身分驗證，Agent 可替換，
但要保留同等 replay 與 least-privilege 保護。

**通過判準**：缺失、錯誤、過期、nonce replay、並行 cron 與 worker crash
皆有測試；過期 lease 可恢復。

### 6. 部署、資料與營運

依持久性需求選資料庫；不要把正式資料放 ephemeral filesystem。SQLite 可做
本機驗證，正式環境若需並發/持久化，使用符合需求的資料庫並測真實語意，
不要假裝兩者鎖定完全相同。

以部署與 scheduler 實際身分做 health + dry-run；驗證 secret、時區、cold
start、timeout、備份與 restore。免費方案與額度只可當當下選項，不用 ping
繞過服務限制。

**通過判準**：restart、DB timeout、LINE timeout/429、過期 lease 與 restore
能恢復或告警。

## Dry-run、批准與 smoke

先用 fake LINE adapter 跑 end-to-end：fixture → 驗簽/路由 → 業務 transaction
→ 每位收件人 outbox → claim → fake response。輸出 would-send 與 delivery
狀態，不呼叫 LINE、不建立公開資源。

若要公開 endpoint、建立 channel/雲端資源或可能計費，先顯示 provider、
region、方案、URL 與資料類型。對真實帳號的 smoke 只送一次批准訊息；
沒有批准就標示「完成至 dry-run」。

## 安全、隱私、成本與限制

- webhook 驗簽不是選配；驗證原始 body，不先 parse。
- 最小化 LINE subject id、對話、預約與個資；預設不保存 raw webhook。
- 會存顧客個資時，逐欄列出用途、可讀角色、保存期限、刪除/更正入口與備份
  retention；沒有用途的電話、地址或完整對話不得落庫。
- LLM 只收到已同意且最小化的欄位；敏感業務要有轉人工與刪除流程。
- LINE push 不是緊急通訊保證；醫療、災防或保證送達需求需其他備援。
- 執行時查官方價格、rate limit 與方案，再用使用者數 × 推播量 × 重試率估價。

常見故障依序查：channel/環境 → webhook URL（若需要）→ raw body signature →
event idempotency → router/state → outbox/lease → provider response/retry key。
不要用整批重送掩蓋單一收件人失敗。

## 完成定義

- **教學規劃**：需求卡、最小元件、資料/信任邊界、credential 名稱、
  dry-run、可靠性、成本/隱私與逐步驗收齊全。
- **repo 實作**：相關測試、部署身分 dry-run、signature/idempotency、
  逐收件人 partial failure/retry、cron replay/concurrency、刪除與 recovery
  有證據。只有經批准的一次真實 smoke 收到且不重送，才算全線完成。

## 官方來源與時效

LINE Console、SDK、訊息格式、retry、額度與方案會改。實作前完整讀
[platform-setup.md](references/platform-setup.md)，重查官方連結並記錄日期；
不要把作者的免費方案或單一家庭規模當成普遍保證。
