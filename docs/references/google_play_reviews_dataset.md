# Google Play 評論資料集

## 範圍

- App: Notion Android
- Google Play app id: `notion.id`
- Language: `en`
- Country: `us`
- 日期範圍：建立時間在 `2025-01-01` 之後，含當天
- 排序方式：由新到舊

## 來源檔案

- `data/raw/notion_android_reviews_google_play_2025_onward_en_us.csv`

## 資料抓取命令

```powershell
.\.venv\Scripts\python.exe src\data_collection\fetch_google_play_reviews.py `
  --batch-size 200 `
  --max-pages 100 `
  --cutoff 2025-01-01 `
  --output data\raw\notion_android_reviews_google_play_2025_onward_en_us.csv
```

## 驗證結果

資料抓取日期：`2026-06-20`。

- 筆數：`6269`
- 不重複 `review_id`：`6269`
- 重複 `review_id`：`0`
- 最早 `review_created_at`：`2025-01-01T03:34:16+00:00`
- 最新 `review_created_at`：`2026-06-19T00:07:18+00:00`
- 早於 `2025-01-01` 的筆數：`0`
