---
name: threads-bot-builder
description: >
  引導使用者規劃或在既有 repo 實作一個人在迴路、可 dry-run、可去重的
  Threads 發文或回覆 bot。當需求涉及 Threads API 憑證、排程、內容來源、
  草稿批准、兩段式發布、token 維護或發文故障時使用；內容題材與技術棧不限，
  由執行 Agent 依使用者環境補完。
---

# Threads bot 建造器

## 定位：提供判斷框架，不代替執行 Agent

這份 Skill 不列完所有 bot 類型，也不生成一套人人相同的專案。先找出需求的
不變結構、風險與驗收方式，再由執行 Agent 讀現有 repo、查當下官方文件，
選擇合適的語言、儲存、排程與通知方式。

只保留一個作者實跑案例供校準。要看平台憑證與 API 邊界時讀
[platform-setup.md](references/platform-setup.md)；需要填寫範例時讀
[recipes.md](references/recipes.md)。

## 先選工作模式

- **教學規劃**：產出決策、架構、風險、分階段驗收；不聲稱已改 repo。
- **repo 實作**：先讀專案規範與現有程式，再逐階段修改、測試與回讀。

未明確要求實作時先做教學規劃。無論哪種模式，真實發文都屬外部副作用：
先完成 dry-run，顯示帳號、完整草稿與來源，再取得當次發布批准。

## 開始前的輸入與執行契約

先確認下列欄位；使用者已提供的不要重問：

1. 目標帳號與受眾。
2. 內容來源、觸發方式、時區與頻率。
3. 去重鍵、人工判斷點、可接受的跳過條件。
4. 語氣、推廣揭露、敏感主題與禁止事項。
5. 現有 repo、執行環境與可用能力：shell、網路、互動提問、排程、
   secret store、瀏覽器。

型態選項只用來幫助思考，不是完整目錄。可舉「存稿排程、事件快訊、
長文改寫、互動回覆」四例，並永遠保留「其他」。將答案收斂成：

> 目標｜來源｜觸發｜去重鍵｜人工 gate｜紅線

不要假設一定有特定 Agent 的提問或排程工具。能互動就直接問；背景執行時，
建立 pending draft 並通知使用者，沒有批准就停。排程依序評估既有工具、
作業系統排程、CI/雲端排程、可重複的手動命令。

Credentials 只確認名稱與是否備妥，不收值：
THREADS_ACCESS_TOKEN、THREADS_USER_ID；需要 server-side token 交換時才加
THREADS_APP_SECRET。建立空白 .env.example，實值放 secret store 或環境變數。

## 預期產出

由執行 Agent 依 repo 慣例決定檔名，但責任必須可辨識：

~~~text
config          # 帳號、時區、來源、紅線；不含 secret
source adapter  # 取材並保留來源時間
workflow        # 狀態機與 approval gate
publisher       # 唯一能呼叫 Threads API 的邊界
state store     # 去重、lease、發布狀態
drafts/logs     # 草稿、決策與遮罩後的 API 結果
tests           # 去重、重入、錯誤分類與 dry-run
~~~

每個 run 至少記錄 run_id、來源與資料時間、內容 hash、目標時段、決策、
草稿路徑、狀態、HTTP/平台錯誤分類、container/publish id 與重試次數；
不得記 token、App Secret、Authorization header 或不必要的私人內容。

## 引導流程

### 1. 定義最小可用流程

把流程寫成「觸發 → 取材 → 去重 → 草稿 → 人工 gate → 發布 → 回讀」。
執行 Agent 依使用者情境補上取材與寫稿方法；素材不足、來源過期、品質不合格
或使用者選擇跳過時，結束為 skipped，不要硬湊內容。
若來源本來就是使用者寫好的存稿，草稿階段只做必要的格式與安全檢查，
不得強迫重寫或接 LLM。

**通過判準**：每一步都有輸入、輸出、停止條件與下一狀態。

### 2. 建立狀態與冪等

建議狀態：

~~~text
discovered -> drafted -> pending_approval -> approved -> publishing -> published
                                  \-> skipped / failed
~~~

用 account + scheduled_slot + content_hash 或等價業務鍵防止排程重疊與人工
重跑造成重複發布；以原子 claim/lease 處理並行。--force 只可略過內容門檻，
不可略過去重、安全、配額或批准。

**通過判準**：同一素材連跑兩次只產生一次可發布動作；worker 重啟可續跑。

### 3. 實作平台 adapter

需要憑證、權限、create/publish、token 與錯誤分類時，完整讀
[platform-setup.md](references/platform-setup.md)。API 參數以執行當下官方文件
為準，不從記憶猜 reply、版本或配額。

所有請求設 timeout；先檢查 HTTP、content type 與 JSON error，再讀 id。
只對官方定義或可證明的暫時性錯誤做有限次 exponential backoff；
不可用固定 sleep 2 當成功證據，也不可對 4xx 永久錯誤盲重試。

**通過判準**：mock 涵蓋 timeout、非 JSON、4xx、5xx、缺 id、暫時未就緒、
永久失敗與重試上限。

### 4. 接上排程與人工 gate

先以排程器的實際身分跑 dry-run，驗證工作目錄、時區、PATH、secret 與單例鎖。
沒有互動能力時：

1. 寫入 drafts/run-id.md 與 pending_approval 狀態。
2. 通知只帶 run id、預覽位置、到期時間與明確續跑入口，不帶 secret。
3. 續跑時以 run id 讀回同一草稿，重新驗來源時效、批准、token 與冪等鍵。
4. 沒有通知管道時安全停在 pending，提供可列出待審草稿的命令或介面。

發布前再次讀取來源並顯示資料時間、確切帳號、完整草稿、揭露與來源；
批准只適用這一篇，不延伸到後續內容。

**通過判準**：dry-run 不呼叫 create/publish；兩次重疊觸發只有一個取得 lease。

### 5. 做回讀與復原

發布成功不能只看命令 exit code。保存平台回傳 id，並以 API 或 Threads UI
確認內容可見。token 刷新、權限失效、配額、來源抓取與發布錯誤都要告警，
訊息只含 run id 與遮罩後分類。

**通過判準**：可從 log 追到每次 skip、failure 或 publish；失敗後不會靜默停發。

## Dry-run 與批准 gate

dry-run 可讀公開來源、去重、寫稿與產生 would_publish payload，但不得呼叫
平台 create/publish。顯示預估 API/模型成本與所有外部資源需求。

只有使用者明確批准「以這個帳號發布這一篇」後，才可做一次真實 smoke。
沒有批准時，完成說法只能是「完成至 dry-run」。

## 故障、安全、隱私與限制

- 最小化權限；App Secret 只在 server-side；.env 必須 git-ignore。
- 只處理有權使用的來源；推廣、AI 參與與商業關係依情境誠實揭露。
- 互動回覆遇到爭議、騷擾、敏感個資或不確定語境時轉人工，不自動猜。
- retention、刪除、成本上限與停用開關要在上線前定義。
- 固定頻率不是必發承諾；安全停止與安靜跳過是正常成功狀態。

常見故障先依序查：排程是否真的觸發 → 來源與時效 → 去重/lease →
approval → token/權限 → create container → publish/回讀。保留原始錯誤分類，
不要在沒有證據時重建 container 或重送內容。

## 完成定義

- **教學規劃**：需求行、架構、credential 名稱、外部副作用、逐步 gate、
  dry-run、錯誤處理、成本/隱私與驗收方式齊全。
- **repo 實作**：測試與 scheduler 身分 dry-run 通過；去重、並行、錯誤分類、
  token 告警有證據。只有經批准的一篇在 UI 可見且可由 publish id 追蹤，
  才能說全線完成。

## 官方來源與時效

平台 UI、API version、權限、配額與 token 規則會改。實作前完整讀
[platform-setup.md](references/platform-setup.md)，重查其中官方連結並把查證日期
寫進交付紀錄；來源內容每次發布前也要重新抓取，不把舊快取冒充最新資訊。
