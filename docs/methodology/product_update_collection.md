# 產品更新資訊蒐集

此步驟用來建立後續「痛點是否仍未解決」分析的基礎資料。這裡只蒐集與初步分類產品更新資訊，不直接判斷問題已修復。

## 資料來源

1. Notion 官方 releases
   - URL: `https://www.notion.com/releases`
   - 用途：蒐集公開產品更新標題、日期、摘要與來源連結。

2. Google Play app detail
   - App id: `notion.id`
   - 用途：取得目前 Google Play 上的 app version、最近更新時間、評分等公開 app metadata。

## 產出檔案

Raw data:

- `data/raw/product_updates/notion_releases.html`
- `data/raw/product_updates/notion_google_play_app_detail.json`

Processed data:

- `data/processed/product_updates/notion_release_notes.csv`
- `data/processed/product_updates/notion_release_notes.json`
- `data/processed/product_updates/notion_google_play_app_detail_summary.json`

## Release note 欄位

- `release_id`：由日期與標題產生的穩定識別欄位。
- `release_date`：更新日期。
- `release_version`：若官方頁面有顯示版本號，例如 `3.6`，就放在此欄。
- `release_title`：產品更新標題。
- `release_summary`：更新內容摘要，從官方 releases 頁面解析。
- `affected_area`：依 keyword 初步分類到產品範圍，例如 `mobile_app`、`editing`、`sync`、`ai`。
- `keywords`：觸發分類的關鍵字。
- `source_url`：官方 release note 來源連結。
- `raw_date_text`：原始日期文字，保留供追溯。

## 執行方式

```powershell
.\.venv\Scripts\python.exe src\data_collection\fetch_product_updates.py
```

## 目前限制

此階段不判斷「已修復」。

原因是公開 release note 只能代表官方提到某個方向的更新，不代表 Google Play 使用者遇到的具體痛點已完全消失。因此後續會再結合：

- LLM theme 的 `affected_area`
- 使用者評論的 `review_created_at`
- 使用者評論的 `app_version`
- 更新前後同類抱怨是否持續出現

再產生較保守的狀態欄位：

- `likely_fixed`
- `still_unresolved`
- `possibly_addressed`
- `unknown`

## 方法原則

不要直接刪掉「看起來已修復」的痛點。比較合理的做法是保留所有 theme，再新增一個狀態欄位，讓後續報告能說明判斷依據與不確定性。
