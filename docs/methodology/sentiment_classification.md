# 情緒分類方法

## 輸入

- 來源檔案：`data/interim/reviews_cleaned_2025_onward_en_us.csv`
- 輸入筆數：`6186`
- 模型輸入使用欄位：`review_text_for_model`

## 模型

- 任務：`sentiment-analysis`
- 模型：`distilbert/distilbert-base-uncased-finetuned-sst-2-english`
- 執行套件：
  - `transformers==5.12.1`
  - `torch==2.12.1`

## 輸出

- 輸出檔案：`data/processed/reviews_with_sentiment_2025_onward_en_us.csv`
- 輸出筆數：`6186`

新增欄位：

- `sentiment_label`：模型輸出的情緒標籤，可能為 `POSITIVE` 或 `NEGATIVE`
- `sentiment_score`：模型對 `sentiment_label` 的信心分數
- `sentiment_bucket`：LLM 分析前使用的專案分桶
- `sentiment_model`：推論時使用的模型 id

## 分類命令

```powershell
.\.venv\Scripts\python.exe src\analysis\classify_sentiment.py `
  --input data\interim\reviews_cleaned_2025_onward_en_us.csv `
  --output data\processed\reviews_with_sentiment_2025_onward_en_us.csv `
  --confidence-threshold 0.8 `
  --batch-size 32
```

## `sentiment_bucket` 規則

模型輸出不會直接作為最終分析群組。每則評論會再被分配到專案層級的 bucket：

- `positive`
  - `sentiment_label = POSITIVE`
  - `sentiment_score >= 0.8`
  - 星等不是 1 或 2 星

- `negative`
  - `sentiment_label = NEGATIVE`
  - `sentiment_score >= 0.8`
  - 星等不是 4 或 5 星

- `mixed_or_uncertain`
  - `sentiment_score < 0.8`
  - 或星等為 3 星
  - 或情緒標籤與星等明顯衝突

## 驗證結果

- 筆數：`6186`
- 不重複 `review_id`：`6186`
- 重複 `review_id`：`0`
- 空的 `sentiment_label`：`0`
- 空的 `sentiment_bucket`：`0`
- 最小 `sentiment_score`：`0.500232`
- 最大 `sentiment_score`：`0.99989`

`sentiment_label` 數量：

- `POSITIVE`：`3778`
- `NEGATIVE`：`2408`

`sentiment_bucket` 數量：

- `positive`：`3503`
- `negative`：`1209`
- `mixed_or_uncertain`：`1474`

依星等與 bucket 交叉統計：

| Rating | Bucket | Rows |
| --- | --- | ---: |
| 1 | negative | 848 |
| 1 | mixed_or_uncertain | 64 |
| 2 | negative | 361 |
| 2 | mixed_or_uncertain | 44 |
| 3 | mixed_or_uncertain | 558 |
| 4 | positive | 440 |
| 4 | mixed_or_uncertain | 360 |
| 5 | positive | 3063 |
| 5 | mixed_or_uncertain | 448 |
