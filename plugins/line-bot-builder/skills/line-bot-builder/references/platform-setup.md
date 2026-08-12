# LINE 平台設定與安全邊界

只在需要 LINE channel、webhook、signature 或訊息 API 時讀本檔。

## 憑證陪走

先完整讀 [browser-setup.md](browser-setup.md)，選定現有瀏覽器、官方安裝分流或
逐步口述 fallback。瀏覽器連線 smoke 通過後，再陪使用者進入 LINE Developers
Console。

這一關先判斷是否真的需要 inbound webhook。純推播只建立必要的 channel 與
access token；要收訊息才設定公開 HTTPS webhook、Use webhook 與 channel
secret。帳密與驗證碼由使用者輸入；建立 Provider／channel、接受條款、發行或
重發 token／secret、開啟 webhook 及修改預設自動回覆，都要在點擊前取得當次
批准。每取得一項 credential，只做遮罩後 read-back 並直接存入環境變數或
secret store。同一步失敗三次就停止猜測，改查當下官方文件與實際畫面。

關閉會遮蓋 bot 回覆的預設自動回覆，只在實際需要時修改。

純推播只需要可發訊息的 channel access token 與合法 recipient；不需要 webhook。
要收訊息時才設定公開 HTTPS webhook、啟用 Use webhook、取得 channel secret，
並用 Verify 加上手機真實訊息做雙重 smoke。

## Webhook signature

使用官方 SDK 的驗簽工具優先。必須對收到的原始 UTF-8 request body 與
x-line-signature 做 HMAC-SHA256 驗證，不能先 parse、重排 JSON、改換行或轉碼。
LINE 不公開固定來源 IP；不能以 IP allowlist 取代 signature。

Verify 可能傳送 events 為空的 POST；合法簽章且格式正確時快速回 200。
實際事件用 webhookEventId 或官方穩定鍵做 unique 去重，耗時工作非同步處理。

## Push 與 retry

對支援的 push/multicast/narrowcast/broadcast 端點，第一次請求就產生並保存
X-Line-Retry-Key；timeout 或 5xx 才用相同 key、相同 recipient、相同內容做
exponential backoff。2xx、409 或一般 4xx 不重試；409 代表同 key 已被接受。

retry key 只能避免重複接受，不保證終端使用者一定收到。逐收件人 outbox、
provider request id、dead letter 與其他關鍵通知備援仍然需要。

## 官方來源（查證：2026-08-02）

- [LINE：Build a bot](https://developers.line.biz/en/docs/messaging-api/building-bot/)
- [LINE：Receive messages](https://developers.line.biz/en/docs/messaging-api/receiving-messages/)
- [LINE：Verify webhook URL](https://developers.line.biz/en/docs/messaging-api/verify-webhook-url/)
- [LINE：Verify webhook signature](https://developers.line.biz/en/docs/messaging-api/verify-webhook-signature/)
- [LINE：Retry failed API requests](https://developers.line.biz/en/docs/messaging-api/retrying-api-request/)
- [LINE：Messaging API reference](https://developers.line.biz/en/reference/messaging-api/)

每次實作或上線前重查 SDK、訊息格式、支援 retry key 的端點、rate limit、
價格與方案，並把查證日期寫進交付紀錄。
