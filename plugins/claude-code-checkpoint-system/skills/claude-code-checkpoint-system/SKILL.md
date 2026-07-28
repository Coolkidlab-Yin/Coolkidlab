---
name: claude-code-checkpoint-system
description: >
  幫使用者建立 Claude Code 跨對話斷點系統。當使用者抱怨「Claude Code 每次開新對話
  就忘光上次做到哪」「跨對話失憶」「每次都要重講一遍進度」,想建斷點/checkpoint/
  跨 session 接力機制,或手上多個專案想一眼看到「現在哪個最該處理」時使用。
  核心是 .project/ 斷點檔 + SessionStart hook 自動載入 + UserPromptSubmit
  時間注入 + 多專案儀表板,設計原則是「讀強制、寫柔性」。
---

# Claude Code 跨對話斷點系統(claude-code-checkpoint-system)

## 什麼時候用

- 每開一個新 Claude Code 對話,都要手動交代「上次做到哪、為什麼這樣決定、有沒有留半成品」
- 長專案跨很多個對話接力,交接靠人腦記,講久了會漏
- 手上多個專案進度不一,「現在哪個最該處理」沒有任何地方能一眼回答
- 想要一層「狀態記在硬碟上、開場自動讀回來」的基礎建設,而不是更聰明的 AI

## 原理:為什麼會失憶、斷點系統補什麼

Claude Code 每個對話是獨立的,沒有跨對話記憶——新對話開場就是一張白紙。斷點系統補的不是模型能力,是基礎建設:把狀態寫在硬碟上,開場自動讀回來。

整套分四層:

| 層 | 元件 | 做什麼 |
|---|---|---|
| 狀態層 | 每個專案一個 `.project/` 資料夾 | 存斷點:精簡斷點 + 長脈絡 + 決策日誌 |
| 載入層 | SessionStart hook | 開場自動把斷點塞進 context |
| 時間層 | UserPromptSubmit hook | 每則訊息注入當下精確時間 |
| 視覺層 | 掃描全部專案的儀表板 | 回答「現在哪個專案最該處理」 |

最關鍵的設計判斷是**「讀強制、寫柔性」**:

- **讀(載入斷點)走 hook 強制執行**——零成本、又絕對不能漏,用機器保證。
- **寫(更新斷點)只用柔性提醒**——如果用 hook 強制擋著不讓你隨手問一句,會非常煩。寫的那端留給人自由。

另外兩個設計判斷:

- **決策日誌 append-only**:決策會演變,用新條目標 `supersedes` 舊的、永不覆寫,才能回溯整條演化線。
- **半成品保護**:精簡斷點裡放一個 `safe_to_continue` 旗標,任務開始設 `false`、乾淨結束才設回 `true`。開場載入看到 `false`,先警告上次有未完成的工作、問要繼續還是回滾,而不是悶頭往下做。

補充:hooks 是 Claude Code 在特定事件觸發時自動執行的 shell command。SessionStart hook 在每次開新對話時跑;UserPromptSubmit hook 在每次使用者送訊息前跑。設定在 `~/.claude/settings.json`。

## 照步驟做

先確認使用者的作業系統跟專案結構,再一層一層建,每建一層停下來跟使用者確認再繼續。

### 第 1 步:狀態層 —— `.project/` 三個檔

在專案根目錄建 `.project/` 資料夾,放三個檔:

1. **`current.yaml`** — 精簡斷點,控制在 30 行內(每次開場都要載入,太長會吃 context)。欄位:
   - `phase`:現在做到什麼階段
   - `last_updated`:上次更新時間
   - `safe_to_continue`:半成品旗標(任務開始設 false、乾淨結束設回 true)
   - `needs_human`:有沒有卡在需要人決定的事
   - `next_task` / `next_input`:下一步做什麼、需要什麼輸入
   - `open_issues`:未解問題清單
2. **`current.full.md`** — 長脈絡(架構、踩過的雷、外部依賴),按需才讀,不進開場載入。
3. **`decisions.yaml`** — 只增不改的決策日誌。每條有 `id`、`date`、`decision`、`rationale`、`status`;決策演變時用新條目標 `supersedes` 舊條目的 id,永遠不要覆寫舊條目。

寫斷點的原則:「下一個 session 看了能 1 分鐘進入狀態」,不是「完整日誌」。

另可加一個 `roadmap.md`(整體路線圖,用機器可解析的 status 標記),供儀表板掃描。

### 第 2 步:載入層 —— SessionStart hook

在 `~/.claude/settings.json` 註冊 SessionStart hook,行為:

- 每次開對話自動把 `current.yaml` 印出來注入 context。
- 如果 `safe_to_continue` 是 `false`,先警告使用者上次有未完成的工作、問要繼續還是回滾,不要悶頭往下做。
- 沒有 `.project/` 的專案要**安靜跳過、不要報錯**(不是每個資料夾都是斷點專案)。

### 第 3 步:時間層 —— UserPromptSubmit hook

註冊 UserPromptSubmit hook,每則訊息前注入一行當下精確時間(年月日時分秒加星期)。

**務必用純 ASCII 輸出、只留 UTC 偏移**(像 `UTC+08:00`),不要印本地化的時區名稱——在 Windows 上會被 cp950 編碼轉成亂碼(詳見踩坑)。

### 第 4 步(選配):視覺層 —— 多專案儀表板

- 一支掃描腳本,掃全部專案的 `.project/` 讀出 phase / 狀態。
- 生成自帶資料的 HTML(embedded JSON),雙擊即開、免伺服器。
- 全域 `project-registry.yaml` 登記專案清單,支援群組 / 角色 / parent,多專案分組顯示。

### 第 5 步:hook 註冊範本

`settings.json` 的註冊遵守「讀強制、寫柔性」:SessionStart 強制載入;寫回斷點若要提醒,用 Stop 事件做柔性提醒即可,不要強制阻擋。

### 建置腳本原則

- init 腳本要**冪等**:不覆寫既有檔,重跑安全。
- **不要依賴 jq** 之類使用者可能沒裝的工具,能用內建或 Python 就好——依賴愈少愈好移植。

## 我踩過的坑

1. **jq 依賴**:盤點腳本依賴 jq,但 Windows 上沒裝。解法不是去裝 jq,是改用 Python 重寫等效版——依賴愈少愈好移植。
2. **多行 YAML 折疊語法**:有 11 個 skill 的描述用了多行折疊語法(`>` / `|`),簡易解析器只抓到折疊符號本身。解法:補上「往下讀到下一個 key 為止」的邏輯。
3. **Windows cp950 亂碼**:時間 hook 輸出 UTF-8,在 Windows cp950 環境下本地化時區名變亂碼。解法:乾脆純 ASCII 輸出、把本地化時區名拿掉只留 UTC offset。

## 注意

- **寫斷點的習慣要養**:骨架用 agent 建好約 30 分鐘,但「養成寫斷點檔的習慣」要 1–2 週——一開始會忘記寫,經歷幾次「下次開新對話想不起來」就學乖了。
- **current.yaml 別放縱變長**:超過 30 行就把細節搬去 `current.full.md`,精簡斷點每次開場都載入,長度直接吃 context。
- **不要用 hook 強制要求寫斷點**:會把「隨手問一句」的體驗毀掉。寫的紀律靠柔性提醒 + 習慣,不靠機器攔截。
- **與內建記憶功能的取捨**:file-based 斷點只在需要時讀進來、沒有上限,適合跨幾百個對話的大專案;小專案用平台內建的自動記憶/同步比較省事,不必硬上這套。
