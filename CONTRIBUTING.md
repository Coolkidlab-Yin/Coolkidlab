# Contributing to Coolkidlab

這個 repo 收的是「別人裝了能完成任務、讀了能學會方法」的 Claude Code Skills，
不是 prompt 收藏。新增或修改 Skill 前，先用下面的完成定義自查。

## Skill 完成定義

每個 `SKILL.md` 至少要讓讀者找到這些答案：

1. **何時該用／不該用**：description 與正文一致，包含真實觸發語境。
2. **開始前要什麼**：輸入、權限、環境、關鍵選擇；只問 secret 名稱與是否備妥，不收值。
3. **會產出什麼**：檔名、資料夾、報告欄位或可觀察行為。
4. **怎麼一步步完成**：每一階段都有動作、理由與通過判準。
5. **哪裡必須停**：資料不完整、權限不足、驗證失敗或外部副作用前要設 gate。
6. **怎樣才算成功**：實跑、smoke、read-back 或真實介面觀察；不能只寫「已建立」。
7. **失敗怎麼辦**：常見症狀、診斷順序、可安全重試與不可盲目重試的邊界。
8. **有哪些限制**：把單一站台實測、推論與平台保證分開。
9. **去哪查最新規格**：會改版的 API、額度與 UI 附官方一手來源及查證日期。
10. **Agent 要補完什麼**：明示 Skill 的引導邊界，不把例子寫成完整可能清單。

## 寫法

- 使用祈使句告訴 Claude 要做什麼，也說明為什麼。
- 把 Skill 寫成給執行 Agent 的導航：說清楚決策順序、不可省的 gate、
  停止條件與驗收證據，再由 Agent 依使用者 repo 和環境補完。
- 不追求列完所有用途、技術棧與分支；用少量例子打開思路，永遠保留
  「其他／依現場判斷」，避免把可泛化 Skill 寫成某一個人的完整專案。
- 把作者實跑版本留成一個有證據的 recipe，標明它是校準案例，不是唯一答案。
- `SKILL.md` 以 500 行內為目標；大型背景資料移到同一 plugin 的 `references/`，
  並在正文說明何時讀哪一份。
- 相對資源必須住在 plugin 目錄內。Claude Code 安裝 plugin 後會使用 cache，
  不可依賴 repo 外的 `../shared-file`。
- 執行 plugin 內腳本時，以 `${CLAUDE_PLUGIN_ROOT}` 定位，不可假設使用者目前目錄
  剛好是 Skill 目錄。
- 範例一律使用假網域、假 ID 與環境變數名稱，不放可用 token。

## Workflow 類額外要求

- 先分清楚「只教學」與「直接在使用者 repo 實作」模式。
- 可逆的本機建置可逐步執行；真實發文、公開部署、付費或覆寫資料前再次確認。
- 先 dry-run，再做外部 smoke；把 log、idempotency 與 recovery 納入設計。
- 教學不是一次吐完整專案：每個 phase 通過才進下一個 phase。

## 可執行工具類額外要求

- `--help` 能跑，輸入錯誤要有可理解訊息，殘缺輸入不能產生看似完整的結論。
- Skill 要列出完整命令、成功輸出、輸出檔與解讀原則。
- 確定性資料交給程式，語意判斷交給模型；模型不可編造來源資料裡沒有的數字。

## 驗證

在 repo 根目錄執行：

```bash
python scripts/validate_skills.py
python scripts/validate_skills.py --runtime-smoke  # 只在信任目前 checkout 時執行
python -m unittest discover -s tests -v
claude plugin validate .
```

PR 的 CI 使用 base branch 的受信驗證器，把投稿 checkout 當純資料做靜態 compile，
不執行投稿者可修改的 validator 或 plugin script；受保護分支 push 才跑
`--runtime-smoke`。若有 Python 腳本，再在受信任 checkout 實跑一個不碰外部帳號的
smoke case。涉及平台 API
的 Skill 要在 PR 說明列出查過的官方文件與日期；無法實際發布時，明說未驗證到哪一層。
修改觸發 description 時，也要更新 `evals/skill-scenarios.json`：每個 Skill 至少保留
一個應觸發案例與一個共享關鍵字、但其實不應觸發的近似案例。

## Plugin 版本

這個 marketplace 的 `plugin.json` 有明確版本，因此任何會改變已安裝 Skill 行為的
發布都要更新版本：相容的教學補強升 minor，純錯字或不改行為的修正升 patch，破壞性
改動才升 major。只推 commit、不改版本，已安裝的使用者可能拿不到更新。
