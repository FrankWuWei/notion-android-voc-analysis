# Notion Android VOC 作品集 Dashboard 實作計畫

> **For agentic workers:** 使用 inline execution 依序完成各項工作，並在每個前端行為完成後驗證。

**目標：** 建立一個 Vite + React + TypeScript 靜態 dashboard，視覺化既有 Notion Android VOC 分析流程、五個更新前後案例與 19 筆證據。

**架構：** `web/` 是獨立前端專案；`src/data/dashboardData.ts` 保存由既有 CSV/JSON 摘要出的靜態資料快照，`App.tsx` 負責篩選與選取狀態，CSS 負責響應式 Analysis Fieldbook 視覺。原始 CSV/JSON 不會被前端修改。

**技術：** Vite、React、TypeScript、Vitest、Testing Library、Lucide React、CSS。

## 工作項目

### Task 1：建立前端專案與測試環境

- 建立 Vite React TypeScript 專案於 `web/`。
- 安裝 `lucide-react`、`vitest`、`jsdom`、`@testing-library/react` 與 `@testing-library/jest-dom`。
- 將 `npm test` 設定為一次執行 Vitest。
- 新增 `src/test/setup.ts` 與最小 smoke test，確認測試環境可運作。

### Task 2：建立資料快照與先失敗的 UI 測試

- 建立 `src/data/dashboardData.ts`，含 6,186 則評論、3 個 bucket、5 個趨勢案例、
  19 筆證據、pipeline 階段與限制文案。
- 先建立 `src/App.test.tsx`，驗證首屏摘要、五個案例、狀態篩選與選取主題後的證據。
- 先執行測試，確認未實作 dashboard 時正確失敗。

### Task 3：實作 dashboard 與響應式視覺

- 建立摘要列、pipeline 軌跡、趨勢表、狀態篩選、主題詳情與證據前後切換。
- 使用 `DM Mono` 與 `Manrope`、灰白工作底、墨黑文字、藍綠資訊色與珊瑚警示色。
- 保持資料工具介面，避免行銷頁 hero、裝飾性漸層、過度圓角與巢狀卡片。
- 在手機寬度將雙欄改為單欄，證據表改為可掃讀的條列資料。

### Task 4：建置與瀏覽器驗證

- 執行 `npm test` 與 `npm run build`。
- 啟動 Vite dev server。
- 以 Playwright 驗證桌面與手機 viewport：首屏非空白、五個案例顯示、篩選與主題選取互動正常、文字沒有溢出或重疊。
