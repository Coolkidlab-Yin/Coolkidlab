# LINE bot 案例與填寫方式

案例用來校準架構，不代表每個 LINE bot 都要有相同資料表、部署或指令。

## 空白決策卡

| 欄位 | 要回答的問題 |
|---|---|
| 目標 | 誰要在 LINE 裡完成哪個工作？ |
| Inbound | 需要收訊息嗎？純推播就不要建 webhook。 |
| Outbound | 哪些事件主動發、誰收、送達失敗怎麼處理？ |
| 狀態 | 是否多輪、可取消、會過期？ |
| 資料 | 最少要存什麼，誰可讀，何時刪？ |
| LLM | 規則是否足夠？哪些欄位允許傳第三方？ |
| 風險 | 個資、緊急性、額度、轉人工與備援是什麼？ |

## 原作者實跑案例：家族行程提醒

作者家中實際使用過的版本。可信價值在提醒重複、資料庫差異與 onboarding
等故障，不是要求別人使用同一技術棧。

| 欄位 | 決策 |
|---|---|
| 目標 | 家人在 LINE 建行程，指定對象於到點前收到提醒 |
| Inbound | 一句話直建；長輩另有引導式多輪流程 |
| Outbound | cron 撈到期 delivery，逐收件人 push |
| LLM | 不用；固定指令以規則與狀態機處理 |
| 資料 | family、membership、event、recipient、conversation、outbox |
| Onboarding | 第一人建立家庭，其餘使用邀請流程加入 |
| 原始技術 | FastAPI、SQLite 開發、Postgres 正式環境、外部 scheduler |

已驗證且需保留的教訓：

1. 一個 event 的 notified flag 無法表示多位收件人的部分成功。
2. 正確做法是逐收件人 delivery；只重試暫時失敗者，成功者不重送。
3. scheduler endpoint 需要驗證、重放防護與原子 claim。
4. SQLite 與 Postgres 的型別、transaction、lock 語意要各自測試。
5. 使用者第一次成功體驗比長篇指令說明更重要。
6. 官方自動回覆可能遮蓋自訂 bot 回覆，需在 inbound smoke 時檢查。

換成客服、預約、打卡、內部工具或純通知時，只沿用決策卡與可靠性 gates；
路由、schema、UI 元件與部署由執行 Agent 依真實需求補完。
