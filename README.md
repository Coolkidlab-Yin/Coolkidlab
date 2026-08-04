# Coolkidlab

Coolkid AI Lab 的繁中 Claude Code plugin 工具庫。內容來自
[coolkidlab.com](https://www.coolkidlab.com) build-in-public 過程中的真實需求，
不是 prompt 收藏：每個 Skill 都要讓 Agent 知道怎麼判斷、何時停、如何驗收，
再依使用者的 repo 與環境補完實作。

## 這個工具庫適合誰

- 想直接跑網站分析，不想先裝一串套件的人。
- 想讓 Agent 帶著自己建立 Workflow，而不是只拿到一篇概念文章的人。
- 想學決策順序、風險邊界與完成證據，而不是複製作者整套技術棧的人。

目前分成兩類：

1. **可執行 SEO 工具**：plugin 內含 Python 腳本，可由 Agent 代跑並解讀。
2. **引導型 Workflow Skills**：提供方向、必要 gates、平台邊界與一個實跑案例；
   不窮舉所有用途，也不替執行 Agent 預寫完整專案。

## 30 秒安裝

在 Claude Code 執行：

~~~text
/plugin marketplace add Coolkidlab-Yin/Coolkidlab
/plugin install article-overlap-checker@coolkidlab
~~~

把第二行 plugin 名稱換成下表任一項。安裝後直接說目標，不必背命令：

~~~text
幫我掃這個網站輸出資料夾，找互搶排名的文章
我想做一個先讓我看草稿才會發布的 Threads bot
從這 12 篇舊貼文萃取一份 voice profile
~~~

更新 marketplace：

~~~text
/plugin marketplace update coolkidlab
~~~

## 選一個適合的 Skill

| 類型 | Skill | 你要準備的輸入 | Agent 會帶你得到什麼 |
|---|---|---|---|
| SEO 工具 | **article-overlap-checker** | 本機 HTML 資料夾或公開 sitemap | 撞稿、太接近與孤島頁報告 |
| SEO 工具 | **competitor-content-map** | 自己與對手的網域 | 主題分桶、覆蓋矩陣、空白與新鮮度地圖 |
| Workflow | **threads-bot-builder** | 帳號目的、內容來源、觸發與人工 gate | 可 dry-run、去重、可回讀的 Threads 流程 |
| Workflow | **ig-bot-builder** | 素材、圖片策略、觸發與人工 gate | 有視覺預覽、權利檢查與可靠發布邊界的 IG 流程 |
| Workflow | **line-bot-builder** | 使用者、收訊息/推播、資料與送達需求 | 只建必要元件、可驗簽且逐收件人追蹤的 LINE bot |
| Workflow | **ga4-chatgpt-referral** | GA4；可選 GSC、Bing Webmaster Tools | 有證據分級的 AI referral 追蹤方法 |
| Workflow | **brand-profile-lockdown** | 經歷、作品、失敗與在意的事 | 有原始事實支撐的 brand-profile.md |
| Workflow | **voice-profile-extraction** | 自有寫作樣本與 holdout | 可驗證、可版本化的 voice-profile.md |
| Workflow | **claude-code-checkpoint-system** | 長期專案與 hooks 環境 | 狀態檔、載入 hook 與跨 session smoke |

### 怎麼選

- 想現在分析資料：先選兩個 SEO 工具。
- 想建立一套系統：選 Workflow；Agent 會先確認模式與範圍，再補完現場細節。
- 只想理解方法：明說「先教學，不要實作」。
- 涉及發文、部署、公開 URL、雲端資源或付費：先 dry-run，外部副作用前確認。

## Skill 的共同設計原則

這個 marketplace 的 Skill 必須同時「給人用」與「給人學」，但不寫成百科：

- **引導，不代做所有設計**：說清楚決策欄位與順序，讓執行 Agent 依 repo 補完。
- **例子不是目錄**：只放少量代表案例與「其他」，不假裝列完所有用途。
- **實跑案例是證據**：保留作者踩過的坑，標明它不是唯一答案。
- **責任清楚**：列出輸入、輸出、停止條件、外部副作用與完成定義。
- **先可逆再外部**：先做 dry-run、mock、smoke；發文、部署、付費前再次確認。
- **事實分層**：官方規格、單一實測與推論分開；會變的 API/額度執行時重查。
- **失敗可診斷**：有去重、log、bounded retry、回讀與 recovery，不以寫完檔案冒充完成。

完整貢獻規格見 [CONTRIBUTING.md](CONTRIBUTING.md)。

## 兩個可直接執行的 SEO 工具

### article-overlap-checker

用 TF-IDF 掃本機 HTML 或公開 sitemap，回報撞稿候選、太接近與孤島頁。
純 Python 標準庫、零依賴，中英混排支援 CJK bigram。預設閾值來自作者
75 頁繁中站的實際分布，是起點，不是通用定律。

本機或內網站請使用 **--dir** 掃輸出資料夾；遠端模式只接受公開 HTTPS，
並採 fail-closed SSRF 防護，不提供 localhost／私網 bypass。

背景故事：
[連載 #25：帶最多流量的頁反而在拖累你想排的詞](https://www.coolkidlab.com/seo-journey/semantic-map-topic-drift.html)。
裸腳本 repo：
[Coolkidlab-Yin/article-overlap-checker](https://github.com/Coolkidlab-Yin/article-overlap-checker)。

### competitor-content-map

把公開 sitemap 轉成主題分桶、跨站覆蓋矩陣、內容空白與 lastmod 新鮮度訊號。
流程先讀自己的站找主軸，再看對手，避免看到空白就照單全收造成主題漂移。

確定性資料由腳本處理、語意分群交給 Agent、搜尋量與競爭度回到有真實資料的
工具驗證。此工具目前只讀公開 HTTPS sitemap，不支援 localhost、私網 staging
或本機匯出；不要為了繞過限制把內網服務公開。需要私有資料時，先另做明確、
可審核的本機匯入設計。

裸腳本 repo：
[Coolkidlab-Yin/competitor-content-map](https://github.com/Coolkidlab-Yin/competitor-content-map)。

## Workflow 的實戰來源

三個 builder 已改名，但保留原本已收錄的文章網址：

| Skill | 實戰連載 | 獨立 repo |
|---|---|---|
| **threads-bot-builder** | [原始 Threads 策展產線](https://www.coolkidlab.com/workflows/threads-auto-poster.html) | [repo](https://github.com/Coolkidlab-Yin/threads-bot-builder) |
| **ig-bot-builder** | [原始 IG 新聞圖卡產線](https://www.coolkidlab.com/workflows/ig-news-bot.html) | [repo](https://github.com/Coolkidlab-Yin/ig-bot-builder) |
| **line-bot-builder** | [原始家族行程提醒產線](https://www.coolkidlab.com/workflows/family-line-bot.html) | [repo](https://github.com/Coolkidlab-Yin/line-bot-builder) |
| **ga4-chatgpt-referral** | [AI referral 倒推 SOP](https://www.coolkidlab.com/workflows/ga4-chatgpt-referral.html) | [repo](https://github.com/Coolkidlab-Yin/ga4-chatgpt-referral) |
| **brand-profile-lockdown** | [品牌顧問式訪談](https://www.coolkidlab.com/workflows/brand-profile-lockdown.html) | [repo](https://github.com/Coolkidlab-Yin/brand-profile-lockdown) |
| **voice-profile-extraction** | [語氣指紋萃取](https://www.coolkidlab.com/workflows/voice-profile-extraction.html) | [repo](https://github.com/Coolkidlab-Yin/voice-profile-extraction) |
| **claude-code-checkpoint-system** | [跨對話斷點系統](https://www.coolkidlab.com/workflows/claude-code-checkpoint-system.html) | [repo](https://github.com/Coolkidlab-Yin/claude-code-checkpoint-system) |

教學 Skill 不含任何人的帳號金鑰、voice profile 或 brand profile。交易類 workflow
依 Lab 的 YMYL 紅線不開源。

## 安全與誠實邊界

- 安裝第三方 plugin 前先讀內容；marketplace plugin 會被複製到本機 cache 執行。
- token、API key、資料庫連線只走環境變數或 secret manager；repo 只放空白範例。
- 社群發布、建立雲端資源、付費 API 等外部副作用必須先預覽並取得確認。
- 網站分析、AI 引用歸因與內容空白都是決策輔助，不是排名或流量保證。

## 驗證 marketplace

維護者在 repo 根目錄執行：

~~~bash
python scripts/validate_skills.py
python scripts/validate_skills.py --runtime-smoke
python -m unittest discover -s tests -v
claude plugin validate .
~~~

第一個只做靜態檢查；runtime smoke 與 tests 只對受信任 checkout 執行。
每個 Skill 的正向觸發與近似誤觸案例收在
[evals/skill-scenarios.json](evals/skill-scenarios.json)，修改 description 時一併更新。

## Credits

撞稿、主題漂移、語意集中度與從 sitemap 看內容版圖等觀念，啟發自
[@darkseoking](https://www.threads.com/@darkseoking) 的繁中 SEO 教學與 MIT
開源內容。Coolkid AI Lab 負責實作、閾值校準、防編造分工與實測記錄。

觀念是公共的，實作是自己的，數據是站台的——三層分開標，是這個 Lab 的誠實原則。

## License

[MIT](LICENSE)
