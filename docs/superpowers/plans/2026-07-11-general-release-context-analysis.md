# 一般產品更新脈絡分析實作計畫

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**目標：** 使用既有的負面評論、主題候選關聯與 Notion 公開更新資料，產生五個代表性主題的更新前後 28 天觀察表與可追溯佐證表。

**架構：** 新增一份人工審查過的主題片語設定檔，分析程式以標準函式庫讀取評論、更新與設定檔。程式只在 `negative` 評論中以大小寫不敏感的片語比對計數，並將每筆命中評論輸出為證據；結果只描述樣本觀察，不推論 Android 修復或因果關係。

**技術：** Python 3.10、`csv`、`json`、`datetime`、`unittest`。

## 全域限制

- 僅使用既有資料集，不呼叫外部 API。
- 所有更新的 `release_scope` 固定為 `general_product_release`。
- 每個觀察區間為 28 天：更新前 `[release_date - 28 days, release_date)`，更新後 `[release_date, release_date + 28 days)`。
- 僅以 `sentiment_bucket == "negative"` 的評論作為分母與比對對象。
- 結果狀態只能使用觀察性語句，不能寫入 `fixed`、`unresolved` 或因果結論。
- 此 workspace 的 Git 狀態不可用，因此本計畫不包含 commit 步驟。

---

### Task 1：建立代表性主題規則與純函式測試

**檔案：**

- 建立：`configs/negative_theme_monitoring_rules.json`
- 建立：`tests/test_analyze_negative_theme_release_trends.py`
- 建立：`src/analysis/analyze_negative_theme_release_trends.py`

**介面：**

- `normalize_match_text(value: str) -> str`
- `review_matches_rule(review_text: str, phrases: list[str]) -> tuple[bool, list[str]]`
- `classify_observation(*, pre_eligible_count: int, post_eligible_count: int, post_match_count: int, pre_window_complete: bool, post_window_complete: bool) -> str`

- [ ] **Step 1：建立失敗測試**

```python
def test_review_matches_rule_case_insensitively():
    matched, phrases = review_matches_rule(
        "I cannot LOG IN after the update", ["log in", "locked out"]
    )
    self.assertTrue(matched)
    self.assertEqual(phrases, ["log in"])

def test_classify_observation_prioritizes_incomplete_window():
    status = classify_observation(
        pre_eligible_count=50,
        post_eligible_count=50,
        post_match_count=5,
        pre_window_complete=True,
        post_window_complete=False,
    )
    self.assertEqual(status, "incomplete_post_window")
```

- [ ] **Step 2：執行測試並確認失敗**

```powershell
.\.venv\Scripts\python.exe -X utf8 -m unittest tests.test_analyze_negative_theme_release_trends
```

預期：因分析模組尚不存在而失敗。

- [ ] **Step 3：建立最小規則設定與純函式實作**

設定檔使用下列五個候選關聯，並保留 `candidate_id` 以確保可回查：

```json
{
  "release_scope": "general_product_release",
  "window_days": 28,
  "minimum_eligible_reviews": 20,
  "rules": [
    {
      "candidate_id": "negative_001::account_login_sso_support_and_subscription_access::2026-05-13-3-5-notion-developer-platform",
      "theme_id": "account_login_sso_support_and_subscription_access",
      "match_any_phrases": ["log in", "login process", "locked out", "request access", "microsoft intune"]
    },
    {
      "candidate_id": "negative_001::pricing_subscription_and_ai_credit_value_concerns::2026-05-13-3-5-notion-developer-platform",
      "theme_id": "pricing_subscription_and_ai_credit_value_concerns",
      "match_any_phrases": ["ai credits", "pay extra", "subscription price", "over priced", "without paying"]
    },
    {
      "candidate_id": "negative_002::editing_text_input_and_basic_note_actions_broken::2026-04-27-rollups-now-as-currency-percent-and-more",
      "theme_id": "editing_text_input_and_basic_note_actions_broken",
      "match_any_phrases": ["double-space", "gibberish characters", "select text", "source formatting", "copy and paste"]
    },
    {
      "candidate_id": "negative_002::navigation_ui_layout_and_removed_favorites::2026-05-04-a-new-home-on-mobile",
      "theme_id": "navigation_ui_layout_and_removed_favorites",
      "match_any_phrases": ["hard to navigate", "sticky title bar", "giant text", "favorite section", "favorites sidebar"]
    },
    {
      "candidate_id": "negative_004::forced_ai_intrusion_limits_and_privacy_trust::2026-05-07-plan-mode",
      "theme_id": "forced_ai_intrusion_limits_and_privacy_trust",
      "match_any_phrases": ["disable the ai", "turned off", "forced to use ai", "ai slop", "ai training"]
    }
  ]
}
```

`classify_observation` 依序回傳：`incomplete_pre_window`、`incomplete_post_window`、`insufficient_observations`、`continued_after_release`、`limited_post_evidence`、`not_observed_after_release`。

- [ ] **Step 4：再次執行純函式測試**

```powershell
.\.venv\Scripts\python.exe -X utf8 -m unittest tests.test_analyze_negative_theme_release_trends
```

預期：純函式測試通過。

### Task 2：建立趨勢列、證據列與 CLI 的失敗測試

**檔案：**

- 修改：`tests/test_analyze_negative_theme_release_trends.py`
- 修改：`src/analysis/analyze_negative_theme_release_trends.py`

**介面：**

- `build_trend_rows(reviews: list[dict], candidates: list[dict], rules: dict) -> tuple[list[dict], list[dict]]`
- `summarize_trends(rows: list[dict]) -> dict`
- `analyze_negative_theme_release_trends(reviews_path: Path, candidates_path: Path, rules_path: Path, output_path: Path, evidence_output_path: Path, summary_output_path: Path) -> dict`

- [ ] **Step 1：建立失敗測試**

```python
def test_build_trend_rows_counts_window_matches_and_emits_evidence():
    rows, evidence = build_trend_rows(
        reviews=[
            review("2026-04-20T00:00:00+00:00", "Cannot log in"),
            review("2026-05-20T00:00:00+00:00", "Still locked out"),
        ],
        candidates=[candidate("2026-05-13")],
        rules=rules_for_login(),
    )
    self.assertEqual(rows[0]["pre_match_count"], 1)
    self.assertEqual(rows[0]["post_match_count"], 1)
    self.assertEqual(rows[0]["observation_status"], "limited_post_evidence")
    self.assertEqual([item["period"] for item in evidence], ["pre", "post"])
```

- [ ] **Step 2：執行測試並確認失敗**

```powershell
.\.venv\Scripts\python.exe -X utf8 -m unittest tests.test_analyze_negative_theme_release_trends
```

預期：`build_trend_rows` 尚未定義而失敗。

- [ ] **Step 3：實作資料讀取、計數與輸出**

趨勢表欄位固定為：

```python
TREND_FIELDNAMES = [
    "candidate_id", "theme_id", "theme_name_zh", "theme_affected_area",
    "release_id", "release_date", "release_title", "release_scope",
    "window_days", "pre_window_complete", "post_window_complete",
    "pre_eligible_count", "post_eligible_count", "pre_match_count",
    "post_match_count", "pre_match_rate", "post_match_rate",
    "rate_change_percentage_points", "observation_status",
]
```

證據表欄位固定為：

```python
EVIDENCE_FIELDNAMES = [
    "candidate_id", "theme_id", "release_id", "release_date", "period",
    "matched_phrases", "review_id", "review_created_at", "app_version",
    "score", "review_text_clean",
]
```

讀取所有評論後，先過濾 `sentiment_bucket == "negative"`。對每個規則以
`candidate_id` 找到候選列，再以更新日期區分前後區間，計算比率
`match_count / eligible_count`；若分母為零，比率輸出空字串。輸出時使用 UTF-8
CSV，摘要 JSON 至少包含 `trend_row_count`、`evidence_row_count`、
`review_corpus_min_at`、`review_corpus_max_at` 與依 `observation_status` 的計數。

- [ ] **Step 4：執行測試並確認通過**

```powershell
.\.venv\Scripts\python.exe -X utf8 -m unittest tests.test_analyze_negative_theme_release_trends
```

預期：趨勢列、證據列與狀態分類測試全部通過。

### Task 3：產生實際輸出與撰寫方法文件

**檔案：**

- 建立：`docs/methodology/general_release_context_analysis.md`
- 產生：`outputs/tables/negative_theme_release_trends.csv`
- 產生：`outputs/tables/negative_theme_release_trend_evidence.csv`
- 產生：`outputs/tables/negative_theme_release_trends_summary.json`

- [ ] **Step 1：撰寫繁體中文方法文件**

文件需說明資料來源、五個代表案例的選取原則、片語比對限制、28 天區間定義、
每個狀態值的意義，以及不得將結果解釋成 Android 修復結論。

- [ ] **Step 2：執行分析腳本**

```powershell
.\.venv\Scripts\python.exe -X utf8 src\analysis\analyze_negative_theme_release_trends.py `
  --reviews data\processed\reviews_with_sentiment_2025_onward_en_us.csv `
  --candidates outputs\tables\theme_release_candidates.csv `
  --rules configs\negative_theme_monitoring_rules.json `
  --output outputs\tables\negative_theme_release_trends.csv `
  --evidence-output outputs\tables\negative_theme_release_trend_evidence.csv `
  --summary-output outputs\tables\negative_theme_release_trends_summary.json
```

預期：產生 5 列趨勢資料、至少 1 列證據資料，以及摘要 JSON。

- [ ] **Step 3：執行完整測試與輸出檢查**

```powershell
.\.venv\Scripts\python.exe -X utf8 -m unittest discover tests
.\.venv\Scripts\python.exe -X utf8 -c "import csv, json; rows=list(csv.DictReader(open('outputs/tables/negative_theme_release_trends.csv', encoding='utf-8'))); evidence=list(csv.DictReader(open('outputs/tables/negative_theme_release_trend_evidence.csv', encoding='utf-8'))); summary=json.load(open('outputs/tables/negative_theme_release_trends_summary.json', encoding='utf-8')); assert len(rows)==5; assert summary['trend_row_count']==5; assert summary['evidence_row_count']==len(evidence); assert {row['release_scope'] for row in rows}=={'general_product_release'}; print('output validation passed')"
```

預期：所有測試通過，且輸出列數、摘要與更新範圍一致。
