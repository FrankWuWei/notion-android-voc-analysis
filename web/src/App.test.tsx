import { fireEvent, render, screen, within } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import App from './App'
import snapshotData from './data/portfolioSnapshot.json'
import type { PortfolioSnapshot } from './types/portfolio'

const snapshot = snapshotData as PortfolioSnapshot

describe('portfolio application shell', () => {
  it('shows the approved project claim and only the core hero metric', () => {
    render(<App />)

    const hero = screen.getByRole('region', {
      name: '建立可重跑、可驗證的 AI 使用者回饋分析流程',
    })
    expect(
      within(hero).getByRole('heading', {
        name: '建立可重跑、可驗證的 AI 使用者回饋分析流程',
      }),
    ).toBeInTheDocument()
    expect(within(hero).getByText('6,186')).toBeInTheDocument()
    expect(within(hero).getByText('納入分析的有效評論')).toBeInTheDocument()
    expect(within(hero).queryByText('情緒分流')).not.toBeInTheDocument()
    expect(within(hero).queryByText('645')).not.toBeInTheDocument()
  })

  it('explains the three-layer analysis approach before presenting its risks', () => {
    render(<App />)

    const approach = screen.getByRole('region', {
      name: '先讓資料可用，再決定分析深度，最後整理問題主題',
    })
    const challenge = screen.getByRole('region', {
      name: '把評論整理成可靠結論，比分類正負面更困難',
    })

    expect(within(approach).getAllByRole('heading', { level: 3 })).toHaveLength(3)
    expect(within(approach).getByText('資料清理')).toBeInTheDocument()
    expect(within(approach).getByText('情緒分流')).toBeInTheDocument()
    expect(within(approach).getByText('大型語言模型分析')).toBeInTheDocument()
    expect(
      within(approach).getByText(
        /先蒐集 6,269 則公開評論，經過資料清理後保留 6,186 則有效資料/,
      ),
    ).toBeInTheDocument()
    expect(
      within(approach).getByText(/並不代表結果自然可靠/),
    ).toBeInTheDocument()
    expect(approach.nextElementSibling).toBe(challenge)
  })

  it('renders the three approved problem statements without card metrics', () => {
    render(<App />)

    const challenge = screen.getByRole('region', {
      name: '把評論整理成可靠結論，比分類正負面更困難',
    })
    expect(
      within(challenge).getByRole('heading', {
        name: '把評論整理成可靠結論，比分類正負面更困難',
      }),
    ).toBeInTheDocument()
    expect(within(challenge).getAllByRole('heading', { level: 3 })).toHaveLength(3)
    expect(within(challenge).getByText('評論需要判斷，不只是清理')).toBeInTheDocument()
  })

  it('loads a traceable, internally consistent static snapshot', () => {
    expect(snapshot.pipeline.validatedBatches).toBe(
      snapshot.pipeline.expectedBatches,
    )
    expect(snapshot.pipeline.sourceValidationErrors).toBe(0)
    expect(snapshot.mainThemes).toHaveLength(3)
    expect(snapshot.mainThemes.every((theme) => theme.evidence.length === 2)).toBe(
      true,
    )
    expect(snapshot.positiveValues).toHaveLength(3)
  })

  it('renders all ten approved report sections and the quality-control case', () => {
    render(<App />)

    const requiredHeadings = [
      '建立可重跑、可驗證的 AI 使用者回饋分析流程',
      '把評論整理成可靠結論，比分類正負面更困難',
      '整體分析流程',
      '三項核心技術決策',
      '引文可以回查，不代表主題判斷正確',
      '跨批次反覆出現的三個主要問題',
      '正向代表樣本中，使用者肯定哪些價值',
      '從主題發現，延伸到更新前後的評論訊號監測',
      '分析結果可以從來源重新產生',
      '分析範圍、解讀邊界與後續方向',
    ]

    requiredHeadings.forEach((heading) => {
      expect(screen.getByRole('heading', { name: heading })).toBeInTheDocument()
    })
    expect(
      screen.getByText((_, element) =>
        Boolean(
          element?.tagName === 'BLOCKQUOTE' &&
            element.textContent?.includes(snapshot.qualityCase.modelQuote),
        ),
      ),
    ).toBeInTheDocument()
    expect(
      screen.getByText((_, element) =>
        Boolean(
          element?.tagName === 'BLOCKQUOTE' &&
            element.textContent?.includes(snapshot.qualityCase.sourceReview),
        ),
      ),
    ).toBeInTheDocument()
    expect(screen.getByText('35')).toBeInTheDocument()
    expect(screen.getByText('28')).toBeInTheDocument()
    expect(screen.getByText('7')).toBeInTheDocument()
    expect(screen.getByText(/23 \/ 23/)).toBeInTheDocument()
    expect(screen.getByText(/不等於模型語意準確率 100%/)).toBeInTheDocument()
  })

  it('shows three batch-coverage strips with a non-prevalence boundary', () => {
    render(<App />)

    const strips = screen.getAllByRole('img', {
      name: /不代表評論發生率/,
    })
    expect(strips).toHaveLength(3)
    expect(strips[0]).toHaveAttribute(
      'aria-label',
      '主題出現在 19 個分析批次中的 19 個，不代表評論發生率',
    )
  })

  it('expands source metadata inline for representative evidence', () => {
    render(<App />)

    const sourceButtons = screen.getAllByRole('button', { name: '查看來源' })
    expect(sourceButtons).toHaveLength(9)
    const firstFigure = sourceButtons[0].closest('figure')
    expect(firstFigure).not.toBeNull()

    fireEvent.click(sourceButtons[0])

    expect(sourceButtons[0]).toHaveAccessibleName('收合來源')
    expect(
      within(firstFigure!).getByText(snapshot.mainThemes[0].evidence[0].reviewId),
    ).toBeInTheDocument()
    expect(within(firstFigure!).getByText('0.6.3424')).toBeInTheDocument()
  })

  it('shows a real monitoring example and keeps its interpretation bounded', () => {
    render(<App />)

    const extended = screen.getByRole('region', {
      name: '從主題發現，延伸到更新前後的評論訊號監測',
    })
    const comparison = within(extended).getByRole('table', {
      name: /編輯、選取、複製貼上與文字格式操作不順前後觀察比較/,
    })

    expect(within(comparison).getByRole('cell', { name: '61' })).toBeInTheDocument()
    expect(within(comparison).getByRole('cell', { name: '73' })).toBeInTheDocument()
    expect(within(comparison).getByRole('cell', { name: '1.64%' })).toBeInTheDocument()
    expect(
      within(extended).getByRole('heading', {
        name: '資料不足，保留為後續監測基線',
      }),
    ).toBeInTheDocument()
    expect(within(extended).queryByText(/不展示容易造成誤解的趨勢曲線/)).not.toBeInTheDocument()

    const sourceButton = within(extended).getByRole('button', {
      name: '查看案例來源',
    })
    fireEvent.click(sourceButton)

    expect(sourceButton).toHaveAccessibleName('收合案例來源')
    expect(
      within(extended).getByText(
        snapshot.extendedValidation.example.evidence.reviewId,
      ),
    ).toBeInTheDocument()
  })
})
