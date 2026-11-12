# LLM Prompt Template 方法

## 目的

此步驟建立可重複使用的 LLM prompt template，並先用 `negative_001` batch 產生一份完整 prompt 供人工檢查。

目前不呼叫 LLM API，也不產生最終分析結果。

## Template 檔案

- `prompts/voc_theme_extraction.v1.md`

此 template 使用 placeholder，讓同一份 prompt 可以套用不同 bucket 與 batch。

主要 placeholder：

- `{{batch_id}}`
- `{{sentiment_bucket}}`
- `{{review_count}}`
- `{{output_schema_json}}`
- `{{reviews_json}}`

## Render 腳本

- `src/analysis/render_llm_prompt.py`

用途：

1. 讀取 prompt template。
2. 從 JSONL batch 檔案中選出指定 `batch_id`。
3. 將 batch metadata、reviews JSON、output schema 填入 template。
4. 輸出完整 prompt 檔案。

## 本次渲染設定

- Template: `prompts/voc_theme_extraction.v1.md`
- Batch file: `data/processed/llm_inputs/negative_llm_batches.jsonl`
- Batch id: `negative_001`
- Output: `outputs/reports/llm_prompts/negative_001_prompt.md`

執行命令：

```powershell
.\.venv\Scripts\python.exe src\analysis\render_llm_prompt.py `
  --template prompts\voc_theme_extraction.v1.md `
  --batch-file data\processed\llm_inputs\negative_llm_batches.jsonl `
  --batch-id negative_001 `
  --output outputs\reports\llm_prompts\negative_001_prompt.md
```

## Prompt 設計重點

- 僅根據輸入評論分析，不使用外部知識。
- 不允許捏造評論中沒有提到的問題。
- 每個 theme 必須附上 `review_id` 與原文 `quote`。
- `quote` 必須來自原始評論，不可改寫。
- 非英文或無法判斷的評論放入 `excluded_reviews`。
- 輸出必須是單一 JSON object。
- 除 `quote` 保留原文外，分析說明使用繁體中文。

## 輸出格式

LLM 預期輸出 JSON 包含：

- `batch_id`
- `sentiment_bucket`
- `analysis_language`
- `themes`
- `excluded_reviews`

每個 theme 包含：

- `theme_id`
- `theme_name_zh`
- `summary_zh`
- `affected_area`
- `severity`
- `evidence`
- `suggested_action_zh`

## 驗證結果

渲染後檔案：

- `outputs/reports/llm_prompts/negative_001_prompt.md`

驗證結果：

- 檔案存在：`True`
- 字元數：`76040`
- 包含 `negative_001`：`True`
- 是否殘留 placeholder：`False`
- 包含 `review_id`：`True`
- 包含輸出 JSON schema：`True`
