# OpenAI API 大型語言模型分析流程

## 目的

此流程把已完成情緒分流的評論批次送入 OpenAI 批次 API，要求模型以固定 JSON 欄位整理主題與證據，再透過程式驗證、修復及補回來源欄位。API 回傳不會直接成為最終分析結果。

## 完整流程

```text
data/processed/llm_inputs
  -> 建立 23 個 API 請求
  -> OpenAI 批次處理
  -> 拆分原始模型輸出
  -> 檢查評論識別碼、星等與原文引文
  -> 修復或移除無法回查的證據
  -> 再次驗證
  -> 從來源資料補回日期、版本與按讚數
  -> 最終驗證
```

## 程式角色

- `build_openai_batch_requests.py`：讀取 23 個評論批次，套用提示模板並加入固定 JSON 欄位規格。
- `submit_openai_batch.py`：上傳請求檔、建立批次工作及查詢狀態。
- `fetch_openai_batch_results.py`：下載批次結果並依批次編號拆成 23 個 JSON 檔。
- `validate_llm_outputs.py`：逐筆比對來源批次，檢查評論識別碼、星等與引文。
- `repair_llm_outputs.py`：修正可由來源確認的星等；引文無法逐字回查時，必須套用已完成語意稽核的版本化決策，未審核案例會直接中止流程。
- `enrich_llm_outputs.py`：以評論識別碼補回日期、應用程式版本、按讚數與情緒欄位。

## 1. 建立 API 請求

```powershell
.\.venv\Scripts\python.exe src\analysis\build_openai_batch_requests.py `
  --batch-dir data\processed\llm_inputs `
  --template prompts\voc_theme_extraction.v1.md `
  --output outputs\reports\openai_batch_requests\voc_theme_analysis_requests.jsonl `
  --model gpt-5.4-mini
```

目前輸出 `23` 行請求，每行使用原始 `batch_id` 作為 `custom_id`，方便回收後對回來源批次。`gpt-5.4-mini` 不支援 `temperature`，因此請求不傳送此參數。

## 2. 上傳前檢查

```powershell
.\.venv\Scripts\python.exe src\analysis\submit_openai_batch.py `
  --request-file outputs\reports\openai_batch_requests\voc_theme_analysis_requests.jsonl `
  --dry-run
```

此步驟只檢查檔案與請求列數，不呼叫 API。

## 3. 設定 API 金鑰

```powershell
$env:OPENAI_API_KEY = "你的 API key"
```

API 金鑰不可寫入 repo、Markdown、CSV 或 JSON。

## 4. 建立與查詢批次工作

```powershell
.\.venv\Scripts\python.exe src\analysis\submit_openai_batch.py `
  --request-file outputs\reports\openai_batch_requests\voc_theme_analysis_requests.jsonl
```

記下回傳的批次工作編號，之後查詢：

```powershell
.\.venv\Scripts\python.exe src\analysis\submit_openai_batch.py `
  --status 你的批次工作編號
```

狀態為 `completed` 後再下載結果。

## 5. 下載並拆分原始輸出

```powershell
.\.venv\Scripts\python.exe src\analysis\fetch_openai_batch_results.py `
  --batch-id 你的批次工作編號 `
  --batch-output-file outputs\reports\openai_batch_results\voc_theme_analysis_output.jsonl `
  --output-dir outputs\reports\llm_batch_outputs_api
```

預期得到 `23` 個 `{batch_id}_output.json`。這個資料夾保存 API 原始回傳，不直接供報告使用。

## 6. 檢查原始輸出

```powershell
.\.venv\Scripts\python.exe src\analysis\validate_llm_outputs.py `
  --batch-dir data\processed\llm_inputs `
  --output-dir outputs\reports\llm_batch_outputs_api `
  --require-all
```

檢查項目：

- 23 個正式批次都有輸出。
- 輸出批次編號與來源一致。
- 情緒群組與來源一致。
- 證據的評論識別碼存在於來源批次。
- 星等與來源評論一致。
- 引文是來源評論中的逐字片段。

原始 API 輸出若有錯誤，不進入下游分析。

## 7. 修復可確認的輸出

```powershell
.\.venv\Scripts\python.exe src\analysis\repair_llm_outputs.py `
  --batch-dir data\processed\llm_inputs `
  --input-dir outputs\reports\llm_batch_outputs_api `
  --output-dir outputs\reports\llm_batch_outputs_api_repaired `
  --report outputs\reports\llm_batch_outputs_api_repair_report.json `
  --quote-reviews configs\llm_quote_reviews.v1.json
```

修復只使用來源批次中可確認的內容：

- 星等不一致時，以來源星等取代。
- 引文無法逐字回查時，必須在 `configs/llm_quote_reviews.v1.json` 有人工語意稽核決策。
- 稽核確認原評論仍支持所屬主題時，改用設定中的逐字片段。
- 原評論不支持所屬主題、評論識別碼不存在，或替代引文仍無法回查時，移除該證據。
- 任何未經稽核的新錯誤引文都會讓流程失敗，不會自動以評論開頭取代。

目前語意稽核涵蓋全部 `35` 段非逐字引文：`28` 段改為支持原主題的逐字片段、`7` 筆因不支持所屬主題而移除。另修正 `4` 筆星等，連同 `5` 筆無效來源識別碼共移除 `12` 筆證據，並移除 `8` 筆無效排除項目。

## 8. 驗證修復後輸出

```powershell
.\.venv\Scripts\python.exe src\analysis\validate_llm_outputs.py `
  --batch-dir data\processed\llm_inputs `
  --output-dir outputs\reports\llm_batch_outputs_api_repaired `
  --require-all
```

只有錯誤數為 `0` 才進入下一步。

## 9. 補回來源欄位

```powershell
.\.venv\Scripts\python.exe src\analysis\enrich_llm_outputs.py `
  --batch-dir data\processed\llm_inputs `
  --input-dir outputs\reports\llm_batch_outputs_api_repaired `
  --output-dir outputs\reports\llm_batch_outputs_api_repaired_enriched
```

補回欄位：

- `review_created_at`：評論日期。
- `app_version`：應用程式版本。
- `thumbs_up_count`：評論按讚數。
- `sentiment_label`、`sentiment_score`、`sentiment_bucket`：情緒模型結果。

這些欄位由評論識別碼連回來源資料，不要求大型語言模型自行抄寫。

## 10. 最終驗證

```powershell
.\.venv\Scripts\python.exe src\analysis\validate_llm_outputs.py `
  --batch-dir data\processed\llm_inputs `
  --output-dir outputs\reports\llm_batch_outputs_api_repaired_enriched `
  --require-all
```

目前最終結果：

- 預期批次：`23`。
- 實際輸出：`23`。
- 驗證後主題：`159`。
- 來源可逐字回查的證據：`645`；其中原先無法逐字回查的 `35` 筆已全部完成上述人工語意稽核。
- 排除評論：`344`。
- 驗證錯誤：`0`。

後續關聯、趨勢分析與作品集應使用 `outputs/reports/llm_batch_outputs_api_repaired_enriched/`，不要直接使用原始 API 輸出。

## 品質原則

1. 先用情緒分類縮小分析範圍，降低混雜訊號與輸入成本。
2. 用固定 JSON 欄位規格控制輸出結構。
3. 用評論識別碼、星等與原文引文檢查來源真實性；非逐字引文另做人工語意稽核，確認評論確實支持所屬主題。
4. 日期與版本由程式補回，避免模型抄寫錯誤。
5. 保留原始輸出、版本化引文稽核決策、修復後輸出、修復報告與最終輸出，讓每次處理都能追溯。
