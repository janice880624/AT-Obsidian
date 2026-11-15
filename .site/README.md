# 互動學習網站

這個資料夾把整個 Vault 轉成一個單頁的互動學習網站（區域臨床路徑、細分部位、筆記閱讀、回想模式、閃卡、自動測驗、學習進度）。

- 每次 push 到 `main`，`.github/workflows/site.yml` 會自動執行 `python3 .site/build.py` 並部署到 GitHub Pages。
- 本機預覽：在 repo 根目錄執行 `python3 .site/build.py`，打開 `_site/index.html`。

## 檔案

| 檔案 | 用途 |
|---|---|
| `build.py` | 讀取 `0X_` 資料夾的筆記與 `assets/` 圖片，清掉模板佔位句，解析雙向連結，輸出 `_site/index.html` |
| `subareas.py` | 各身體區域的「細分部位」規則（依標題與英文名稱比對，由上而下第一個符合者） |
| `template.html` | 網站介面 |
| `marked.min.js` | Markdown 轉換（marked v12，MIT） |

## 調整細分部位

新筆記會依 `subareas.py` 的關鍵字自動歸類，對不到的會落在每個區域最後一個分類。要讓某類筆記換分類，在對應規則的正規表示式加入關鍵字即可。

不會出現在網站上的內容：`99_模板`、`07_個案紀錄`、每日知識包索引、修正與驗證報告。
