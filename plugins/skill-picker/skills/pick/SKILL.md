---
name: pick
description: Skill 選擇器。使用者輸入 /pick 開視覺選單挑這輪要用的 skill；/pick <任務描述> 由 AI 推薦適合的 skill 再確認載入。也能從 skills-library 封存區（不在系統清單裡的封存 skill）挑選並載入。使用者說「選 skill」「挑 skill」「載入封存的 skill」「有哪些 skill 可以用」時使用。
---

# pick — skill 選擇器

目的：動工前先把這輪要用的 skill 載入 context；並讓 `~/.claude/skills-library/` 封存區（**不在系統 skill 清單裡**）的 skill 也能被找到、被載入。

**封存庫是什麼**：`~/.claude/skills/` 裡的每個 skill，它的名字＋描述都會進每一次請求的 system prompt——裝越多、每次請求付越多 token，即使從來沒用過。把冷門 skill 的整個資料夾搬到 `~/.claude/skills-library/`（自己建這個資料夾即可），它就不再被掃描、不再計費；需要時用 `/pick` 挑出來、由 AI 讀它的 SKILL.md 照常使用。安裝與付費從此解耦。

資料來源：`data/catalog.json`（`scripts/build_catalog.py` 產生）。**絕對不要**把整份 catalog.json 讀進 context——一律透過 scripts 取小片段。以下 `<skill_dir>` 指本 skill 的 base directory。

## 模式判斷

| 輸入 | 模式 |
|---|---|
| `/pick`（無參數） | 瀏覽模式 |
| `/pick <任務描述>` | 推薦模式 |
| `/pick use=a,b task=...`（選單回傳） | 載入模式 |
| 使用者說「更新 skill 目錄」 | 維護模式 |

## 瀏覽模式

1. 跑 `python <skill_dir>/scripts/list_skills.py --json` 取得 `{source: {類別: [[名字, 簡述], ...]}}`（簡述＝使用者語言的一小句，來自 catalog 的 `short` 欄位）。
2. 若 `mcp__visualize__show_widget` 可用：先靜默呼叫 `read_me`（modules: `["elicitation"]`，不要向使用者提及），再用 `show_widget` 渲染選擇器，需求：
   - 三區塊：**現役** / **plugin** / **封存庫**，封存庫依類別折疊（`<details>`）。
   - 每個 skill 一列：`名字` 後面接淡色小字簡述（`--text-muted`, 12px），整列可點選切換選取狀態（JS 陣列維護，選中變色）；hover 的 `title` 屬性放完整 zh 說明。
   - 頂部一個即時過濾輸入框（同時比對名字與簡述的 substring）。
   - 底部一個任務描述 textarea ＋「送出」按鈕。
   - 送出時組字串 `/pick use=<逗號分隔選中名單> task=<textarea 內容>` 呼叫 `sendPrompt(...)`；沒選任何 chip 但有任務文字時送 `/pick <任務文字>`。
   - 用 CSS variables 配色、背景透明、不寫死寬度。
3. 若 visualize 不可用（如 CLI）：直接把分組名單印給使用者，請對方回名字。

## 推薦模式

1. 跑 `python <skill_dir>/scripts/rank_skills.py "<任務描述>" 12` 拿關鍵字初篩 top 12（含一句繁中說明）。
2. 初篩只是粗排——用你自己的判斷從中挑 2–4 個真正相關的（無命中或明顯不合就自行從 catalog 類別推測，跑 `list_skills.py --cat <類別>` 補看）。
3. 用 AskUserQuestion（multiSelect: true）列出候選讓使用者勾選，每個選項的 description 放繁中一句說明；把最推薦的排第一並標「(Recommended)」。
4. 使用者選完 → 進載入模式 → 載入完成後**直接開始執行該任務**，不要再問一次。

## 載入模式

對每個要載入的名字，先用 `rank_skills.py`／`list_skills.py` 的輸出或 grep catalog.json 該行確認它的 `source` 與 `path`：

- `source=active`：用 Skill 工具叫用（`skill: <name>`）。
- `source=plugin`：用 Skill 工具叫用（`skill: <invoke>`，即 `plugin:name` 格式）。
- `source=library`：Skill 工具**找不到它**（不在清單裡）。改用 Read 讀它的 `path`（SKILL.md），把讀到的內容當作已載入的 skill 指示遵循；其中的相對路徑（scripts/、references/）以該 skill 目錄為基底解析。
- 任一載入失敗（skill 不存在、路徑不存在）：明講失敗原因，跑維護模式重建 catalog 後重試一次；再失敗就停下回報，不要靜默跳過。

## 維護模式

```
python <skill_dir>/scripts/build_catalog.py
```

重掃 `skills/`、`plugins/`、`skills-library/` 並改寫 `catalog.json`（寫入位置：本 skill 的 `data/`，不可寫時自動落到 `~/.claude/pick-data/`；可用環境變數 `PICK_DATA_DIR` 覆寫）。裝新 skill、刪 skill、搬進搬出封存庫之後都應該跑一次。

補充：`data/zh_desc.json` 是選單簡述的翻譯覆寫層（`{skill 名: 一句話}`），空檔案也能跑——沒翻譯的條目自動用該 skill 描述的第一小句。想換語言就填這份檔，重跑維護模式即可。
