# 一般產品更新脈絡分析

## 目的

此分析示範如何把大型語言模型整理出的使用者問題，轉成可重跑的時間比較。Notion 公開產品更新只作為時間切點，用來比較切點前後是否仍出現相關負面評論；結果不判定 Android 問題已修復，也不推論某次更新造成或解決問題。

## 使用資料

- 負面評論：`data/processed/reviews_with_sentiment_2025_onward_en_us.csv`
- 最終 API 主題與更新候選：`outputs/tables/theme_release_candidates.csv`
- 公開更新說明：`data/processed/product_updates/notion_release_notes.csv`
- 關鍵詞組規則：`configs/negative_theme_monitoring_rules.json`

公開更新範圍一律標示為 `general_product_release`，代表它可能涵蓋網頁、iOS、開發者平台或全產品功能，不能視為 Android 版本修復紀錄。

## 代表案例

目前保留三個同時具備完整 28 天觀察期間、實際命中評論與可回查證據的案例：

- 文字編輯、選取與複製貼上操作不順。
- 登入、權限與訂閱後存取問題。
- 價格偏高與功能額外付費爭議。

候選階段原本另有行動版空白畫面與離線同步主題，但在對應的 28 天期間前後都是零筆命中，因此不為了湊足案例數而放入作品集。

## 比對方式

每個代表主題都從最終 API 主題證據整理出 `match_any_phrases`。評論文字轉成小寫後，包含任一關鍵詞組即視為相關評論。規則可讀、可修改、可回查，但不是完整的主題分類模型。

只掃描 `sentiment_bucket = negative` 的完整評論資料。即使候選主題來自不確定情緒群組，期間比較仍統一使用負面評論作為計算對象與分母。

每個時間切點使用兩段期間：

- 更新前：`[release_date - 28 days, release_date)`
- 更新後：`[release_date, release_date + 28 days)`

提及率計算方式：

```text
符合主題關鍵詞組的負面評論數 / 同期間全部負面評論數
```

## 觀察狀態

- `continued_after_release`：更新後至少有 3 筆相關負面評論。
- `limited_post_evidence`：更新後有 1 至 2 筆相關負面評論。
- `not_observed_after_release`：更新後沒有相關負面評論。
- `insufficient_observations`：任一完整期間少於 20 筆負面評論。
- `incomplete_pre_window`：資料未涵蓋完整的更新前 28 天。
- `incomplete_post_window`：資料未涵蓋完整的更新後 28 天。

上述狀態只描述目前資料與規則的觀察結果。`not_observed_after_release` 不代表問題已修復。

## 目前產出

- 代表案例：`3` 個。
- 固定期間命中證據：`6` 筆。
- 趨勢表：`outputs/tables/negative_theme_release_trends.csv`。
- 逐筆證據：`outputs/tables/negative_theme_release_trend_evidence.csv`。
- 摘要：`outputs/tables/negative_theme_release_trends_summary.json`。

逐筆證據保留評論識別碼、日期、應用程式版本、星等、命中詞組與評論文字，可由彙總數字回查來源。

## 執行方式

```powershell
.\.venv\Scripts\python.exe -X utf8 src\analysis\analyze_negative_theme_release_trends.py
```

## 使用限制

- 關鍵詞組可能漏掉同義表達，也可能命中語境不同的評論。
- 公開更新不是 Android 專屬版本紀錄。
- 三個案例是具證據的作品集示範，不代表其他主題不重要。
- 若要判斷修復成效，仍需 Android 版本修復紀錄、較長觀察期間與可重現問題的操作資料。