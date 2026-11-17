# HTTP 快取入門 · LLM Wiki

從圖片請求學會辨識直接重用、成功驗證與取得新版。

## 概念索引

- [K01 · HTTP 快取與副本](concepts/K01.md) ｜快取存了什麼，能省下什麼？ 搜尋詞：快取 副本 GET 200 HTTP 請求 回應 瀏覽器
- [K02 · 新鮮度與 max-age](concepts/K02.md) ｜副本在什麼條件下可直接重用？ 搜尋詞：fresh stale 60 秒 max-age Age 重載 重新整理
- [K03 · 條件式請求與 304](concepts/K03.md) ｜副本過期後，瀏覽器如何確認版本？ 搜尋詞：ETag If-None-Match 驗證 304 200 過期 GET status
- [K04 · Cache-Control 指令比較](concepts/K04.md) ｜可重用、先驗證、不可儲存有何差別？ 搜尋詞：Cache-Control max-age no-cache no-store 指令 儲存
- [K05 · 用 Chrome DevTools 檢查](concepts/K05.md) ｜怎麼在瀏覽器找出快取的線索？ 搜尋詞：Network Chrome DevTools Headers Preserve log Disable cache 開發者 工具 實作

## 來源索引

- [S01 · RFC 9111 · HTTP Caching](sources/S01.md) ｜規範 HTTP 快取的儲存、重用、期限及驗證。以它確認規則與適用條件。
- [S02 · RFC 9110 · HTTP Semantics](sources/S02.md) ｜定義 HTTP 驗證標記、條件式請求及狀態碼。用於查對欄位的方向與 304 的內容。
- [S03 · HTTP caching](sources/S03.md) ｜用實例解釋快取、期限和驗證，也提醒瀏覽器重新整理可能改變請求行為。
- [S04 · HTTP conditional requests](sources/S04.md) ｜以一連串請求展示首次取得資源、使用副本、驗證舊版與下載新版。
- [S05 · Network features reference](sources/S05.md) ｜Chrome 開發者工具的操作參考。用它定位快取開關、網路請求紀錄及 HTTP 標頭。

[Ingest／Query／Lint 日誌](log.md)
