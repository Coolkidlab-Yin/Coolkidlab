---
name: ig-news-bot
description: >
  AI / 股市新聞 IG 自動發文 bot 建置教學。當使用者想做「IG 自動發文」
  「新聞圖卡 bot」「RSS 監測自動發社群」,或提到 兩階 LLM 內容管線/
  便宜模型篩選+貴模型寫稿/Pillow 自動生圖發 IG 時使用。
  也適用於「不知道 IG API token 怎麼申請」「Meta 開發者後台看不懂」
  這類卡在憑證的求助 —— 本 skill 會開瀏覽器陪使用者一頁一頁走完申請。
  核心設計:事件驅動(有大事才發,沒大事安靜)+ 兩階 LLM 分工省 token
  + IG API 只收公開圖片 URL 的實戰坑。
  Use when the user wants an automated Instagram news/content bot, or is
  stuck getting Instagram API credentials.
---

# IG 新聞自動發文 bot(ig-news-bot)

## 什麼時候用

- 想做一個「監測 RSS 新聞 → 自動寫稿 → 自動生圖 → 自動發 IG」的 bot
- 想學「兩階 LLM 分工」:便宜模型做篩選、貴模型做精工,把 token 花在刀口上
- 被 IG Graph API 發圖卡住(本機圖檔怎麼傳都失敗)
- 想避免「定時硬發」把帳號變成雜訊 — 這套是事件驅動:有大事才發

## 架構總覽

### 為什麼是事件驅動,不是定時發

IG 演算法明確偏好圖文,純文字觸及超差 — 但更難的是「該發什麼」。
定時排程最大的問題:沒新聞的日子它還是會發,為了填時段就挑一則沒人在乎的
新聞硬寫,發久了帳號就變雜訊。所以這個 bot 每 30 分鐘掃一次,
但只有夠重要的新聞才會變成貼文 — 有大事才發,沒大事就安靜。

### 六段 pipeline

```
collectors → importance_scorer → dedup → writer → image_gen → publisher
 (抓 RSS)     (評重要性分數)    (去重)   (寫文案)  (Pillow生圖)  (發 IG)
```

### 兩階 LLM 分工(核心省錢設計)

| 階段 | 模型 | 工作 | 特性 |
|---|---|---|---|
| 第一階 | Claude Haiku(便宜) | 一次掃最多 30 則新聞,每則評重要性分數 | 量大、篩選 |
| 第二階 | Claude Opus(貴) | 只有過閾值的新聞,用使用者的口吻寫成貼文 | 量小、精工 |

為什麼省:Haiku 一次 input 約 $0.0008、Opus 約 $0.015,差 20 倍(原作者 2026 年當時的量級,實際以官方定價頁為準 — 重點是「分工差一個數量級」這個結構,不是確切數字)。
一天 100 則新聞先丟 Haiku 過濾掉 90 則,只剩 10 則丟 Opus 寫稿,
總成本是「100×Haiku + 10×Opus」,遠低於「100×Opus」— 約全程用
Opus 的 1/10,月省約 $50-80。

### 生圖為什麼用 Pillow 不用 Canva

Pillow 是程式自動 render,跑排程沒人介入;Canva 要人手動拖,接不進
workflow。只發少量、可接受手動的話 Canva 也行,但這套的重點是「自動」。

## 照步驟做

依序引導使用者完成,每完成一步先停下來確認再繼續。

### 第 0 步:確認環境

先問清楚,缺一項就先補:

- 作業系統與 Python 版本(需要 3.9 以上)
- 套件:`pip install anthropic pillow feedparser requests python-dotenv`
- 一台「會一直開著」的機器 — 這個 bot 每 30 分鐘要跑一次。自己的電腦
  關機就停,長期跑建議放小型 VPS 或任何免費排程服務
- 一個有中文的字型檔(Pillow 預設字型不含中文)。**不用他自己找**,
  第 5 步的程式會從候選清單自動偵測,偵測不到才需要他補一個路徑。

**接下來三把鑰匙,使用者通常一把都沒有。不要問「你有沒有」,
直接帶他去申請 —— 第 0.5 步就是在做這件事。**

### 第 0.5 步:開瀏覽器,陪使用者把三把鑰匙拿到手

這步最久(抓 30 分鐘),也是最多人在這裡放棄的地方。
**不要只丟一串網址叫他自己去弄。開瀏覽器,陪他一頁一頁走。**

各家後台改版很勤,任何寫死的點擊步驟過幾個月就對不上。所以這份文件
只定義「要拿到什麼」和「怎麼確認拿對了」,實際畫面長怎樣、按鈕在哪,
由你當場開瀏覽器看著辦。

#### 先確認你有沒有瀏覽器能力

1. **有瀏覽器工具**(能開網頁、讀畫面、點選)→ 直接用,跳到下一段。
2. **沒有** → 先花三分鐘讓使用者裝起來,這比讓他自己摸索後台省事得多:
   - 跟他說明白:裝了之後,你就能看到他螢幕上的那個分頁,可以告訴他
     「現在畫面上那顆藍色按鈕就是,點它」,而不是叫他在幾十個選單裡找。
   - 引導他安裝 **Claude 的 Chrome 擴充功能**(Chrome 線上應用程式商店
     搜尋 Claude)。裝完在擴充功能裡登入同一個帳號,並對要操作的網站
     開啟權限。
   - **先確認他符合條件再叫他去裝**,不然白忙一場:需要付費方案
     (免費方案不能用),而且只支援正牌 Chrome —— Edge、Brave、Arc
     這些 Chromium 分支不支援。這功能仍在 beta,細節以官方說明為準。
   - 裝好後帶他實驗一次:請他隨便開一個網頁,你描述一下看到什麼,
     讓他確認這個工具真的通了 —— **順便讓他學會這個工具,後面很多事
     都用得到**,不只是這次申請。
3. **兩者都沒有**(例如純終端機環境)→ 退回口述模式:一次只講一步,
   每步問他「畫面上看到什麼」,用他的回答決定下一句怎麼講。
   不要一次倒十個步驟給他。

#### 陪跑的規矩(這幾條不能破)

- **帳號、密碼、驗證碼一律他自己打。** 你不代填、不代讀。
- **送出、同意條款、建立應用程式、產生金鑰這類按鈕,由他按。**
  你負責告訴他按哪顆、按下去會發生什麼。
- **拿到的 token 和 key 不要貼進對話。** 直接請他貼進 `.env`。
  你要驗證的話,叫他跑驗證指令,你看指令的輸出就好。
- **叫他不要截整個畫面貼給你。** 沒有瀏覽器工具時他一定會想截圖,
  而 App Secret、token 就在那個畫面上。要看的話請他先遮住,
  或改成用文字描述「我現在看到哪些選項」。
- 你的角色是導遊不是代駕:看畫面、講下一步、確認結果對不對。
- **卡住的出口**:同一步試三次還找不到按鈕,不要繼續猜。改做這三件事之一 ——
  請他描述整個畫面上有哪些字、去查該服務的官方文件看現在的畫面長怎樣、
  或先跳過這把鑰匙去拿另一把,回頭再處理。**不要讓他在同一個畫面卡超過十分鐘**,
  那是多數人放棄的地方。

#### 三把鑰匙:要拿到什麼才算數

一把一把拿,每拿到一把就當場驗證再往下,不要三把一起弄。

**先跟他講清楚 `.env` 是什麼,以及它不會自己生效。** `.env` 只是一個
純文字檔,一行一個 `名稱=值`,放在專案資料夾裡。程式**要主動去讀它**
才會生效 —— 這是這一步最常見的卡點:key 明明貼進 `.env` 了,驗證指令
卻說沒有 key,使用者以為 key 拿錯,其實是沒人載入。

所以驗證的時候二選一,先跟他約好用哪一種:

```python
# 方法 A(推薦,之後正式程式也這樣寫):程式開頭載入 .env
from dotenv import load_dotenv   # pip install python-dotenv
load_dotenv()                    # 之後 os.environ 才讀得到 .env 裡的東西
```

```bash
# 方法 B:這次先不用 .env,直接在這個終端機視窗設環境變數
# (關掉視窗就沒了,只適合當下驗證)
export ANTHROPIC_API_KEY=xxx      # macOS / Linux / Git Bash
$env:ANTHROPIC_API_KEY="xxx"      # Windows PowerShell
```

下面三把鑰匙的驗證指令都假設環境變數已經生效(用上面任一種方法)。

**鑰匙 1|Claude API key**(約 5 分鐘)

- 去哪:Anthropic 的 API 主控台(console.anthropic.com)
- 拿到什麼:一組 API key
- **先提醒他要儲值** —— 新帳號沒有免費額度,沒儲值一呼叫就失敗,
  很多人卡在這裡以為是自己程式寫錯
- 存成 `ANTHROPIC_API_KEY`
- 驗證:

  ```bash
  python -c "import anthropic;print(anthropic.Anthropic().models.list().data[0].id)"
  ```

  印出一個模型 ID 就對了。

**鑰匙 2|圖床 API key**(約 5 分鐘)

- 為什麼要:IG 發圖只吃公開網址,不吃本機圖檔(見踩坑段),中間一定要有圖床
- 去哪:任何有 API 的免費圖床都行(imgbb 是常見選擇)
- 存成 `IMGBB_API_KEY`
- **先講清楚再讓他決定**:免費圖床上傳的圖是公開的,拿到網址的人都看得到。
  發 IG 的圖本來就要公開所以沒差,但別拿同一組流程傳私人照片。
- 驗證(傳一張測試圖,拿回網址):

  ```bash
  python -c "import os,requests,base64;print(requests.post('https://api.imgbb.com/1/upload',data={'key':os.environ['IMGBB_API_KEY'],'image':base64.b64encode(open('test.png','rb').read())}).json()['data']['url'])"
  ```

  印出一個網址、而且那個網址在瀏覽器打得開就對了。
  (`test.png` 隨便一張圖都行;換別家圖床的話 endpoint 要跟著換。)

**鑰匙 3|IG 發文憑證**(約 20 分鐘,最容易卡)

先讓他選路線 —— 選錯的話後面權限名稱全對不上:

| | A. Instagram 登入(多數人選這個) | B. Facebook 登入 |
|---|---|---|
| 要不要粉絲專頁 | **不用** | 要,IG 必須連一個粉專 |
| 權限名稱 | `instagram_business_basic`<br>`instagram_business_content_publish` | `instagram_basic`<br>`instagram_content_publish`<br>`pages_read_engagement`<br>(若使用者的粉專角色來自商務管理平台,另需 `ads_management`、`ads_read`) |
| API 主機 | `graph.instagram.com` | `graph.facebook.com` |

只想自己發文、沒有粉專 → 走 A。

**要達成的狀態**(照順序,每項達成再往下):

1. 他的 IG 是**專業帳號**(商業或創作者)。個人帳號不能用 API 發文,
   在 IG App 的設定裡免費切換。
2. 在 Meta 的開發者後台建好一個應用程式,加入 Instagram 相關產品。
3. 權限已勾選(照上表選的路線)。**自用不必送 App Review**,
   要開放給別人用才需要送審 —— 先講,免得他以為要等審核。
4. 走完授權流程拿到 token,並**換成長期 token**(短期的很快過期)。
5. 拿到自己的 IG 使用者 ID(後面發文要用)。

過程中他會看到「App Secret」。**提醒他:這東西等同密碼,只能放在自己
機器上,不要貼進任何網頁、不要進版控、不要貼給你。**

**驗證拿對了**(這條由他在終端機跑,你看輸出。**不要叫他把網址貼進瀏覽器**
—— token 會留在瀏覽器歷史紀錄裡):

```bash
curl -s "https://graph.instagram.com/v25.0/me?fields=user_id,username&access_token=$IG_ACCESS_TOKEN"
```

Windows PowerShell 沒有 curl 的話用這條:

```powershell
python -c "import os,requests;print(requests.get('https://graph.instagram.com/v25.0/me',params={'fields':'user_id,username','access_token':os.environ['IG_ACCESS_TOKEN']}).text)"
```

回傳 `{"user_id":"...","username":"他的帳號名"}` 就代表憑證正確。

**要的是 `user_id` 不是 `id`。** 這兩個是不同的東西:`id` 是 app-scoped ID,
拿去當發文用的 `<IG_USER_ID>` 會失敗,而且錯誤訊息不會告訴你是這個原因。

token 錯或過期時,**HTTP status 是 400 不是 401**,要看回應內容裡的
`error.code == 190` 來判斷,不要靠 status code 判。
遇到就**停在這裡把它弄對,不要往下走** —— 不然後面每一步都會失敗,
而且錯誤訊息看起來跟 token 完全不相干。

> 上面的網址與參數以 Meta 官方文件為準。後台畫面會改版,API 也可能升版本,
> 對不上的時候以你當場在官方文件看到的為準,不要硬套這份文件。

#### 收尾:三把鑰匙都進 .env

```
ANTHROPIC_API_KEY=...
IMGBB_API_KEY=...
IG_ACCESS_TOKEN=...
IG_USER_ID=...
```

順手建一個 `.env.example`(只放欄位名不放值)進 repo,
再把 `.env` 寫進 `.gitignore`。**幫他確認 `.env` 真的被 ignore 了**
(`git check-ignore -v .env` 有輸出就對了)—— 這是最常見的外洩方式。

### 第 1 步:collectors(抓 RSS)

RSS 來源分三類:AI、台股、美股。每 30 分鐘掃一次(排程見第 7 步)。

### 第 2 步:importance_scorer(Haiku 評分)

用便宜的 Claude Haiku 一次掃最多 30 則,幫每則新聞評重要性分數。
設定閾值 — 只有超過閾值的才進下一階。

### 第 3 步:dedup(去重)

把發過的新聞 key 記在 jsonl,發前比對,避免重複發同一則。
去重要可靠,這是防洗版的底線。

### 第 4 步:選發規則(配額 + 防洗版)

用程式寫死規則,不要每次臨場判斷:

- AI 類:達閾值的全發,但同一次最多 2 則(不洗版)
- 台股 / 美股:各取分數最高的幾則,當天保底,但同類當天已發過就跳過

這樣結果可控:不會某天突然暴發 10 則,也不會真正的大新聞被漏掉。
自動化的重點不是「全交給 AI」,是「把判斷標準寫成規則,讓它穩定執行」。

### 第 5 步:writer(Opus 寫稿)+ image_gen(Pillow 生圖)

- writer:只有過閾值的新聞交給 Claude Opus,用使用者的口吻寫成貼文文案
- image_gen:Pillow 生 1080x1080 的圖,放標題、分數、logo

**中文字型一定要明講,不然第一張圖的中文不會正常顯示**(通常是空白或方框)。
Pillow 的 `ImageFont.load_default()` 載的是拉丁字型,不含中文。
一定要用 `ImageFont.truetype()` 指定一個真的有中文的字型檔:

```python
# Windows:微軟正黑體,Windows 10/11 預設就有(不分語系版本)
font = ImageFont.truetype("C:/Windows/Fonts/msjh.ttc", 48)
```

**不要在程式裡寫死單一路徑。** 系統更新會搬字型、改檔名(macOS 尤其明顯,
Apple 自己也不建議用路徑找字型),而且你不知道使用者是哪個作業系統。
改用「候選清單 + 存在才用 + 找不到就明確報錯」:

```python
from pathlib import Path
CANDIDATES = [
    "C:/Windows/Fonts/msjh.ttc",
    "/System/Library/Fonts/PingFang.ttc",
    "/System/Library/Fonts/STHeiti Light.ttc",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
]
path = next((p for p in CANDIDATES if Path(p).exists()), None)
if path is None:
    raise SystemExit("找不到中文字型,請在 CANDIDATES 補一個你系統上有的字型檔路徑")
font = ImageFont.truetype(path, 48)
```

先叫使用者跑一次「只生一張圖、打開來看」,親眼確認標題是中文,再往下接發文。

### 第 6 步:publisher(發 IG)

流程必須是:Pillow 本機生圖 → 上傳到圖床(如 imgbb)拿公開 URL →
把 URL 丟給 IG API 發。千萬別直接傳本機路徑(見踩坑段)。
同時排好 token refresh,失敗時要記錄,不要無聲無息。

發文是**兩段式**,不是一次呼叫(以 Instagram 登入路線為例):

```
# 1. 先建一個「容器」,把圖片網址和文案交給 IG
POST https://graph.instagram.com/v25.0/<IG_USER_ID>/media
     ?image_url=<圖床公開網址>&caption=<文案>&access_token=<token>
     → 回傳 {"id": "<容器 ID>"}

# 2. 再把容器發出去
POST https://graph.instagram.com/v25.0/<IG_USER_ID>/media_publish
     ?creation_id=<容器 ID>&access_token=<token>
     → 回傳 {"id": "<貼文 ID>"}
```

兩段之間 IG 要時間去抓那張圖。官方建議的做法是查容器狀態、**每分鐘查一次、
最多查 5 分鐘**,備妥了再發:

```
GET https://graph.instagram.com/v25.0/<容器 ID>?fields=status_code&access_token=<token>
```

**額度**:同一個 IG 帳號在滾動的 24 小時內,最多用 API 發 100 篇。
這套是事件驅動、一天幾則,正常不會撞到,但寫重試邏輯時別無限重打。

### 第 7 步:dry-run 先跑,確認再開真發

一定要做 --dry-run 模式:照跑抓新聞、評分、寫稿、生圖,但不真的發 —
圖存到 `logs/preview/`、文案存成草稿檔,人先看過再開真發。
新手前 2 週建議全 dry-run。另外做一個 --force 方便測試。

排程:Windows 用工作排程器每 30 分鐘跑一次(其他平台用 cron 同理)。

**四個檢查點,過了才算真的做完**:

1. `python -c "import anthropic..."` 印出模型 ID → Claude 鑰匙對了
2. `GET /me` 回傳你的 IG 帳號名 → IG 鑰匙對了
3. dry-run 跑完,`logs/preview/` 裡有一張圖,**打開看得到中文標題**
   (不是空白也不是方框),
   草稿檔裡有一段像人寫的文案 → 產線通了
4. 關掉 dry-run 發第一篇,IG App 上真的看得到 → 全線通了

第 3 點沒過就不要開真發。

## 我踩過的坑

1. **IG Graph API 只收「公開 URL」,不收本機圖檔** — 這段卡最久。
   它不吃你本機的圖檔,要一個公開可存取的圖片 URL,所以一定要先過圖床。
   第一次不知道,直接傳本機路徑怎麼試都失敗,查半天才發現是這個設計。
2. **Meta 的 token 會過期,而且是「靜默不發」** — API 其實有回錯
   (HTTP 400、`error.code` 190),但如果你的程式沒有把發文失敗記下來、
   沒有通知你,從外面看就是某天默默停了。長期 token 是 60 天,
   要排 refresh,**而且發文失敗一定要留紀錄並告警**,不然壞掉你不會知道。
3. **Pillow 預設字型不含中文** — 第一張圖的中文顯示不出來(空白或方框),
   新手看到這個通常會以為是自己程式寫錯。指定一個有中文的字型檔就好,
   而且不要寫死路徑(見第 5 步)。
4. **定時硬發 = 帳號變雜訊** — 寫死「每天 18:00 發一則」,沒大事的日子
   就會硬擠一則不重要的,久了 follower 只覺得吵。改成事件驅動才解。
5. **洗版控制要寫成程式規則** — 靠臨場判斷不穩定,配額寫死才可控。

## 紅線與注意

- **AI 揭露警語**:每篇貼文結尾自動帶一句說明「此貼文由 AI 自動產出,
  作為自己的資訊蒐集與觀點記錄」— 不假裝是純人工。
- **不碰投資建議**:發文只做工具本身,文案裡不寫任何買賣結論或操作建議。
- **secrets 不落地**:IG token、Claude API key、圖床 key 一律走環境變數
  或秘密管理工具,不硬編碼、不 commit。
- **先 dry-run 再真發**:自動發文最怕「發出去才發現寫爛或圖醜」,
  預覽機制不是選配。
