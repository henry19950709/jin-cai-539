# 今彩 539 歷史資料分析

這個專案提供可安裝到 iPhone 主畫面的 Web App（PWA），保留原本 Python / PyQt5 桌面版。手機版可查歷年同期數、同日期與同週次，並依年份、月份、期別、合數及尾數篩選開獎資料。統計在手機瀏覽器內完成；Python 只負責取得與匯出開獎資料。

## 本機啟動 Web App

在專案根目錄執行：

```powershell
.\.venv\Scripts\python.exe app.py
```

然後開啟 <http://127.0.0.1:8000/>。啟動程式會把 `data/daily539_cache.json` 匯出到 `docs/data/`，再用 Python 標準函式庫提供網頁；不需要 Flask 或 npm。其他作業系統可用 `python app.py`。

本機 HTTP 方便開發；iPhone 的離線 PWA 需要透過 HTTPS 網址使用。給朋友使用時，先把變更提交並推送到 GitHub，然後到倉庫的 **Settings → Pages → Build and deployment → Source** 選擇 **GitHub Actions**。本專案的 `.github/workflows/update-pages-data.yml` 會在推送到 `main` 後自動測試並發布 `docs/`；Actions 成功後可複製 Pages 網址給朋友。朋友在 iPhone Safari 開啟網址後，選擇「分享」→「加入主畫面」→「作為 Web App 開啟」。

也可使用 Vercel 免費 Hobby 方案：連結同一個 GitHub 倉庫後匯入專案，根目錄的 `vercel.json` 已指定 `docs/` 為輸出目錄。Hobby 僅供個人、非商業用途；目前專案的每日資料更新與發布流程仍以 GitHub Pages 為主要設定。

## 更新開獎資料

`docs/data/cache.json` 是發布到手機的資料快照。它不會在使用者開啟網頁時爬取官方網站。更新步驟：

```powershell
.\.venv\Scripts\python.exe scripts\update_pages_data.py
.\.venv\Scripts\python.exe scripts\export_pages_data.py
```

沒有現成虛擬環境時，先安裝 `requirements-data.txt`。GitHub Actions 每天執行資料更新，並在同一流程中重新發布網站；也能手動執行工作流程，勾選 `refresh_data` 來更新。若官方資料來源無法連線且資料超過 14 天未更新，更新腳本會失敗，避免把舊資料誤認成最新資料。網頁會明確顯示最後一期日期。

目前倉庫中的歷史快取涵蓋 2007-01-01 至 2026-10-27，共 6,004 期。發布前仍應確認已更新到近期開獎。

## 測試

```powershell
node --test tests\test_web_logic.mjs
$env:QT_QPA_PLATFORM = "offscreen"
.\.venv\Scripts\python.exe -m unittest discover -s tests
```

Web 版的純分析邏輯在 `docs/logic.mjs`，不需要額外 JavaScript 套件。桌面版依賴請見 `requirements.txt`；入口仍為 `main.py`。

## 主要檔案

- `docs/`：手機版介面、PWA manifest、Service Worker、圖示與已匯出的資料。
- `docs/logic.mjs`：與 Python 分析器對應的條件篩選與參照分析。
- `scripts/export_pages_data.py`：驗證本機快取並匯出靜態資料。
- `scripts/update_pages_data.py`：從資料來源取得近期開獎；過舊時回報失敗。
- `src/`、`main.py`：原本的 Python 桌面版。

歷史統計不代表未來開獎結果；實際開獎請以官方公告為準。
