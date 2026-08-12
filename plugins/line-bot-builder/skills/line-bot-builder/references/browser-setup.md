# LINE 後台瀏覽器陪走

建立平台憑證通常需要登入後台。優先使用可互動的瀏覽器能力，讓 Agent 一次帶
一個畫面；這份 Skill 的工程契約不依賴任何單一 Agent，沒有瀏覽器能力時仍可
安全改用逐步口述。

## 四層判斷（照順序，不要跳）

### 第一層：先看你自己有沒有瀏覽器工具

**這一層由 Agent 自己判斷，不要問使用者，也不要叫他安裝任何東西。**

檢查你目前可用的工具清單裡，有沒有名稱含下列關鍵字的工具：

~~~text
browser / chrome / playwright / puppeteer / webdriver / computer
~~~

有 → 直接用現成能力，跳到「連線 smoke」。少數 Agent 的工具要先載入才會出現
完整定義；若你的環境有工具搜尋機制，先查一次再判定沒有。

沒有 → 進第二層。

### 第二層：你知道自己是哪個 Agent，就給對應路徑

你在自己的系統設定裡就知道自己是誰，不需要偵測使用者的環境變數或資料夾。
照下表選一條，把安裝連結給使用者，並說明裝完要重新載入才會出現工具。

| 你是 | 給使用者的官方路徑 |
|---|---|
| Claude Code、Claude 桌面版或其他 Claude 產品 | [Claude Chrome 擴充](https://chromewebstore.google.com/detail/claude/fcoeoabgfenejglbffodgkkbkcdhcgfn)；安裝與授權步驟見 [Anthropic 官方說明](https://support.claude.com/en/articles/12012173-getting-started-with-claude-for-chrome) |
| 其他支援 MCP 的 Agent（Codex、Cursor、Cline 等） | [Microsoft Playwright MCP](https://github.com/microsoft/playwright-mcp)，依該 repository 當下的 client 設定方式安裝 |

不要從本檔複製固定的安裝命令或設定格式；官方 repository 的設定方式會改，
請使用者以連結內當下的說明為準。

Claude 瀏覽器擴充在官方說明頁列為付費方案功能；條件以該頁當下內容為準。
使用者不符合條件時不要卡住，直接改走第三層或第四層。

### 第三層：認不出自己是哪個 Agent，或使用者想自己選 → 全給

把三條路徑一次列出來讓使用者挑，不要猜：

| 想要的效果 | 官方來源 | 適合誰 |
|---|---|---|
| 用你已經登入的 Chrome，直接接手後台分頁 | [Claude Chrome 擴充](https://chromewebstore.google.com/detail/claude/fcoeoabgfenejglbffodgkkbkcdhcgfn) ＋ [官方說明](https://support.claude.com/en/articles/12012173-getting-started-with-claude-for-chrome) | 用 Claude 產品，且希望沿用現有登入狀態 |
| 跨 Agent 通用的瀏覽器自動化 | [Microsoft Playwright MCP](https://github.com/microsoft/playwright-mcp) | 用任何支援 MCP 的 Agent |
| 另外要看 console 訊息或網路請求 | [Chrome DevTools MCP](https://github.com/ChromeDevTools/chrome-devtools-mcp) | 需要排查前端錯誤或抓 API 回應時的補充選項 |

只給這三個網址。不要補上未經查證的擴充、映像站、第三方套件或安裝命令。

### 第四層：不想裝，或環境不支援 → 逐步口述 fallback

使用者拒絕安裝、公司環境禁止、或目前 Agent 不支援時，**不要卡住也不要重複勸說**，
直接改走本檔最後一節的逐步口述流程。這條路一樣能完成所有憑證關卡，只是慢一些。

## 連線 smoke

拿到瀏覽器能力後，先做一次不需登入的驗證再進後台：

1. 開啟一個公開頁面（例如平台的官方文件頁），讀回頁面標題。
2. 向使用者確認：這個瀏覽器環境只開放這次任務需要的分頁。

讀不回標題就當作沒有瀏覽器能力，回到第四層。

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
