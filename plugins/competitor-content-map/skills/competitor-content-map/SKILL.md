---
name: competitor-content-map
description: >
  讀取自己與競品的公開 sitemap，產出 URL 路徑粗分桶、跨站覆蓋矩陣、內容空白候選、
  lastmod 新鮮度訊號及可選 AI 語意分群。當使用者要做競品內容盤點、content gap、
  sitemap 比較、選題卡位或主題漂移檢查時使用；輸入為自己的站與一至多個對手域名或設定檔，
  輸出為同一資料夾中的時間戳 Markdown 作戰地圖與 JSON 原始資料，不輸出搜尋量或競爭度。
---

# 對手內容地圖

## 引導邊界

腳本只建立公開 sitemap 的確定性地圖；執行 Agent 依市場、語言、商業模式與
可用研究工具補完語意與優先順序。報告不是完整策略，也不需預想所有產業分桶。

## 適用與不適用

適用：規劃新內容前盤點公開版圖、比較主題覆蓋、找出待驗證的 gap、觀察 sitemap
`lastmod` 訊號。建議同時傳 `--you`，先用自己的主軸約束空白候選。

不適用：

- 估算搜尋量、KD、競爭度、流量、排名或商業價值；sitemap 沒有這些資料。
- 判定對手頁面品質或實際排名；URL 數量不是成效。
- 抓未公開、需登入或對方禁止存取的內容。
- 直接產出可發布內容月曆；本工具只產生「值得再驗證」的主題候選。

## 開始前輸入

先取得：

1. **自己的站**：建議一個公開域名，傳給 `--you`；沒有時必須接受無法做主軸對齊。
2. **對手站**：至少一個公開域名，傳給 `--vs`，或放入 UTF-8 設定檔。
3. **輸出資料夾**：`--out` 是資料夾，不是 `.md` 檔；例如 `./maps`。
4. **執行模式**：basic、`--cc`、`--ai` 三選一；不要同時傳 `--cc` 與 `--ai`。
5. **分析問題**：要比較的市場與內容範圍；避免把不同語言或不同商業模式的站混成結論。

設定檔一行一個域名，整行 `#` 開頭為註解；行尾 ` you` 只標一個自己的站。命令列
`--you` 優先於設定檔。不要在域名行尾加入註解。

## 三種執行模式

| 模式 | 依賴與行為 | 何時選 | 成功判準 |
|---|---|---|---|
| basic | Python 標準庫；確定性抓取、粗分桶、矩陣、gap、lastmod，報告內附手動 AI prompt | 預設；零依賴、要可重現原始地圖 | Markdown + JSON 都產出；無第 8 節也屬正常 |
| `--cc` | basic 後呼叫已安裝且已登入的 `claude -p` | 使用者已可用 Claude Code 訂閱且要自動語意分群 | basic 產物存在，Markdown 有 `## 8. AI 語意分群結果` |
| `--ai` | basic 後用 `anthropic` 套件與環境中的 `ANTHROPIC_API_KEY` 呼叫 API，會產生費用 | 使用者明確同意 API 成本且已有安全注入的 key | basic 產物存在，Markdown 有第 8 節，終端無 API 跳過訊息 |

`--cc` 或 `--ai` 失敗時，腳本仍可能以 exit code 0 產出 basic 地圖；因此不能只看 exit code
宣稱 AI 分群完成。

## 執行模式與腳本定位

有檔案系統與網路能力時，agent 直接代跑、讀 Markdown 與 JSON、標記殘缺來源；只有登入、
API 成本同意或來源選擇需要使用者時才停下來。不要硬編碼、回顯或寫入 API key。

不要假設目前目錄有 `scripts/`。plugin 安裝版優先從 `${CLAUDE_PLUGIN_ROOT}` 定位；裸 repo
的腳本在 repo 根目錄。

macOS / Linux / Git Bash：

```bash
if [ -n "${CLAUDE_PLUGIN_ROOT:-}" ] && [ -f "${CLAUDE_PLUGIN_ROOT}/skills/competitor-content-map/scripts/competitor_sitemap_map.py" ]; then
  SCRIPT="${CLAUDE_PLUGIN_ROOT}/skills/competitor-content-map/scripts/competitor_sitemap_map.py"
elif [ -f "./competitor_sitemap_map.py" ]; then
  SCRIPT="./competitor_sitemap_map.py"
elif [ -f "./scripts/competitor_sitemap_map.py" ]; then
  SCRIPT="./scripts/competitor_sitemap_map.py"
else
  echo "找不到 competitor_sitemap_map.py" >&2; exit 1
fi
python "$SCRIPT" --help
```

PowerShell：

```powershell
$scriptPath = $null
if ($env:CLAUDE_PLUGIN_ROOT) {
  $candidate = Join-Path $env:CLAUDE_PLUGIN_ROOT 'skills\competitor-content-map\scripts\competitor_sitemap_map.py'
  if (Test-Path -LiteralPath $candidate) { $scriptPath = $candidate }
}
if (-not $scriptPath -and (Test-Path -LiteralPath '.\competitor_sitemap_map.py')) { $scriptPath = '.\competitor_sitemap_map.py' }
if (-not $scriptPath -and (Test-Path -LiteralPath '.\scripts\competitor_sitemap_map.py')) { $scriptPath = '.\scripts\competitor_sitemap_map.py' }
if (-not $scriptPath) { throw '找不到 competitor_sitemap_map.py' }
python $scriptPath --help
```

通過判準：`--help` 顯示 `--vs`、`--you`、`--config`、`--cc`、`--ai`、`--out`。
若 `python` 不存在，使用環境既有的 `python3` 或 `py -3`，不要下載未知執行檔。

## 工作流程

| 步驟 | 動作 | 為什麼 | 通過判準 |
|---|---|---|---|
| 1. 驗證站台 | 正規化域名，瀏覽器檢查首頁、`/sitemap.xml` 或 `robots.txt`；排除需登入與範圍不相符的站 | 避免把錯域名或異質競品變成內容策略 | 每個目標都可公開存取，且清楚標記自己／對手 |
| 2. 驗證輸出與模式 | 確認 `--out` 是可建立的資料夾；basic／`--cc`／`--ai` 三選一 | 防止把 `map.md` 建成資料夾，也避免兩種 AI 模式互相遮蔽 | 輸出目標不是既有檔案；模式依賴已滿足 |
| 3. 先跑 basic | 即使最終要 AI 分群，也先取得確定性地圖與 JSON | 把抓取事實與模型推論分開，便於重跑與查錯 | exit code 0，終端列出 Markdown、JSON 路徑 |
| 4. 檢查完整性 | 在 Markdown「抓取結果」或 JSON 檢查每站 `url_count`、`sitemaps_used`、`errors`、`incomplete` | 部分失敗不能當完整比較 | 每個預定站 `url_count > 0` 且 `incomplete = false`；否則只產診斷並 exit code 3 |
| 5. 讀自己的主軸 | 確認第 0 步有自己的主打桶、佔比與 slug tokens | gap 若沒有主軸約束，容易把團隊帶向主題漂移 | 有 `--you` 且自己的站抓取成功；否則降級為無對齊盤點 |
| 6. 執行可選 AI 分群 | 需要時用同一組輸入重跑 `--cc` 或 `--ai`，保留 basic 產物 | AI 只負責語意歸納，不應改寫抓取事實 | Markdown 出現第 8 節；沒有 skip、timeout、缺 key 或套件訊息 |
| 7. 外部驗證 gap | 將候選帶到可觀測的第一方／專業關鍵字工具與 GSC 驗證需求 | sitemap 與 LLM 都無法提供搜尋量和競爭度 | 每個要採用的候選都有外部證據或明確標為待驗證 |

### basic 命令

macOS / Linux / Git Bash：

```bash
python "$SCRIPT" --you www.your-site.com --vs rival1.com rival2.com --out ./maps
```

PowerShell：

```powershell
python $scriptPath --you 'www.your-site.com' --vs 'rival1.com' 'rival2.com' --out '.\maps'
```

設定檔：

```bash
python "$SCRIPT" --config ./competitors.txt --out ./maps
```

### `--cc` 與 `--ai`

```bash
# 先確認 claude CLI 已安裝且使用者已登入
claude --version
python "$SCRIPT" --you www.your-site.com --vs rival1.com --cc --out ./maps-cc

# API 模式：key 必須已由安全的環境／secret manager 注入，不要寫進命令、Skill 或 repo
python -m pip show anthropic
python "$SCRIPT" --you www.your-site.com --vs rival1.com --ai --out ./maps-ai
```

PowerShell 將 `$SCRIPT` 改成 `$scriptPath`。`--ai` 會另外計費；未取得使用者同意不要代跑。

## 輸出解讀

- `map-*.md`：完整抓取才有的人讀作戰地圖；第 7 節是手動 AI prompt，第 8 節只在自動分群成功時出現。
- `data-*.json`：完整抓取的 URL、sitemap、錯誤、完整性、bucket 與 gap 可稽核資料。
- `diagnostic-*.md`／`diagnostic-*.json`：抓取不完整時的排錯資料；刻意不產出 gap、內容策略或 AI prompt。
- **路徑桶**是粗分類；語意分群結果是模型推論。
- **主軸對齊**依 URL 路徑與 slug token 計算；中文 slug 可能使輪廓偏薄。
- **lastmod** 是 sitemap 提供者聲明；全站同日常是產生器行為，不能證明真的更新內容。
- **空白候選**只代表公開 sitemap 的覆蓋差異，不代表有搜尋需求、能排名或值得投資。

禁止補造 sitemap 中不存在的搜尋量、KD、引用次數、流量或優先分數。若使用者需要這些值，
另行用 Keyword Planner、GSC 或已授權的專業資料源取得，並標來源與日期。

## 停止條件與排錯

- exit code 2 或顯示至少需 `--vs`／`--config`：補齊輸入；不要用空清單產報告。
- `--out` 指向既有檔案：改成新資料夾。副檔名不會讓它變成報告檔。
- 所有站都抓不到、exit code 1：檢查域名、網路、robots 與 sitemap；停止分析。
- exit code 3：任一目標、子 sitemap 或 URL 安全檢查失敗，或碰到 sitemap／URL 上限；只讀 `diagnostic-*` 排錯，不得做策略結論，修復後重跑。
- 自己的站或個別對手抓不到：不可把缺資料解讀為內容空白，也不可宣稱「與你的主軸對齊」或「你沒有寫」。
- `--cc` 找不到 CLI、逾時或回非零：basic 仍有效；第 8 節未出現就標記 AI 分群未完成。
- `--ai` 缺套件、key 或 API 失敗：不要貼 key 排錯；改 basic／`--cc`，或由使用者修復安全注入。
- AI 回傳搜尋量、KD 或排名斷言：刪除那些欄位，保留為待外部驗證候選。

## 完成定義

- 目標輸出資料夾中有同時間戳的 Markdown 與 JSON，兩者皆可讀。
- 每個納入比較的站都抓到 URL；所有失敗、截斷或缺 sitemap 的站已揭露。
- 有自己的站時已先讀第 0 步；沒有時已明說不能做主軸對齊。
- 選定模式的成功判準成立，不能把 basic fallback 說成 AI 分群完成。
- 回報包含輸出資料夾絕對路徑、兩個檔案路徑、站數、各站 URL 數、模式與待驗證 gap。
- 不含未經來源驗證的搜尋量、競爭度或排名承諾。

## 安全與侷限

- 只抓公開 HTTPS sitemap 與 URL；限制 443 port、同來源 sitemap／頁面，redirect 會重驗，
  連線固定到驗證過的公開 IP 並保留原網域的 TLS 驗證；拒絕 private／loopback／link-local／
  reserved 位址、不符 MIME、過大回應與解壓縮炸彈。
  仍須尊重 robots、網站條款與負載，不繞過登入或反爬限制。
- 每站有 sitemap 與 URL 數量安全上限；碰到上限即標記不完整、只產診斷並 exit code 3。
- `--cc` 使用本機已登入的 Claude CLI；`--ai` 使用付費 API。任何 key 都不得寫入 repo、報告或對話。
- AI prompt 可能包含公開 URL 清單；不得把內部、未發布或帶敏感 query 的 URL 送往第三方模型。
- sitemap 沒列出的頁面不可見；頁面內容品質、索引、排名、點擊與轉換也不在本工具觀測範圍。

## 來源與時效

截至 **2026-08-02** 查證：

- Coolkidlab plugin 根 README：https://github.com/Coolkidlab-Yin/Coolkidlab
- 獨立 repo README：https://github.com/Coolkidlab-Yin/competitor-content-map
- 執行行為以同目錄 `scripts/competitor_sitemap_map.py` 的 `--help`、exit code 與 JSON 為準。
- Sitemap 協定（官方規格）：https://www.sitemaps.org/protocol.html
