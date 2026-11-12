# Notion Android 使用者回饋分析

以 Google Play 美國區英文評論建立可重跑的使用者回饋分析流程，將非結構文字轉成可回查的產品主題、原始證據與待驗證建議。專案涵蓋資料蒐集與清理、情緒分類、大型語言模型批次分析、模型輸出驗證與產品案例追蹤，並以靜態作品集網站呈現分析方法、品質控制、主要發現與解讀邊界。

## 專案目標

從大量公開評論中辨識 Notion Android 使用者重複回報的問題，並將分析結果轉成可量化、可追溯且能進入產品討論的驗證方向。

## 目前資料與結果

- 清洗後評論：`6,186` 則，範圍 `2025-01-01` 至 `2026-06-19`。
- 大型語言模型輸入：`3,183` 則。負面與不確定評論全量分析，正向評論取 `500` 則代表樣本。
- OpenAI 批次處理：`23 / 23` 個批次通過最終驗證。
- 驗證後輸出：`159` 個主題、`645` 筆可回查主題證據、最終來源驗證錯誤 `0` 筆。
- 輸出稽核：逐筆審查 `35` 段無法逐字回查的引文；`28` 段改為支持原主題的逐字片段，`7` 筆因不支持所屬主題而移除，另修正 `4` 筆星等。
- 跨批次主題整併：`159` 個 batch-level themes 以版本化規則整併為 `11` 個痛點家族與 `6` 個正向價值家族；`645` 筆 evidence 全數保留，涉及 `618` 個不重複評論識別碼。
- 代表產品案例：`3` 個，固定比較時間切點前後各 `28` 天，共保留 `6` 筆期間證據。

`645` 筆是大型語言模型主題的引文證據；`6` 筆則是三個代表案例在固定 28 天期間內重新掃描完整負面評論後的命中證據，兩者用途不同。

Canonical theme 的來源主題數、batch 覆蓋數與 evidence 數，只描述已驗證 batch outputs 的跨批次訊號，不是 6,186 則評論的發生率或產品優先級排行。

公開產品更新一律視為比較時間切點，不是 Android 修復紀錄。本專案不推論某項公開更新造成或解決特定 Android 問題。

## 分析流程

1. 使用 `google-play-scraper` 逐頁蒐集 Notion Android 公開評論，依評論識別碼去重並在日期界線停止。
2. 清理空值、重複值、HTML 特殊符號、相容字元與多餘空白，同時保留否定詞、標點、星等、日期與應用程式版本。
3. 使用 DistilBERT 英文情緒分類模型初步分流，再以模型信心與星等交叉檢查，保留不確定評論。
4. 將 `3,183` 則評論拆成 `23` 個批次，透過 OpenAI 批次 API 與固定 JSON 欄位規格抽取主題及證據。
5. 逐筆驗證評論識別碼、星等與原文引文；無法逐字回查的引文必須經版本化人工語意稽核，確認仍支持原主題後才能替換，否則移除。
6. 依 `affected_area` 與版本化 `theme_id` 規則將 batch-level themes 整併成一致的 canonical theme families，保留完整來源 mapping 與 evidence。
7. 以最終 API 輸出建立產品更新候選關聯，挑選具完整觀察期間與實際證據的案例，回到完整負面評論重算。
8. 將最終統計、品質數字與逐筆證據保留為新版作品集可使用的正式資料產物。

## 網頁作品集

`web/` 是以 Vite、React 與 TypeScript 建立的靜態作品集。網站資料由正式分析產物產生為版本化 JSON snapshot；瀏覽器執行時不呼叫 API，也不需要後端或資料庫。

先重建網站資料，再啟動本機網站：

```powershell
$env:PYTHONUTF8='1'
.\.venv\Scripts\python.exe -m src.analysis.build_portfolio_web_snapshot

Set-Location web
npm install
npm run dev
```

前端驗證：

```powershell
npm run test
npm run lint
npm run build
```

完整驗證結果記錄於 `docs/portfolio_web_verification_report_v1.md`。

## 重建驗證後輸出與下游分析

```powershell
.\.venv\Scripts\python.exe -X utf8 src\analysis\repair_llm_outputs.py
.\.venv\Scripts\python.exe -X utf8 src\analysis\validate_llm_outputs.py --output-dir outputs\reports\llm_batch_outputs_api_repaired --require-all
.\.venv\Scripts\python.exe -X utf8 src\analysis\enrich_llm_outputs.py
.\.venv\Scripts\python.exe -X utf8 src\analysis\consolidate_canonical_themes.py
.\.venv\Scripts\python.exe -X utf8 src\analysis\link_themes_to_product_updates.py
.\.venv\Scripts\python.exe -X utf8 src\analysis\analyze_negative_theme_release_trends.py
.\.venv\Scripts\python.exe -m src.analysis.build_portfolio_web_snapshot
```

正式資料產物包括：

- `data/processed/reviews_with_sentiment_2025_onward_en_us.csv`
- `data/processed/llm_inputs/manifest.json`
- `outputs/reports/llm_batch_outputs_api_repaired_enriched/`
- `outputs/reports/llm_batch_outputs_api_repair_report.json`
- `configs/llm_quote_reviews.v1.json`
- `outputs/tables/canonical_themes.csv`
- `outputs/tables/canonical_theme_source_mapping.csv`
- `outputs/tables/canonical_theme_evidence.csv`
- `outputs/tables/negative_theme_release_trends.csv`
- `outputs/tables/negative_theme_release_trend_evidence.csv`
- `configs/negative_theme_monitoring_rules.json`
- `configs/portfolio_web.v1.json`
- `web/src/data/portfolioSnapshot.json`

## 專案結構

```text
src/data_collection/  公開評論與產品更新資料蒐集
src/preprocessing/    評論清理
src/analysis/         情緒分類、LLM 批次處理、驗證、關聯與趨勢分析
configs/              分析、人工稽核、主題整併與作品集資料規格
data/                 原始、清理後與處理後資料
outputs/               LLM 結果、品質報告、趨勢表與原始證據
docs/methodology/      分析方法、執行方式與解讀限制
web/                   React / TypeScript 靜態作品集
```

## 驗證

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v

Set-Location web
npm run test
npm run lint
npm run build
```

原始評論 CSV 與大型分析輸出不納入版本控制；可依專案腳本在本機重新產生。
