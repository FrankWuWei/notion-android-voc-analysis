export const chapters = [
  { id: 'overview', number: '01', label: '專案概覽' },
  { id: 'method', number: '02', label: '分析方法' },
  { id: 'quality', number: '03', label: '品質驗證' },
  { id: 'findings', number: '04', label: '分析發現' },
  { id: 'delivery', number: '05', label: '工程交付' },
] as const

export const heroContent = {
  eyebrow: 'Notion Android 使用者回饋分析',
  title: '結案報告-建立可重跑、可驗證的 AI 使用者回饋分析流程',
  description:
    '以 Notion Google Play 應用程式公開評論為資料來源，將零散的非結構化回饋整理成可追溯的問題主題、來源證據與待驗證方向。',
} as const

export const approachContent = {
  label: '分析思路',
  title: '先讓資料可用，再決定分析深度，最後整理問題主題',
  introduction: (rawReviews: number, effectiveReviews: number) =>
    `本專案先蒐集 ${rawReviews.toLocaleString('en-US')} 則公開評論，經過資料清理後保留 ${effectiveReviews.toLocaleString('en-US')} 則有效資料；接著以情緒分流控制深入分析範圍，再用大型語言模型整理問題主題。`,
  steps: [
    {
      number: '01',
      title: '資料清理',
      description: '移除無效與重複內容，讓評論成為可分析的資料。',
    },
    {
      number: '02',
      title: '情緒分流',
      description: '辨識需要優先保留的訊號，控制深入分析的範圍。',
    },
    {
      number: '03',
      title: '大型語言模型分析',
      description: '從零散文字中整理反覆出現的具體問題主題。',
    },
  ],
  handoff:
    '但把三個步驟串接起來，並不代表結果自然可靠；每個階段仍有一個關鍵問題需要處理。',
} as const

export const challengeContent = {
  label: '問題與難點',
  title: '把評論整理成可靠結論，比分類正負面更困難',
  introduction:
    '真正的難點出現在每個階段的判斷邊界：哪些資料應該保留、情緒分流會不會漏掉訊號，以及模型整理出的主題是否真的有來源支持。',
  items: [
    {
      number: '01',
      title: '評論需要判斷，不只是清理',
      description:
        '評論可能過短、重複、使用不同語言，文字內容也可能與星等互相衝突。只按照星等或模型標籤分類，容易錯過真正的問題訊號。',
    },
    {
      number: '02',
      title: '情緒分類不能回答使用者遇到什麼問題',
      description:
        '正面或負面只能作為初步分流，無法區分效能、同步、編輯操作或功能缺口，因此還需要進一步的主題分析。',
    },
    {
      number: '03',
      title: '大型語言模型輸出需要回到來源驗證',
      description:
        '模型可能改寫引文、填錯星等，甚至把真實評論放到不相符的主題。每筆來源證據都必須能連回原始 review_id 與逐字內容。',
    },
  ],
} as const

export const processContent = {
  label: '02 / 分析方法',
  title: '整體分析流程',
  introduction:
    '每個階段都保留明確輸入、判斷規則與輸出，讓分析可以分段重跑，也能追查數字如何產生。',
  stages: [
    {
      number: '01',
      title: '準備可分析資料',
      detail:
        '移除空值、過短內容與重複資料，正規化文字格式，同時保留否定詞、標點與原始識別碼。',
    },
    {
      number: '02',
      title: '保留情緒不確定性',
      detail:
        '低信心、三星評論，或文字情緒與星等衝突時，不強制歸類為正面或負面。',
    },
    {
      number: '03',
      title: '控制深入分析範圍',
      detail:
        '負面與不確定評論完整保留；正向評論使用 500 則代表樣本補充產品價值背景。',
    },
    {
      number: '04',
      title: '產生結構化主題',
      detail:
        '要求大型語言模型以固定欄位輸出主題、產品面向、嚴重程度、待驗證方向與來源證據。',
    },
    {
      number: '05',
      title: '回查與修正模型輸出',
      detail:
        '比對 review_id、星等與引用原文；非逐字引文必須進入版本化人工語意稽核。',
    },
    {
      number: '06',
      title: '統一跨批次主題',
      detail:
        '以版本化規則整併相近主題，同時保留來源主題、分析批次與 evidence 的完整對應。',
    },
  ],
} as const

export const decisionContent = {
  label: '核心技術決策',
  title: '三項核心技術決策',
  introduction:
    '這些決定不是實作細節，而是用來控制分析成本、可信度與跨批次一致性的主要邊界。',
  items: [
    {
      number: '01',
      title: '控制深入分析的評論範圍',
      problem:
        '所有有效評論都送入大型語言模型會增加成本，也會讓大量簡短正向評論稀釋問題訊號。',
      decision:
        '完整保留負向與不確定評論，正向評論抽取 500 則代表樣本。',
      reason:
        '優先保留潛在問題，同時仍能觀察使用者肯定的產品價值。',
      limitation:
        '正向結果只能描述代表樣本，不能推論完整正向評論的主題比例。',
    },
    {
      number: '02',
      title: '模型輸出必須通過來源回查',
      problem:
        '固定 JSON 格式只能控制結構，不能保證引文、星等及主題關係正確。',
      decision:
        '以 review_id 回查星等和逐字原文；非逐字引文必須經人工語意稽核。',
      reason:
        '正式結果需要能追溯，不能只因格式正確就直接採用。',
      limitation:
        '人工語意稽核完整涵蓋 35 筆非逐字引文，不代表已人工閱讀全部 645 筆 evidence。',
    },
    {
      number: '03',
      title: '把分散的批次主題整併成一致分類',
      problem:
        '不同批次會用不同名稱描述相近問題，159 個批次主題無法直接比較。',
      decision:
        '使用版本化規則整併成 17 個主題家族，並保留來源 mapping。',
      reason:
        '相同輸入可以重跑出一致結果，分類規則也能被檢查與調整。',
      limitation:
        '17 個主題只能描述批次覆蓋與代表 evidence，不是 6,186 則評論的完整主題發生率。',
    },
  ],
} as const

export const qualityContent = {
  label: '03 / 品質驗證',
  title: '引文可以回查，不代表主題判斷正確',
  introduction:
    '這筆案例的 review_id 真實存在，但模型產生的引文不在來源評論中，來源內容也不支持原本的錯誤與資料遺失分類。',
  modelOutputLabel: '模型原始輸出',
  sourceLabel: 'review_id 對應的真實評論',
  verdict: '移除這筆 evidence，而不是自動替換引文。',
  principle:
    '驗證不只確認資料來自哪裡，也要確認來源是否支持模型做出的分類。',
} as const

export const findingContent = {
  label: '04 / 分析發現',
  title: '跨批次反覆出現的三個主要問題',
  introduction:
    '這裡呈現的是主題在已驗證分析批次中的反覆訊號，不是 6,186 則評論的發生率，也不是產品優先級排行。',
  themes: {
    performance_stability: {
      title: '問題一:效能與穩定性',
      validation:
        '依裝置等級、App 版本與頁面複雜度，量測開頁時間、資料庫載入時間與異常退出率。',
    },
    sync_offline_data_integrity: {
      title: '問題二:同步、離線與資料完整性',
      validation:
        '分別測試離線讀取、離線編輯、重新連線同步與衝突處理，確認內容保存狀態是否清楚且可靠。',
    },
    editing_input_controls: {
      title: '問題三:編輯、輸入與操作控制',
      validation:
        '建立手機、平板、螢幕鍵盤與實體鍵盤的操作矩陣，驗證文字選取、複製貼上、游標與區塊移動。',
    },
  },
} as const

export const positiveContent = {
  label: '正向價值補充',
  title: '正向代表樣本中，使用者肯定哪些價值',
  introduction:
    '正向結果來自 500 則代表樣本，用來補充產品價值背景，不代表完整正向評論的主題比例，也不與負面主題比較高低。',
  values: {
    productivity_organization_value:
      '使用者將 Notion 同時用於工作、客戶與個人生活管理。',
    ai_assistance_value:
      'AI 的價值不只是回答問題，也包含協助建立與整理內容，降低設定門檻。',
    customization_template_value:
      '模板與自訂能力讓使用者能快速建立符合個人需求的工作方式。',
  },
} as const

export const extendedValidationContent = {
  label: '延伸驗證設計',
  title: '從主題發現，延伸到更新前後的評論訊號監測',
  introduction:
    '這段分析使用公開更新作為固定時間切點，但只把差異視為觀察訊號，不推論更新造成或改善了 Android 問題。',
  steps: [
    '選擇公開產品更新作為固定時間切點。',
    '建立更新前後各 28 天的觀察區間。',
    '限定可比較的負面評論母體。',
    '使用版本化關鍵詞組辨識主題訊號。',
    '比較命中數、母體數與命中率，並檢查樣本是否足夠。',
  ],
  statusTitle: '已完成驗證，結果保留為監測基線',
  statusSummary:
    '三個候選案例都已完成固定時間窗與規則命中計算；現有證據足以展示監測方法，尚不足以形成改善結論。',
  exampleLabel: '實際案例',
  decisionLabel: '案例判定',
  decision: '資料不足，保留為後續監測基線',
  decisionReasons: [
    '公開產品更新沒有明確的 Android 修復範圍。',
    '後期零筆命中只表示觀察期間沒有捕捉到相同規則訊號。',
  ],
} as const

export const engineeringContent = {
  label: '05 / 工程交付',
  title: '分析結果可以從來源重新產生',
  introduction:
    '資料處理、規則、正式產物與驗證彼此分開保存，不依賴單次 Notebook 執行狀態。',
  structure: [
    { path: 'configs/', description: '版本化分類與稽核規則' },
    { path: 'src/analysis/', description: '各階段分析與驗證程式' },
    { path: 'outputs/tables/', description: '中間與最終結果表' },
    { path: 'tests/', description: '關鍵資料轉換測試' },
    { path: 'docs/methodology/', description: '方法與判斷紀錄' },
  ],
  proofs: [
    {
      title: '各階段可以獨立執行',
      description:
        '資料清理、情緒分流、批次準備、輸出驗證與主題整併分別由獨立程式負責。',
    },
    {
      title: '分類與稽核決策有版本紀錄',
      description:
        '情緒條件、35 筆引用稽核決策與 17 個主題家族整併規則皆可追查。',
    },
    {
      title: '中間與最終產物分開保存',
      description:
        '原始模型輸出、修復後輸出、稽核報告、mapping 與 evidence 表不互相覆蓋。',
    },
    {
      title: '驗證可以重複執行',
      description:
        '分析測試涵蓋清理、分流、批次、引用驗證、語意淘汰、主題整併與延伸觀察。',
    },
  ],
} as const

export const boundaryContent = {
  title: '分析範圍、解讀邊界與後續方向',
  foundation: [
    '找出反覆出現在多個批次的問題家族。',
    '保留能連回原始評論的 evidence。',
    '建立模型輸出檢查、語意稽核與淘汰流程。',
    '將一次性分析延伸成可重跑的處理與監測方法。',
  ],
  cautions: [
    '批次覆蓋不等於 6,186 則評論中的發生率。',
    '17 個主題不是完整母體的產品優先級排行。',
    '645 筆 evidence 都能回查來源，但沒有全部經過人工語意審核。',
    '公開產品更新只能作為時間切點，不能用來推論 Android 改善成效。',
    '美國區英文評論不能代表所有地區與語言的使用者。',
  ],
  nextSteps: [
    '建立完整評論的多標籤主題分類。',
    '建立人工標註測試集，量測分類準確度。',
    '加入單筆模型重判與再次驗證機制。',
    '取得 Android 專屬更新與版本資料。',
    '擴大人工語意抽查與多地區分析。',
  ],
} as const
