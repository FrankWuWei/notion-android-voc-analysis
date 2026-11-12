# 一般產品更新脈絡分析設計

## 目標

使用既有的 Notion 公開更新說明，作為負面評論主題的一般產品更新脈絡。
分析必須呈現某類負面回饋是否在更新前後被觀察到，但不得宣稱 Android
問題已被修復，或由該更新所造成。

## 範圍

- 評論輸入資料：`data/processed/reviews_with_sentiment_2025_onward_en_us.csv`。
- 更新輸入資料：`data/processed/product_updates/notion_release_notes.csv`。
- 候選關聯輸入資料：`outputs/tables/theme_release_candidates.csv`。
- 僅分析 `sentiment_bucket` 為 `negative` 的候選關聯。
- 將目前所有更新說明視為 `general_product_release`。
- 每筆更新使用固定的前後各 28 天觀察區間。

## 資料契約

趨勢資料表會以每個負面主題與更新候選關聯為一列，記錄候選關聯識別字、
更新範圍、更新日期、評論觀察區間涵蓋狀態、更新前後的命中評論數、
可用評論數、提及率、提及率差異，以及保守的觀察狀態。

佐證資料表會保留命中的 `review_id`、`review_created_at`、`app_version`、
`score` 與 `review_text_clean`，讓讀者能由彙總數字回查到原始評論。

## 比對方式

分析會為現有候選關聯中的每個負面主題建立小型、明確的關鍵字與片語設定。
評論經大小寫正規化後，只要包含至少一個設定片語，就視為命中該主題。
設定檔是專案產出的一部分，執行時不會動態推論關鍵字。

## 觀察規則

- 若評論資料結束日期早於更新後第 28 天，該更新標示為
  `incomplete_post_window`。
- 若任一完整觀察區間少於 20 筆可用評論，標示為
  `insufficient_observations`。
- 在資料量足夠時，更新後有至少 3 筆命中負面評論，標示為
  `continued_after_release`。
- 更新後有 1 至 2 筆命中負面評論，標示為 `limited_post_evidence`。
- 更新後沒有命中負面評論，標示為 `not_observed_after_release`。
- 以上狀態只描述本次評論樣本的觀察結果，不代表更新已修復、未修復，或造成
  某個問題。

## 產出

- `configs/negative_theme_monitoring_rules.json`
- `outputs/tables/negative_theme_release_trends.csv`
- `outputs/tables/negative_theme_release_trend_evidence.csv`
- `outputs/tables/negative_theme_release_trends_summary.json`
- `docs/methodology/general_release_context_analysis.md`

## 限制

- 不修改原始與處理後的評論資料集。
- 不新增外部資料來源或 API 依賴。
- 僅使用 Python 標準函式庫，並遵循現有腳本與測試的慣例。
- 所有下游輸出與文件都必須標示 `general_product_release`。
