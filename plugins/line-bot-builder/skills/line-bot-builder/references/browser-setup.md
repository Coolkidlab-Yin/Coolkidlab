# LINE 後台瀏覽器 MCP 陪走

## 先講為什麼要接

設定 LINE Developers Console 的每一步都在登入後的網頁裡：建立 App、勾權限、按發行 token、
開 webhook。接上瀏覽器能力之後，Agent 和使用者看的是同一個畫面，可以直接說
「左邊選單第三項」並確認他點對了。

沒接也做得完，只是每個畫面都要使用者自己描述或截圖回報，來回次數多很多，也更容易在
「我以為你點的是那個」上卡住。

**所以預設要主動幫使用者接起來，不是等他卡住才提。** 這份 Skill 不綁定任何單一
Agent；接不接、用哪一種，最後由使用者決定。

## 兩條路都是 MCP，差別在接哪個瀏覽器

使用者常誤以為「擴充」和「MCP」是兩件事。實際上兩條路的工具都是透過 MCP 到達
Agent 的（例如 Claude 擴充在工具清單裡是 `mcp__claude-in-chrome__*`）。真正要幫
使用者判斷的是**接到哪一個瀏覽器**：

| | Claude 瀏覽器擴充 | Playwright MCP |
|---|---|---|
| 接管的瀏覽器 | 使用者**現在正在用、已經登入**的 Chrome | **另外開**一個乾淨的瀏覽器 |
| 登入狀態 | 沿用，不必重登平台後台 | 沒有，要在那個瀏覽器重新登入一次 |
| Agent 看得到的範圍 | 同一個 Chrome 裡的其他分頁也在範圍內 | 只有它自己開的那一個 |
| 安裝方式 | Chrome 線上應用程式商店 | `claude mcp add` ／ `codex mcp add` ／ MCP 設定檔 |

不要用「這個才是 MCP」當理由推薦其中一邊。要講的是取捨：怕重登就用擴充，
怕 Agent 看到無關分頁就用 Playwright MCP。

## 四層判斷（照順序，不要跳）

### 第一層：先看你自己有沒有瀏覽器能力

**這一層由 Agent 自己判斷，不要問使用者，也不要先叫他安裝任何東西。**

檢查你目前可用的工具清單裡，有沒有名稱含下列關鍵字的工具：

~~~text
browser / chrome / playwright / puppeteer / webdriver / computer
~~~

工具要先載入才看得到完整定義的環境（例如有工具搜尋機制的 Agent），先查一次再判定沒有。

- **有** → 跳到「連線 smoke」。但要**講出來**你打算用哪一個，例如
  「我這邊有 Chrome 瀏覽器工具，等一下我用它陪你開 LINE Developers Console」。
  不要默默使用，使用者有權知道 Agent 會看到他的瀏覽器畫面。
- **有但受限**（例如只能讀不能點、不能跨分頁、被沙箱擋住）→ 說明限制，
  再依第二層提供可補足的 MCP 選項，讓使用者決定要不要加裝。
- **沒有** → 進第二層。

### 第二層：沒有就主動帶他接（給指令，不是只丟連結）

你在自己的系統設定裡就知道自己是誰，不需要偵測使用者的環境變數或資料夾。
照下表選一條，把指令與連結一起給，並說明**裝完要重新啟動 Agent 才會出現工具**。

| 你是 | 帶使用者做什麼 |
|---|---|
| Claude Code | 二選一。要沿用他已經登入的 Chrome → 裝 [Claude 瀏覽器擴充](https://chromewebstore.google.com/detail/claude/fcoeoabgfenejglbffodgkkbkcdhcgfn)（步驟見 [官方說明](https://support.claude.com/en/articles/12012173-getting-started-with-claude-for-chrome)）。要獨立、不動到他原本的瀏覽器 → 接 Playwright MCP：`claude mcp add playwright npx @playwright/mcp@latest` |
| Codex CLI | 接 Playwright MCP：`codex mcp add playwright -- npx @playwright/mcp@latest` |
| 其他支援 MCP 的 Agent（Cursor、Cline、VS Code 外掛等） | 依該 Agent 的 MCP 設定檔加入 [Playwright MCP](https://github.com/microsoft/playwright-mcp)，標準寫法是 `{"mcpServers": {"playwright": {"command": "npx", "args": ["@playwright/mcp@latest"]}}}` |

上面兩條 CLI 指令與 JSON 寫法都取自官方文件；若執行後報錯或選項不同，**以
[Playwright MCP 官方 repository](https://github.com/microsoft/playwright-mcp) 當下的
說明為準**，不要自己改參數硬試。

Claude 瀏覽器擴充在官方說明頁列為付費方案功能；條件以該頁當下內容為準。
使用者不符合條件時不要卡住，直接改用 Playwright MCP 或走第四層。

### 第三層：認不出自己是哪個 Agent，或使用者想自己選 → 全給

把三條路徑一次列出來讓使用者挑，不要猜：

| 想要的效果 | 官方來源 | 適合誰 |
|---|---|---|
| 用他已經登入的 Chrome，直接接手後台分頁 | [Claude 瀏覽器擴充](https://chromewebstore.google.com/detail/claude/fcoeoabgfenejglbffodgkkbkcdhcgfn) ＋ [官方說明](https://support.claude.com/en/articles/12012173-getting-started-with-claude-for-chrome) | 用 Claude 產品，且希望沿用現有登入狀態 |
| 跨 Agent 通用的瀏覽器自動化，開獨立瀏覽器不動原本的 | [Microsoft Playwright MCP](https://github.com/microsoft/playwright-mcp) | 任何支援 MCP 的 Agent |
| 另外要看 console 訊息或網路請求 | [Chrome DevTools MCP](https://github.com/ChromeDevTools/chrome-devtools-mcp) | 需要排查前端錯誤或抓 API 回應時的補充選項 |

只給這三個網址。不要補上未經查證的擴充、映像站、第三方套件或安裝命令。

### 第四層：不想裝，或環境不支援 → 逐步口述 fallback

使用者拒絕安裝、公司環境禁止、或目前 Agent 不支援時，**不要卡住也不要重複勸說**，
直接改走本檔最後一節的逐步口述流程。這條路一樣能完成所有憑證關卡，只是慢一些。
之後也不要每個畫面都再問一次要不要裝。

## 連線 smoke

拿到瀏覽器能力後，先做一次不需登入的驗證再進後台：

1. 開啟一個公開頁面（例如平台的官方文件頁），讀回頁面標題。
2. 向使用者確認：這個瀏覽器環境只開放這次任務需要的分頁。

讀不回標題就當作沒有瀏覽器能力，回到第四層，不要反覆重試。

安裝瀏覽器能力本身不是建立 App、channel 或憑證的批准。完成連線 smoke 後，
仍要在每個外部副作用前重新取得批准。

## 後台陪走節奏

1. Agent 先說明目前要進入的畫面、目的及通過證據。
2. 使用者自行完成登入、密碼、驗證碼及帳號切換。
3. Agent 只讀取完成本步必要的畫面文字；不先探索整個帳號。
4. 碰到建立、同意、發行、重發、公開、部署、計費或真實發布按鈕時先停下。
5. 使用者批准後只執行該次動作，隨即以遮罩後 read-back 或平台回讀驗證。
6. 同一步找不到或失敗三次就停止操作，改讀當下官方文件與實際畫面文字；
   不從記憶猜 UI 名稱、API 版本、權限、參數或配額。

## 安全紅線

瀏覽器擴充或瀏覽器 MCP 可能看見同一個瀏覽器環境中其他已登入分頁。開始前，
先關閉或移出所有與本次任務無關的分頁；最好使用專用瀏覽器設定檔或獨立視窗，
只開這次需要的 LINE Developers Console 的 Provider、channel 與 webhook 後台。

用 Playwright MCP 這類會另開瀏覽器的方案時，預設就是乾淨環境，這一條的風險較低，
但仍要向使用者說明 Agent 看得到什麼。

Agent 只可操作使用者明確指定的後台分頁，不得打開或瀏覽信箱、密碼管理器、
金流、私人社群、雲端硬碟或其他帳號頁面。帳號、密碼、驗證碼與恢復碼一律由
使用者親自輸入。

token 或 secret 產生後，不得要求使用者貼進對話、不得讀出完整值、不得截取
完整後台；只確認欄位名稱、遮罩後的末幾碼，以及是否已直接存入環境變數或
secret store。

建立 App、Provider 或 channel、接受條款、變更權限、發行或重發 token／secret、
切換正式模式、開啟 webhook、建立公開資源、部署、啟用計費，以及任何真實發文
或推播，都必須在點擊前停下，說明這次動作會改變什麼，並取得只適用於該次動作
的明確批准。

若瀏覽器工具無法限制分頁、畫面出現本次任務不需要的敏感資料，或無法確認目前
操作的是哪個帳號，立即停止自動操作，改成一次一個畫面的逐步口述。不得把
「已登入」或「按鈕看得到」當成憑證完成；必須再以遮罩後 read-back 及平台或
API 的實際回讀驗證。

## 逐步口述 fallback

每次只輸出：

~~~text
目前畫面：[頁面名稱]
現在做：[一個動作]
請不要貼出：[密碼／驗證碼／token／secret]
完成後回報：[一個非敏感結果，或裁切並遮罩後的截圖]
~~~

使用者回報前不預先給後續五個畫面，也不假裝已看到後台。
