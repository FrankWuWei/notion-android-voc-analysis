# Notion Android VOC 作品集網頁：新 task 交接說明

## 使用方式

開啟新的 Codex task 後，先要求讀取本文件與實際 repo，再開始討論網頁規劃。
本文件只整理已完成事實、已確認偏好與尚未決定事項，不代表新版畫面已定案。

## 新 task 開場文字

```text
請先讀取 docs/portfolio_dashboard_new_thread_handoff.md，並檢查目前 repo 與 web/ 的實際內容。

這次要重新規劃 Notion Android VOC 作品集網頁。請先整理既有內容與提出「純文字的頁面資訊架構」，清楚區分：
1. repo 已有的事實與數據；
2. 已確認的呈現偏好；
3. 仍需討論的設計選擇。

在資訊架構與首頁內容確認前，不要直接修改 React，也不要自行增加新的標題、卡片、分析結論或設計概念。每次提出設計建議時要說明原因，並先取得確認。
```

## 專案目的

- 以 Notion Android App 的 Google Play 使用者評論練習非結構文字分析。
- 展示如何從大量客戶回饋辨識產品痛點，並轉換成可討論、可驗證的產品建議。
- 作品集主要面向資料分析、AI 應用及相關職缺的面試官。
- 定位偏向「AI 應用型資料分析」，不是單純展示一個前端 dashboard。

## 已完成的資料流程

1. 使用 `google-play-scraper` 蒐集 Notion Android 的 Google Play 評論。
2. 資料條件為 `lang=en`、`country=us`，日期為 2025-01-01 之後。
3. 保留 `data/raw/` 原始資料，清洗結果另存於 `data/interim/` 與 `data/processed/`。
4. 清洗包含空值、無意義文字、重複評論、空白、HTML entity 與 NFKC Unicode 正規化；不移除否定詞和有語意的標點。
5. 使用 `distilbert/distilbert-base-uncased-finetuned-sst-2-english` 執行情緒分類。
6. 結合模型信心與星等，產生 `positive`、`negative`、`mixed_or_uncertain` 三個 `sentiment_bucket`。
7. 依 bucket 分流並建立 LLM 批次輸入；負面與不確定評論優先保留，正面評論採代表性取樣。
8. 透過 OpenAI Batch API 產生主題、產品面向、嚴重程度、證據與排除原因等結構化 JSON。
9. 以程式檢查 `review_id`、星等與引用文字，再由 `review_id` 補回日期、版本與按讚數。
10. 使用公開產品更新資訊建立固定期間觀察，但只作為一般產品脈絡及時間切點。
11. 將正式資料產物轉成前端靜態快照，供 React 作品集讀取。

## 現行可驗證數字

以下數字來自目前 repo 的正式資料快照與彙總檔，開新 task 時仍應再次核對：

| 項目 | 現行數字 |
| --- | ---: |
| 原始評論 | 6,269 |
| 清洗後有效評論 | 6,186 |
| LLM 入選評論 | 3,183 |
| LLM 批次 | 23 / 23 |
| 驗證後主題 | 159 |
| 可回查主題證據 | 652 |
| 最終驗證錯誤 | 0 |
| 固定期間代表案例 | 3 |
| 固定期間案例證據 | 6 |

目前情緒 bucket 的已驗證筆數：

| Bucket | 筆數 |
| --- | ---: |
| `positive` | 3,503 |
| `negative` | 1,209 |
| `mixed_or_uncertain` | 1,474 |

重要差異：舊版 dashboard 規格仍可能出現「5 個案例、19 筆證據」，但目前正式快照已更新為「3 個代表案例、6 筆固定期間證據」。新版網頁必須以現行快照與來源表為準。

## 正式資料與程式位置

- 清洗及情緒結果：`data/processed/reviews_with_sentiment_2025_onward_en_us.csv`
- LLM 輸入清單：`data/processed/llm_inputs/manifest.json`
- LLM 正式輸出：`outputs/reports/llm_batch_outputs_api_repaired_enriched/`
- 固定期間觀察：`outputs/tables/negative_theme_release_trends.csv`
- 固定期間證據：`outputs/tables/negative_theme_release_trend_evidence.csv`
- 觀察彙總：`outputs/tables/negative_theme_release_trends_summary.json`
- 監控規則：`configs/negative_theme_monitoring_rules.json`
- 前端快照產生程式：`src/analysis/build_dashboard_snapshot.py`
- 前端正式快照：`web/src/data/dashboardSnapshot.ts`

`web/src/data/dashboardSnapshot.ts` 是展示用衍生資料，不是最終事實來源。需要更新數據時，應修改或重跑資料流程，不要手動竄改快照數字。

## 現有網頁實作

- 前端位置：`web/`
- 技術：Vite、React、TypeScript、Vitest、Lucide React、CSS。
- 主要頁面：`web/src/App.tsx`
- 主要樣式：`web/src/App.css`
- 前端資料轉換：`web/src/data/dashboardData.ts`
- 產生的資料快照：`web/src/data/dashboardSnapshot.ts`
- 目前正式網頁仍是淺色系，並已包含固定導覽、流程、LLM 品質、產品訊號、固定期間觀察、原始證據與建議等區段。

`.superpowers/brainstorm/` 內的深色首頁預覽只是討論草稿，不是正式網頁，也不是已核准需求。不要直接照該草稿實作。

## 已確認的呈現偏好

- 全站文案使用繁體中文；模型 ID、欄位名稱、路徑與 bucket 值保留原始英文。
- 移除「我、我們、我想回答的問題」等第一人稱表述。
- 用一般讀者能理解的中文說明專有名詞，不要堆疊沒有解釋的英文標記。
- 整體必須簡潔、有條理，清楚說明專案為何進行、過程做了哪些選擇、得到哪些結果。
- 「起承轉合」只代表敘事順序概念，不可直接成為頁面標題。
- 導覽列需要固定在畫面上，方便快速切換區段。
- 內文與細部文字需要維持足夠尺寸，不可為了塞入資訊而縮得過小。
- 不使用沒有清楚用途的箭頭、大括號、裝飾符號或標籤。
- 避免過多卡片、巢狀卡片、裝飾圖形與一次塞入大量資訊。
- 視覺偏好為深色、專業的 AI 分析介面，但深色首頁的實際內容與版面仍未定案。
- 第一屏不應直接堆入完整資料流程、模型名稱與分析成果；已選擇先從問題背景切入，但實際文案尚未核准。

## 尚未決定的內容

- 首頁主標題以外應顯示哪些文字與數字。
- 首頁是否顯示 `6,186` 等資料規模。
- 問題背景要用段落、條列或其他形式呈現。
- 新版完整區段順序與每一區的資訊量。
- 深色視覺的色彩、版面比例與元件形式。
- 哪些現有區段保留、合併、移動或刪除。

以上項目應先用純文字資訊架構討論，不應由新 task 自行補完。

## 分析結論的表達邊界

- 公開產品更新只能作為一般產品脈絡或固定期間比較的時間切點。
- 不能宣稱某次公開更新已修復或造成 Android 問題。
- `not_observed_after_release` 只表示固定期間內未觀察到相同規則命中，不等於問題已修復。
- `limited_post_evidence` 表示更新後仍有少量相關評論，樣本不足以形成強結論。
- 產品建議必須寫成待驗證方向，不能包裝成已證實的改善方案。
- 重要數字與結論需要能回查原始 `review_id`。

## 新 task 的建議工作順序

1. 先讀本文件與上述正式資料檔。
2. 檢查 `web/src/App.tsx` 與實際執行畫面，說明目前內容有哪些問題。
3. 先提出純文字的頁面區段順序與每區目的，不製作 mockup、不修改程式。
4. 將「現有事實」與「設計建議」分開列出，避免把建議寫成既定需求。
5. 取得確認後，再討論首頁文案與資訊密度。
6. 首頁與完整資訊架構確認後，才修改 React/CSS。
7. 完成後執行測試、建置，並用實際瀏覽器檢查桌面與手機畫面。

## 常用驗證命令

在 `web/` 目錄執行：

```powershell
npm test
npm run build
npm run dev -- --host 127.0.0.1 --port 5173
```

若 `5173` 已被占用，改用其他未使用的 port，並在交付時提供實際網址。
