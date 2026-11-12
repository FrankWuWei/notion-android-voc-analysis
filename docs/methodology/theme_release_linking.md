# LLM 主題與產品更新關聯方法

## 目的

此步驟用來把 LLM 分析出的使用者評論主題，和 Notion 官方產品更新資訊建立「候選關聯」。

這裡不直接宣告某個痛點已修復。公開 release note 只能代表官方曾更新某個功能方向，不能證明 Google Play 使用者遇到的具體問題已完全消失。因此本步驟採用保守做法：保留所有痛點主題，另外產出候選關聯與時間狀態欄位，供後續人工複核與報告討論。

## 輸入

- LLM enriched output：`outputs/reports/llm_batch_outputs_api_repaired_enriched/`
- 產品更新資料：`data/processed/product_updates/notion_release_notes.csv`

使用 enriched output 的原因是每個 evidence 已補回：

- `review_created_at`
- `app_version`
- `score`
- `thumbs_up_count`

這些欄位可以用來判斷評論出現在產品更新前或更新後。

## 輸出

- 候選關聯表：`outputs/tables/theme_release_candidates.csv`
- 摘要統計：`outputs/tables/theme_release_candidates_summary.json`

目前結果：

- 大型語言模型主題數：`159`
- release note 數：`10`
- 候選關聯數：`15`
- 有至少一個候選關聯的主題數：`14`

## 關聯規則

每個 LLM theme 會和每個 release note 交叉比對。

比對訊號包含：

- `affected_area` 是否重疊，例如 `mobile_app`、`editing`、`sync`、`ai`。
- release note 的 `keywords` 是否出現在 theme 摘要或 evidence quote 中。
- release title 是否有具體詞出現在 theme 文字中。

為降低假陽性，以下寬泛詞不能單獨構成關聯：

- `ai`
- `agent`
- `agents`
- `mobile`
- `app`
- `table`
- `database`
- `word`
- `fix`
- `control`
- `controls`
- `workspace`

沒有 `affected_area` 重疊時，單一關鍵字也不會輸出候選關聯，必須有更強的具體訊號。

## 主要輸出欄位

- `candidate_id`：候選關聯識別碼，由 batch、theme、release 組合而成。
- `theme_id`：LLM 主題識別碼。
- `theme_name_zh`：LLM 主題名稱。
- `theme_affected_area`：主題所屬產品範圍。
- `theme_severity`：LLM 判斷的嚴重度。
- `release_id`：產品更新識別碼。
- `release_date`：產品更新日期。
- `release_title`：產品更新標題。
- `match_score`：規則計算出的關聯分數。
- `match_level`：目前分為 `strong` 或 `medium`。
- `area_overlap`：theme 與 release 重疊的產品範圍。
- `matched_keywords`：所有命中的 release keywords。
- `matched_specific_keywords`：排除寬泛詞後仍命中的具體關鍵字。
- `matched_title_terms`：命中的 release title 具體詞。
- `pre_release_evidence_count`：該 theme 的 evidence 中，出現在 release 前的數量。
- `post_release_evidence_count`：該 theme 的 evidence 中，出現在 release 後的數量。
- `review_timing_status`：評論 evidence 與 release date 的時間關係。
- `resolution_hint`：保守的後續判斷提示。

## resolution_hint 解讀

- `still_reported_after_release`
  - 同一個 theme 在 release 後仍有 evidence。
  - 不建議視為已修復，可優先列入仍待改善或需進一步確認的問題。

- `possibly_addressed_no_later_evidence_in_sample`
  - 該 theme 的 evidence 只出現在 release 前，樣本中 release 後沒有再出現。
  - 只能說「可能被處理」或「目前樣本未再觀察到」，不能直接宣稱已修復。

- `not_addressed_by_this_release`
  - evidence 只出現在 release 後。
  - 代表該 release 不太可能解決這個問題。

- `unknown_no_dated_evidence`
  - 缺少可用時間資訊。

## 執行方式

```powershell
.\.venv\Scripts\python.exe src\analysis\link_themes_to_product_updates.py `
  --llm-output-dir outputs\reports\llm_batch_outputs_api_repaired_enriched `
  --release-notes data\processed\product_updates\notion_release_notes.csv `
  --output outputs\tables\theme_release_candidates.csv `
  --summary-output outputs\tables\theme_release_candidates_summary.json
```

## 使用限制

這份表是候選關聯，不是最終修復判斷。

後續若要產生更可靠的未解問題清單，建議再加入：

- 全量評論層級的 release 前後統計，而不只看 LLM evidence sample。
- `app_version` 與 release date 的對照。
- 人工抽查 `strong` 與 `still_reported_after_release` 的代表案例。
- Android app 專屬更新來源，避免 iOS 或 web release 被誤當成 Android 修復。