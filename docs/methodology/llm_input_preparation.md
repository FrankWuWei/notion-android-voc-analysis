# LLM 輸入資料準備方法

## 目的

此步驟只負責準備後續 LLM 分析使用的輸入資料，不會呼叫 LLM，也不會產生最終產品洞察。

主要目的：

- 將 `sentiment_bucket` 分開處理，避免正面、負面、混合評論全部混在一起。
- 控制每批評論數量，降低單次 LLM 輸入過大造成的成本與輸出不穩定。
- 保留 `review_id`，讓後續每個 LLM 結論都能回查原始評論。

## 輸入

- 來源檔案：`data/processed/reviews_with_sentiment_2025_onward_en_us.csv`
- 輸入筆數：`6186`

來源 bucket 數量：

- `positive`：`3503`
- `negative`：`1209`
- `mixed_or_uncertain`：`1474`

## 輸出

輸出資料夾：

- `data/processed/llm_inputs/`

輸出檔案：

- `data/processed/llm_inputs/positive_llm_batches.jsonl`
- `data/processed/llm_inputs/negative_llm_batches.jsonl`
- `data/processed/llm_inputs/mixed_or_uncertain_llm_batches.jsonl`
- `data/processed/llm_inputs/manifest.json`

## 分桶與抽樣策略

- `negative`
  - 使用全量資料。
  - 原因：這是主要產品痛點來源。

- `mixed_or_uncertain`
  - 使用全量資料。
  - 原因：這類評論常包含「整體喜歡但有明確抱怨」的高價值 VOC。

- `positive`
  - 先取最多 `500` 則代表性樣本。
  - 排序依據：`thumbs_up_count` 較高優先，其次是 `review_text_char_count` 較長者。
  - 原因：正面評論數量最多且重複性較高，先抽代表樣本可降低 token 成本。

## 批次設定

- 每批最多 `150` 則評論。

實際輸出：

- `positive`：選取 `500` 則，輸出 `4` 批
- `negative`：選取 `1209` 則，輸出 `9` 批
- `mixed_or_uncertain`：選取 `1474` 則，輸出 `10` 批

## 每則評論保留欄位

每則評論只保留後續 LLM 分析必要欄位：

- `review_id`
- `score`
- `review_created_at`
- `app_version`
- `thumbs_up_count`
- `sentiment_label`
- `sentiment_score`
- `sentiment_bucket`
- `review_text_for_model`

不保留 `user_name` 等個人識別或分析不必要欄位。

## JSONL 格式

每個 `.jsonl` 檔案中，一行代表一個 LLM batch。

每個 batch 包含：

- `batch_id`
- `sentiment_bucket`
- `source_file`
- `selection_strategy`
- `batch_index`
- `total_batches`
- `review_count`
- `reviews`

## 產生命令

```powershell
.\.venv\Scripts\python.exe src\analysis\prepare_llm_inputs.py `
  --input data\processed\reviews_with_sentiment_2025_onward_en_us.csv `
  --output-dir data\processed\llm_inputs `
  --batch-size 150 `
  --positive-limit 500
```

## 注意事項

`lang=en` 與 `country=us` 是 Google Play 抓取時的語系與地區設定，不保證每一則評論文字都是英文。後續 LLM 分析時，可以要求模型標記或忽略非英文評論；若需要更嚴謹的控制，也可以在下一階段加入語言偵測。
