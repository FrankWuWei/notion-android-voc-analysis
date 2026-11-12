# Notion Android VOC Portfolio Web

這是依據新版內容與視覺規格建立的獨立靜態前端，不沿用舊網頁內容或資料結構。

## 產生驗證後資料

在 repository 根目錄執行：

```powershell
$env:PYTHONUTF8='1'
.\.venv\Scripts\python.exe -m src.analysis.build_portfolio_web_snapshot
```

此命令只讀取本地分析產物並產生 `src/data/portfolioSnapshot.json`，不呼叫外部 API。

## 本地開發

```powershell
cd web
npm install
npm run dev
```

## 驗證

```powershell
npm run test
npm run lint
npm run build
```
