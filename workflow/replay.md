# 再執行與驗收

## 時間與來源

- `ingest.json` 記錄 5 份 HTTP 回應的收件時間、實際 URL、回應標頭、內容大小、完整快照路徑及 SHA-256。其 `received_taipei` 與 `received_utc` 是同一瞬間。
- `clock-check.json` 保存重跑前後和 GitHub、Cloudflare 的新鮮 HTTPS 回應時鐘比對。來源文件的 Date 欄位可能由中介快取提供，實際收件時間由擷取程式記錄。
- `scope.md` 記錄使用者確認範圍及本次更新的先後順序。

## 在自己的電腦重跑

需要 Python 3.10 以上及已安裝的 Google Chrome。在 ZIP 解壓出的資料夾執行：

```text
python -m pip install beautifulsoup4 playwright
python workflow/verify_clock.py before
python workflow/ingest.py
python workflow/check_content.py
python workflow/build.py
python workflow/check_browser.py --capture evidence
python workflow/verify_clock.py after
```

`ingest.py` 用新時間戳命名快照子資料夾。Chrome 檢查會驗證四種視窗與本機 HTTP 快取情境，產生 PNG 與逐檔 SHA-256。重跑前若要保留舊驗收，先另存原 ZIP。

線上部署的匿名測試見 `public-check.json`。在本地 HTML 與部署版本相同時，可重跑：

```text
python workflow/check_public.py https://ytomfang.github.io/http-cache-llm-wiki/
```
