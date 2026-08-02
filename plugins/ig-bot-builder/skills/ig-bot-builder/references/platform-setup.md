# Instagram 平台設定與發布邊界

只在需要憑證、公開圖片或 Meta publisher 時讀本檔。UI 與參數會改版，
執行 Agent 應以官方文件與實際回應補完，不照抄固定版本。

## 憑證陪走

- 先使用現有瀏覽器能力；沒有就逐步口述，不要求特定 Agent 擴充功能。
- 帳密、驗證碼由使用者輸入；建立 App、同意條款、產生 key/secret 由使用者確認。
- token/secret 不貼對話、不截完整後台，直接存環境變數或 secret store。
- 每取得一項就做遮罩後 read-back；同一步卡三次就查官方文件，不再猜。

先選官方支援的登入路線。Instagram Login 與 Facebook Login 的帳號連結、
權限、API host 可能不同；依使用者帳號型態與當下文件選一條，不混用 scope。
確認 IG 是官方支援發文的專業帳號，取得正確的 IG user id，並以 /me 類端點
回讀 username。不要只憑 `id` / `user_id` 欄位名稱推定物件身分；記錄取得端點、
欄位與物件類型，並用遮罩後的帳號回讀確認「使用者 → 專頁 → IG 帳號」映射。

token 錯誤不一定回 401；保存 Meta error code/type/subcode，再依官方文件分類。

## 圖片與媒體

圖片發布通常要求 Meta 能匿名抓取的公開 HTTPS URL，不接受本機路徑。
公開 URL 必須：

- 不需要 cookie、登入、IP allowlist 或短到來不及抓取的簽名。
- 回正確 MIME、合理大小與平台支援的尺寸/格式。
- 不放私人照片、未發布敏感素材或使用權不明內容。
- 記錄託管供應商、到期時間與刪除方式。

若供應商或現有 CDN 不合適，由 Agent 提出候選與取捨，取得同意後再建立資源；
Skill 不指定 imgbb、S3 或其他唯一答案。

## Container 與 publish

單張圖片通常是建立 media container、輪詢處理狀態、再 media_publish。
輪播依目前官方結構，先為每個 child 建立帶 is_carousel_item=true 的 container，
再以 media_type=CAROUSEL 與 children 建立父 container；caption 放父層，
最後發布父 container。張數、媒體組合與完整參數仍以當下官方文件為準。

adapter 必須保存所有 container id/status history；只在官方可發布狀態進 publish。
輪詢使用 bounded backoff、總 timeout 與 terminal failure；4xx 不盲重試。
發布前再次驗 approval、idempotency、用量與 token health。

## 官方來源（查證：2026-08-02）

- [Meta：Instagram Platform](https://developers.facebook.com/docs/instagram-platform/)
- [Meta：Instagram API with Instagram Login](https://developers.facebook.com/docs/instagram-platform/instagram-api-with-instagram-login/)
- [Meta：Instagram API with Facebook Login](https://developers.facebook.com/docs/instagram-platform/instagram-api-with-facebook-login/)
- [Meta：Content Publishing](https://developers.facebook.com/docs/instagram-platform/content-publishing/)
- [Pillow：ImageFont](https://pillow.readthedocs.io/en/stable/reference/ImageFont.html)

每次實作或上線前重查 API version、scope、帳號資格、媒體限制、發布用量與
token 規則，並把日期和選用登入路線寫進交付紀錄。
