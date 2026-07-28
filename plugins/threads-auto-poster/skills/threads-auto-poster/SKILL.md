---
name: threads-auto-poster
description: >
  帶使用者建一個「人在迴路」的 Threads 半自動發文 bot。當使用者想做
  Threads 自動發文/排程發文/每天定時發文/用 Threads Graph API 寫發文 bot,
  或提到「自動發 Threads」「Threads bot」「排程貼文」時使用。
  照這份 SOP 引導:Claude Code 排程觸發 → 使用者選方向 → 抓 GitHub
  trending 選題 → 依語氣規則寫文 → Graph API 兩段式發文 → token 自動刷新。
---

# Threads 半自動發文 bot(threads-auto-poster)

## 什麼時候用

- 使用者想固定在 Threads 分享內容(例如策展 GitHub 好專案),但每天手挑手寫太耗時
- 使用者想做 Threads 排程發文或發文 bot,但不想要「全自動亂發」砸帳號
- 使用者要接 Threads Graph API,想避開已知的編碼與 token 陷阱

不適用:使用者想做「完全無人值守、AI 自己決定發什麼」的全自動 bot——這份 SOP 的核心立場正好相反,見下方架構總覽。

## 架構總覽(人在迴路設計)

這個 bot 的核心不是「全自動」,是「**人出方向,AI 包勞動**」:

1. 每天固定時間(原設計是 20:00 Asia/Taipei)由 Claude Code 的 scheduled-tasks 自動觸發
2. 觸發後第一件事**不是發文**,是用 AskUserQuestion 跳一題問使用者今天想看哪個方向(也要能直接回「今天跳過」)
3. 使用者點一下方向後,剩下的抓 repo、去重、寫文、發文全部自動
4. 使用者出 5 秒判斷,省下每天約 20 分鐘的重複勞動;而且每篇都是使用者選過方向的,不會發出沒看過的東西

為什麼堅持人在迴路:全自動發文 bot 很容易吐出一堆機器味、沒人看過的內容,反過來砸掉帳號可信度。自動化可以省力,但不能拿可信度去換。引導使用者時,先確認他接受這個架構再動工;若他堅持全自動,提醒風險後尊重決定。

## 照步驟做

動工前先跑第 0 步,之後每完成一步先跟使用者確認再往下做。

### 第 0 步:確認環境

先問清楚,不要假設:

- Claude Code 版本、是否有 scheduled-tasks 功能可用
- 是否已有 Threads Graph API 權限與 access token(沒有的話,先引導他到 Meta 開發者後台申請,拿到 long-lived token)
- 要用哪個 Threads 帳號發文
- 作業系統(Windows 使用者要特別注意第 5 步的編碼坑)

### 第 1 步:排程設定

用 Claude Code 的 scheduled-tasks 設一個每天固定時間觸發的排程(原設計是每天 20:00,時區 Asia/Taipei;時間與時區依使用者作息調整)。

### 第 2 步:建立流程指引檔(daily-workflow.md)

把完整流程寫成一份指引檔,排程觸發時照這份跑:

> 問方向 → 抓 repo → 去重 → 寫文 → 發文 → 記 log

語氣規則(第 4 步)與紅線(見文末)都**寫死在這份指引檔裡**,不要每次重講一遍。

### 第 3 步:問方向(AskUserQuestion)

觸發後第一步用 AskUserQuestion 跳一題,選項例如:

- AI / agent
- CLI 工具
- 全端後台
- 隨意挑(trending 第一名)
- 今天跳過

選項依使用者平常關注的領域客製。「今天跳過」必須是合法選項——人在迴路的意思是人隨時可以喊停。

### 第 4 步:抓 repo + 去重 + 選題

兩條抓取路徑:

- 選「隨意挑」→ 用 WebFetch 抓 GitHub trending
- 指定方向 → 走 GitHub search,按 star 排序抓前 15 個

然後:

1. 比對過去 30 天的發文 log 去重,不重複介紹同一個 repo
2. 避開 awesome-list 類清單專案與明顯刷 star 的專案
3. 挑一個高 star、且最近仍有在維護的

### 第 5 步:依語氣規則寫繁中介紹文

原設計的語氣規則(引導使用者定義自己的版本,寫進指引檔):

- 第一人稱
- 整篇最多 1 個 emoji
- 句尾不加句號,直接換行
- 控制在 480 字以內(Threads 上限 500,留 buffer)

### 第 6 步:Graph API 兩段式發文

Threads Graph API **不是一步發**,是兩段式:

1. 先建一個 `media_type` 為 `TEXT` 的 container
2. sleep 約 2 秒(不等的話 container 還沒就緒,publish 會失敗)
3. 再 publish

示意(端點與參數以 Meta 官方文件為準):

```bash
# 1. 貼文先寫成 UTF-8 檔(Windows 必要,原因見下方踩坑)
#    post.txt 內容 = 貼文全文

# 2. create container
CONTAINER_ID=$(curl -s -X POST "https://graph.threads.net/v1.0/<YOUR_THREADS_USER_ID>/threads" \
  --data-urlencode "media_type=TEXT" \
  --data-urlencode "text@$(cygpath -m /path/to/post.txt)" \
  --data-urlencode "access_token=<YOUR_TOKEN>" | jq -r '.id')

# 3. sleep 再 publish
sleep 2
curl -s -X POST "https://graph.threads.net/v1.0/<YOUR_THREADS_USER_ID>/threads_publish" \
  --data-urlencode "creation_id=$CONTAINER_ID" \
  --data-urlencode "access_token=<YOUR_TOKEN>"
```

token 一律走環境變數或機密管理工具注入,不要硬編碼進腳本、不要寫進會 commit 的檔案。

### 第 7 步:token 每週自動 refresh

long-lived token 大約 **60 天會靜默失效**——不報錯,bot 就默默不發了。對策:

- 建一個 refresh-token 腳本(token 滿 24 小時後即可刷新),排每週自動跑一次
- 刷新後的新 token 要回寫到 bot 讀取的位置

### 第 8 步:每步記 log

「沒報錯但也沒發」是這類 bot 最難抓的故障型態。流程每一步(選題、去重結果、產文、container id、publish 回應)都要記 log,方便事後對照哪一步斷掉。log 同時是第 4 步去重的資料來源。

## 我踩過的坑(原作者實測)

1. **Windows CP950 編碼**:Git Bash 的 curl 是 Windows 原生 build,中文直接塞進命令列會被 CP950 codepage 轉成亂碼。解法:貼文先用 Write 寫成 UTF-8 檔,curl 用 `--data-urlencode` 搭配 `@檔案` 去讀,路徑用 `cygpath -m` 轉成 curl 讀得懂的格式。
2. **兩段式發文的時序**:create container 後直接 publish 會失敗,中間要 sleep(約 2 秒)。
3. **token 60 天靜默失效**:不會報錯,就是某天開始不發了。每週自動 refresh + 每步 log 是唯二保險。
4. **「沒報錯但也沒發」**:這種靜默故障最難 debug,所以 log 不是選配是必要。

## 紅線與注意(自動發文的品質紅線)

寫死在流程指引檔裡,每篇都守:

1. **不塞 slogan**:結尾不加「追蹤我」這類 CTA
2. **不放聯盟連結或 UTM**:文中任何連結都不帶推廣參數
3. **不超過 500 字**:Threads 上限,寫文時留 buffer 控在 480 內

原因:策展型帳號的價值是「這個人真的每天在看這些東西」,一旦開始順手塞推廣,可信度就崩了——而 bot 最容易做歪的地方就是「順手塞」。

另外幾條注意:

- Threads Graph API 是官方 API,正常使用不會被鎖帳號;有 rate limit(每天約 250 篇 publish),日發 1 篇遠低於上限
- 不堆 hashtag、不重複發同一個 repo
- 想換平台(X / Bluesky):選 repo 與寫文那段通用,只有發文 API 那段要換,所以把發文 call 做成最後一段獨立 function
