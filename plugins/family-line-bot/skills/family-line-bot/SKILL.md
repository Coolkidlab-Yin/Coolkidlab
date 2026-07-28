---
name: family-line-bot
description: >
  家族共享行程提醒 LINE bot 的完整建置教學。當使用者想做 LINE bot、
  行程提醒 bot、家庭共享行事曆機器人,或提到 LINE Messaging API 專案、
  webhook 收訊息、cron 定時提醒、邀請碼加入群組 這類需求時使用。
  涵蓋 FastAPI + Supabase + Render 免費三件套架構、不接 LLM 的訊息
  路由設計、cron 提醒去重、本機 SQLite / 線上 Postgres 同一套 code。
---

# 家族行程提醒 LINE bot(family-line-bot)

## 什麼時候用

- 想做一個給家人用的 LINE bot:一句話建行程、到點自動提醒相關的人
- 想學 LINE Messaging API 的 webhook 收訊息 / push 完整接法
- 想做任何「有限指令集」的聊天 bot,在猶豫要不要接 LLM
- 想知道 cron 每分鐘跑的提醒怎麼不重複發

核心前提:家庭工具的死亡點是「要另外開一個 app」。這個 bot 不另開介面,
直接活在大家本來就整天掛著的 LINE 裡。

## 架構總覽(一句話建行程 + cron 自動提醒)

家人在 LINE 打一句「明天下午 3 點 <家人稱呼> 醫院回診 提前 1 小時提醒」,
bot 用規則解析出時間 / 對象 / 事由 / 提前量,存進資料庫;一個 cron job
每分鐘呼叫派送端點,撈出到點未通知的行程 push 給所有參加的人。

技術棧全免費:

| 元件 | 用什麼 | 免費額度(來源站台實測) |
|---|---|---|
| Web 框架 | Python FastAPI | — |
| 訊息通道 | LINE Messaging API | — |
| 資料庫 | Supabase Postgres | free tier 500MB DB + 50K MAU,家族 5-10 人遠低於上限 |
| 部署 | Render | free tier 750 hr/month,自動 sleep 後 cold start 約 30 秒 |
| 定時觸發 | cron-job.org | 每分鐘打派送端點;另每 14 分鐘 ping 一次保持 Render 不睡 |

關鍵設計決策:**主流程刻意不接 LLM**。家族行程 bot 的指令集很固定
(建行程 / 查行程 / 刪行程 / 提醒),keyword 比對 + 一句話規則解析就能
100% 搞定。好處:零 API 成本、回應即時、行為可預測(LLM 偶爾自由發揮,
長輩會被搞糊塗),也避開把家人輸入的隱私上傳第三方。來源站台實測
regex 解析跑 100 次成功率 95%+;LLM 只當 fallback(regex 抓不到才丟給
輕量模型),而且是選配。判斷「哪裡不用 AI」跟「哪裡用 AI」一樣重要。

## 照步驟做

### 元件清單(照這個順序建)

1. **FastAPI webhook + LINE Messaging API**:收訊息 / push 完整接法
2. **不接 LLM 的訊息路由**:keyword 比對 → 對話狀態機 → 一句話解析 → fallback,照這個順序
3. **一句話建行程的規則解析**:從一句話抓出時間 / 對象 / 事由 / 提前量
4. **引導式新增的對話狀態機**:一步步問標題 → 開始時間 → 結束 → 參加的人 → 提前多久 → 確認;草稿存 conversation_states 表的 JSONB 欄位,中途打「取消」隨時跳出
5. **邀請碼 onboarding**:第一個人建家族當 admin,其他人輸入邀請碼加入當 member
6. **cron 提醒去重**:notify_time + notified flag,push 完立刻標記;partial failure 不重試
7. **cross-db 資料層**:SQLAlchemy + 自訂 TypeDecorator(UUID / JSONB)讓同一套 code 本機跑 SQLite、線上跑 Supabase Postgres;migration 用 Alembic 管

兩種建行程方式並存,對應兩種人:懶人版一句話直建,新手版(長輩用)
打「新增行程」進引導式問答。同一個 bot 不強迫所有人用同一種方式。

### Agent Prompt(整段複製貼給你的 AI agent 就能從零建起來)

> 我要你幫我做一個「家族共享行程提醒 LINE bot」,活在家人本來就在用的
> LINE 裡,不另外開 app。技術棧請用 Python FastAPI 接 LINE Messaging API
> 收訊息與 push,資料庫用 Supabase Postgres,但開發階段我要能在本機跑
> SQLite、上線跑 Postgres 用同一套程式碼,所以資料層請用 SQLAlchemy 加
> 自訂 TypeDecorator 把 UUID 與 JSONB 在兩邊抹平,migration 用 Alembic 管。
>
> 功能我要這些:第一,邀請碼加入家族 — 第一個人建家族當 admin,其他家人
> 輸入邀請碼加入當 member。第二,建行程要兩種方式並存:懶人版用一句話
> (像是「明天下午三點 <家人稱呼> 醫院回診 提前一小時提醒」),請用規則
> 解析出時間、對象、事由、提前量,不要接任何 LLM;新手版用引導式問答,
> 做一個對話狀態機一步步問標題、開始時間、結束、參加的人、提前多久,
> 過程中的草稿存進 conversation_states 表的 JSONB 欄位,中途打「取消」
> 可隨時跳出。第三,提醒用一個 cron job 每分鐘呼叫一次派送端點,撈出
> 提醒時間已過且尚未通知的行程,push 給所有參加的人。
>
> 請務必避開這些我已知的雷:cron 派送端點一定要驗 secret header,防外部
> 亂打;每筆行程要有一個 notified 旗標,push 完立刻標成已通知,不然下一
> 分鐘會重複撈到同一筆狂發;就算 push 給其中一個人失敗也不要重試整筆,
> 只記 log,否則已經收到的家人會被重複轟炸;訊息路由請走 keyword 比對加
> 狀態機加一句話解析加 fallback 的順序,刻意不接 LLM,因為指令集很固定、
> 要回應即時又行為可預測,長輩才不會被搞糊塗。
>
> 開工前請先確認我的環境:我有沒有 LINE 官方帳號與 channel token、
> Supabase 專案、Python 版本、本機要不要先用 SQLite 跑通。然後一步一步建,
> 每完成一步就停下來跟我確認再繼續,不要一次全寫完。

## 我踩過的坑

1. **cron 每分鐘跑,同一筆提醒重複發**:派送端點撈的是「notify_time 已過
   且 notified 還是 false」的行程,push 完必須**立刻**把 notified 標成
   true — 這個 flag 是避免下一分鐘又撈到同一筆的關鍵。
2. **push 部分失敗時不要重試整筆**:就算 push 給其中一個人失敗,也只記
   log,不重試整筆 — 重試會害已經收到的人收第二次。寧可漏記一個,也不要
   全家被疲勞轟炸。
3. **派送端點裸奔**:cron 打的 `/api/cron/dispatch` 一定要驗 secret
   header,防外部亂打。
4. **本機 / 線上資料庫差異**:不想為了測小功能就連雲端資料庫,就用
   SQLAlchemy + TypeDecorator 抹平 SQLite 與 Postgres 的 UUID / JSONB
   差異;「本機測完直接上線」才不會踩資料庫差異的雷。
5. **家人不會用 bot**:不解釋,直接示範 — 在群組打一句話讓 bot 跳出提醒,
   家人看 1 次就會用。bot 不要寫指令說明書,要讓第一個成功案例自己說話。

## 紅線與注意

- **secret 不落地**:LINE channel token、Supabase 連線字串、cron secret
  一律走環境變數,不硬編碼、不 commit。
- **隱私**:主流程不接 LLM 的理由之一就是家人輸入不上傳第三方;若加
  LLM fallback,先想清楚哪些內容會被送出去。
- **免費額度是實測不是保證**:Supabase / Render 的 free tier 條件可能
  變動,部署前以官方當下的方案頁為準。
- **換平台可行**:Telegram / Discord 也能做 — 抽掉 LINE handler 那段換成
  對應 API 即可,parser + 資料庫 + cron 三段通用(來源站台估約 30 分鐘
  工程)。台灣家人最常用 LINE,所以原版做 LINE。

## 侷限(誠實告知)

- 規則解析只涵蓋固定格式的句子(日期 + 時間 + 人 + 事);句式太自由時
  會落到 fallback,不是萬能 NLU。
- Render free tier 會自動 sleep,cold start 約 30 秒 — 靠外部 ping 保活,
  不適合對延遲極敏感的場景。
- 本 skill 的數據(成功率、免費額度、上線時長)來自來源站台的單一實例
  實測,你的環境請自行驗證。
