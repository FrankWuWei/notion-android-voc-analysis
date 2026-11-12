# 資料清洗方法

## 輸入

- 來源檔案：`data/raw/notion_android_reviews_google_play_2025_onward_en_us.csv`
- 輸入筆數：`6269`
- 原始資料規則：`data/raw/` 底下的檔案保持不變。

## 輸出

- 清洗後檔案：`data/interim/reviews_cleaned_2025_onward_en_us.csv`
- 輸出筆數：`6186`

## 清洗規則

1. 保留原始資料。
   - raw CSV 只作為讀取來源。
   - 清洗後資料寫入 `data/interim/`。

2. 移除不適合文字情緒分析的資料列。
   - 移除空的 `review_text`。
   - 移除只有空白的 `review_text`。
   - 正規化後，移除少於 `3` 個英數字元的文字。
   - 移除重複的 `review_id`，保留第一次出現的資料列。

3. 在不改變情緒語意的前提下標準化文字。
   - 還原 HTML entities，例如 `&amp;`。
   - 使用 `NFKC` 做 Unicode 正規化。
   - 將重複空白與換行壓成一個空白。
   - 移除前後空白。

4. 保留否定詞與標點。
   - 清洗流程不移除 stopwords。
   - 清洗流程不移除標點符號。
   - 例如 `can't sync!!! not good` 這類片語會被保留。

5. 準備模型輸入長度。
   - 完整清洗後文字存放在 `review_text_clean`。
   - 模型輸入文字存放在 `review_text_for_model`。
   - `review_text_for_model` 上限為 `2000` 字元。
   - 是否截斷紀錄在 `review_text_was_truncated`。

6. 保留輔助分析欄位。
   - `score`
   - `review_created_at`
   - `app_version`
   - `thumbs_up_count`

## 驗證結果

清洗後驗證：

- 筆數：`6186`
- 不重複 `review_id`：`6186`
- 重複 `review_id`：`0`
- 空的 `review_text_clean`：`0`
- `review_text_clean` 最少英數字元數：`3`
- `review_text_clean` 最大長度：`501`
- `review_text_for_model` 最大長度：`501`
- 被截斷的資料列：`0`

移除資料列：

- 正規化後過短：`83`
- 空文字：`0`
- 重複 `review_id`：`0`
