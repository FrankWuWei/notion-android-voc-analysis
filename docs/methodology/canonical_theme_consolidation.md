# Canonical 主題整併方法

## 目的

此步驟將 23 個 LLM batch 各自產生的主題，整併成可跨 batch 閱讀的穩定主題家族。整併使用固定且版本化的映射規則，只讀取已完成來源驗證、語意稽核、修復及 enrichment 的正式 LLM 輸出。

## 為什麼需要整併

原始的 `159` 筆 themes 是 batch-level outputs。不同 batch 可能分別產生「效能卡頓」、「載入緩慢」或「Android 端效能不穩」等語意相近主題，因此不能把 `159` 直接解讀為 159 個互不重複的使用者痛點。

## 輸入

- `outputs/reports/llm_batch_outputs_api_repaired_enriched/`
- `configs/canonical_themes.v1.json`

目前正式輸入包含：

- `negative`：61 個 batch themes、235 筆 evidence。
- `mixed_or_uncertain`：69 個 batch themes、310 筆 evidence。
- `positive`：29 個 batch themes、100 筆 evidence。

合計 `159` 個 batch themes、`645` 筆 evidence，涉及 `618` 個不重複評論識別碼。

## 確定性的整併方式

`src/analysis/consolidate_canonical_themes.py` 使用以下欄位進行確定性映射：

- `sentiment_bucket`
- `affected_area`
- `theme_id`

規則先處理需要細分的內容，例如空白畫面、Widget、媒體上傳、行動版功能落差與一般自訂需求，再以 `affected_area` 作為 fallback。每個來源主題都保留唯一識別碼：

```text
{batch_id}::{theme_id}
```

目前 taxonomy 分成：

- 11 個 pain-point canonical themes。
- 6 個 positive-value canonical themes。

## 輸出

- `outputs/tables/canonical_themes.csv`
  - 每個 canonical theme 的來源主題數、batch 覆蓋數、evidence 數及唯一 review 數。
- `outputs/tables/canonical_theme_source_mapping.csv`
  - 每個 batch-level theme 到 canonical theme 的完整 mapping。
- `outputs/tables/canonical_theme_evidence.csv`
  - 保留 canonical theme、來源 theme、原始 `review_id`、引文、日期、版本與星等。
- `outputs/tables/canonical_themes_summary.json`
  - 總體筆數、group 統計、方法版本與輸入 digest。

## 計數邊界

本步驟可以回答：

- 哪些主題家族出現在較多 batch。
- 每個家族整併了多少 batch-level themes。
- 有多少已驗證 evidence 與唯一 `review_id` 可回查。

本步驟不能回答：

- 該主題占 2,683 則負面／不確定評論的百分比。
- 該主題在 6,186 則有效評論中的真實發生率。
- 主題的重要性或產品優先級排名。

原因是原始 LLM prompt 只要求每個 theme 提供代表 evidence，沒有替每一則輸入評論建立完整 theme assignment。因此網站與報告應使用「batch 覆蓋」、「來源主題數」與「已驗證 evidence」，不可改寫成 prevalence。

## 執行方式

```powershell
.\.venv\Scripts\python.exe -X utf8 src\analysis\consolidate_canonical_themes.py
```

整併不會改寫原始 LLM outputs。需要修改 taxonomy 時，先調整 `configs/canonical_themes.v1.json` 或程式中的版本化映射規則，再重新產生所有輸出。
