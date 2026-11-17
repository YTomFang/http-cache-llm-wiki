# HTTP 快取入門的執行與驗收

| 紀錄 | 可查核的內容 |
| --- | --- |
| [需求與對話節錄](scope.md) | 範圍確認及重新更新 Wiki 的順序 |
| [外部時鐘比對](clock-check.json) | 重跑前後的 UTC／臺灣時間，及 GitHub 和 Cloudflare 即時回應 |
| [五份擷取紀錄](ingest.json) | 完整回應的實際時間、URL、HTTP 標頭、大小及 SHA-256 |
| [查詢紀錄](query.json) | 八個教學問題與入選的 Wiki 條目 |
| [初稿](draft-v0.json)／[修訂稿](draft-v1.json) | 第 3 和第 4 頁的說法如何改動 |
| [大綱證據關卡](evidence-gate.json)／[內容檢查](content-check.json) | 兩項案例前提、引用與涉及的來源 |
| [Chrome 驗收](browser-check.json)／[9 張截圖](../evidence/) | 四種視窗尺寸、互動測試、快取實驗與各張 PNG 的 SHA-256 |

完整作業 ZIP 收錄五份原始 HTML 快照，依擷取紀錄可重算 SHA-256。公開儲存庫提供 Wiki Markdown 及擷取、編譯和檢查腳本。從儲存庫或 ZIP 執行的指令見[重跑說明](replay.md)。
