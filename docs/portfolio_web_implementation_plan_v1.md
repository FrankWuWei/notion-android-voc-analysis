# Notion Android 使用者回饋分析作品集：實作計畫 v1

## 依據

- 內容：`docs/portfolio_web_content_spec_v1.md`。
- 視覺：`docs/portfolio_web_visual_spec_v1.md`。
- 設計審查：`docs/portfolio_web_taste_review_v1.md`。
- 前端目錄：`web/`。
- 明確排除：不讀取、沿用或改寫舊網頁內容與資料結構。

## 技術架構

- Vite、React、TypeScript。
- CSS variables 與一般 CSS。
- 建置時產生 `portfolioSnapshot.json`，瀏覽器執行時不呼叫 API。
- Vitest、Testing Library、ESLint 與 Vite production build。
- 最終以真實瀏覽器驗證桌面、平板與手機畫面。

## 階段一：技術骨架與資料契約

狀態：已完成。

- 在空白 `web/` 建立全新前端。
- 新增 `configs/portfolio_web.v1.json`，版本化保存代表 evidence 與預期數字。
- 新增 `src/analysis/build_portfolio_web_snapshot.py`。
- 由正式分析產物產生 `web/src/data/portfolioSnapshot.json`。
- 驗證資料範圍、分析批次、主題、evidence、人工稽核、延伸驗證與測試數量。
- 建立 TypeScript 型別、基本應用殼層與前端測試。

完成條件：

- Snapshot 可重複產生且內容雜湊一致。
- 59 項既有分析測試通過。
- 前端單元測試、ESLint 與 production build 通過。

## 階段二：第一屏與視覺基礎

狀態：已完成。

- 實作全站 token、字體、內容容器與響應式斷點。
- 實作桌面左側章節導覽與手機頂部章節選單。
- 實作第 1～2 區。
- 在第一屏與問題難點之間加入未編號分析思路導讀，說明資料清理、情緒分流與大型語言模型分析各自的用途。
- 以真實瀏覽器檢查第一屏資訊量、排版與手機單欄結果。
- 通過視覺確認後再進入階段三。

## 階段三：方法與品質驗證

狀態：已完成。

- 實作第 3～5 區。
- 建立六階段資料流、三項核心技術決策與深色品質比較區。
- 驗證內容順序、數字邊界及桌面／手機比較方式。

## 階段四：分析結果與結尾

狀態：已完成。

- 實作第 6～10 區。
- 建立 19 格批次覆蓋條、代表 evidence、正向價值、延伸驗證、工程交付與分析邊界。
- 實作 evidence 原地展開與缺值顯示。

## 階段五：完整驗證

狀態：已完成。

- 執行 snapshot、分析測試、前端測試、ESLint 與 production build。
- 驗證鍵盤操作、focus、語意結構、色彩對比與 `prefers-reduced-motion`。
- 以真實瀏覽器檢查桌面、平板與手機，不允許水平捲動。
- 完成公開前內容檢查，但第一版不加入 GitHub 或完整資料下載連結。

完成結果：

- Snapshot 重建前後 SHA-256 一致。
- 59 項分析測試與 8 項前端測試通過。
- ESLint 與 Vite production build 通過。
- 以 `1440 × 1000`、`900 × 1000`、`390 × 844` 實際瀏覽器尺寸檢查。
- 三種尺寸均無水平捲動，瀏覽器 console 無錯誤或警告。
- 十個主要區段、桌面與行動導覽、evidence 展開及鍵盤 focus 狀態均已確認。
- 公開頁面沒有外部連結，瀏覽器執行時沒有 API 請求。

詳細紀錄：`docs/portfolio_web_verification_report_v1.md`。
