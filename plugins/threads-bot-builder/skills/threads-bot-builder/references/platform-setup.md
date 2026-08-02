# Threads 平台設定與 API 邊界

本檔只保存容易做錯、且必須對照官方文件的部分。執行 Agent 要依使用者環境
補完程式碼，不照抄過期的 UI 路徑或 API version。

## 憑證陪走

1. 先確認 Agent 是否有可用瀏覽器能力；沒有就採逐步口述，不要求安裝某個
   特定 Agent 的擴充功能。
2. 帳號、密碼、驗證碼由使用者輸入；建立 App、同意條款、產生或重發 secret
   等有外部副作用的按鈕由使用者確認。
3. token/secret 直接存入環境變數或 secret store，不貼進對話、不截完整後台。
4. 同一步找不到三次就停，改讀當下官方文件與畫面文字，不憑記憶猜。

要達成的狀態：

- Threads 帳號與 Meta App 已準備。
- 只發文通常需要 threads_basic、threads_content_publish；需要管理回覆或
  刪文時，再依當下官方文件加最小權限。
- 短期 token 已依官方 server-side 流程換成長期 token。
- THREADS_USER_ID 與帳號已用官方 /me 類端點回讀確認。

## Publisher 契約

Threads 發布是先建立 container，再 publish。publisher adapter 必須：

- 以環境變數讀 token，不把 token 放 URL log。
- 保存 create response 的 container id。
- 檢查 HTTP status、content type 與 JSON error。
- 依官方可觀察狀態輪詢；若該媒體型態沒有狀態端點，只對明確暫時性
  「未就緒」結果做 bounded exponential backoff。
- 超過總 timeout 或遇到永久錯誤就停，不再建立新 container。
- publish 後保存 publish id 並回讀可見性。

回覆、串文或媒體貼文的參數容易改版。需要時當場查官方 Posts/Reply 文件，
不要從本檔或模型記憶猜參數名。

串文逐則保存前一則真實 publish id，確認該則已由平台接受後才建立下一則；
每一則都有 bounded timeout 與同一 run 的 sequence id。不要用猜測的 reply
參數，也不要以本機等待秒數取代平台回應。

若第 N 則失敗，保留已發布項目的 id 並把 run 標成 `partial_failed`，不要刪除或
重發前 N-1 則。只有在平台狀態能證明可安全接續時才自動重試第 N 則；否則通知
操作者已發布連結、失敗序號與原因，由人選擇接續或結束這次 run。

## Token 與 Windows

長期 token 的有效期與可刷新條件以官方文件為準；建立到期前 health job，
刷新失敗就停止發布並告警。App Secret 僅用於 server-side 交換。

Windows 傳繁中文字串時，先以 UTF-8 檔或程式 HTTP client 傳遞並做 round-trip
測試；不要把 shell code page 偶然成功當成可靠方案。

## 官方來源（查證：2026-08-02）

- [Meta Threads API：Posts](https://developers.facebook.com/docs/threads/posts)
- [Meta Threads API：Access tokens and permissions](https://developers.facebook.com/docs/threads/get-started/get-access-tokens-and-permissions)
- [Meta Threads API：Long-lived tokens](https://developers.facebook.com/docs/threads/get-started/long-lived-tokens)
- [Meta Threads API：Troubleshooting](https://developers.facebook.com/docs/threads/troubleshooting)

每次實作或上線前重查以上文件、記錄日期與使用的 API version。數字、scope、
UI 文案或 token 天數只能視為當次查證結果，不當成永久保證。
