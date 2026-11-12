import { qualityContent } from '../content/portfolioContent'
import type { PortfolioSnapshot } from '../types/portfolio'

export function QualitySection({ snapshot }: { snapshot: PortfolioSnapshot }) {
  const qualityCase = snapshot.qualityCase
  const audit = snapshot.qualityAudit

  return (
    <section id="quality" className="quality-section" aria-labelledby="quality-title">
      <header className="quality-section__heading">
        <p className="section-label">{qualityContent.label}</p>
        <h2 id="quality-title">{qualityContent.title}</h2>
        <p>{qualityContent.introduction}</p>
      </header>

      <div className="quality-comparison">
        <article>
          <p className="quality-comparison__label">{qualityContent.modelOutputLabel}</p>
          <dl className="quality-comparison__metadata">
            <div>
              <dt>theme</dt>
              <dd>{qualityCase.themeId}</dd>
            </div>
            <div>
              <dt>review_id</dt>
              <dd>{qualityCase.reviewId}</dd>
            </div>
          </dl>
          <blockquote>“{qualityCase.modelQuote}”</blockquote>
        </article>

        <article>
          <p className="quality-comparison__label">{qualityContent.sourceLabel}</p>
          <dl className="quality-comparison__metadata">
            <div>
              <dt>score</dt>
              <dd>{qualityCase.score} / 5</dd>
            </div>
            <div>
              <dt>app_version</dt>
              <dd>{qualityCase.appVersion ?? '資料未提供'}</dd>
            </div>
          </dl>
          <blockquote>“{qualityCase.sourceReview}”</blockquote>
        </article>
      </div>

      <div className="quality-verdict">
        <div>
          <p className="quality-verdict__label">最終處理</p>
          <p className="quality-verdict__statement">{qualityContent.verdict}</p>
          <p>{qualityCase.reasonZh}</p>
        </div>
        <p className="quality-verdict__principle">{qualityContent.principle}</p>
      </div>

      <div className="audit-summary" aria-label="非逐字引文人工語意稽核結果">
        <div>
          <strong>{audit.reviewedNonVerbatimQuotes}</strong>
          <span>筆進入人工語意稽核</span>
        </div>
        <span className="audit-summary__arrow" aria-hidden="true">→</span>
        <div>
          <strong>{audit.replacedWithSupportingVerbatimQuote}</strong>
          <span>筆改為支持原主題的逐字內容</span>
        </div>
        <span className="audit-summary__divider" aria-hidden="true">+</span>
        <div>
          <strong>{audit.droppedAsUnsupported}</strong>
          <span>筆因不支持主題而移除</span>
        </div>
      </div>

      <p className="quality-validation-boundary">
        <strong>{snapshot.pipeline.validatedBatches} / {snapshot.pipeline.expectedBatches}</strong>
        {' '}批次通過來源與結構驗證；最終來源驗證錯誤{' '}
        <strong>{snapshot.pipeline.sourceValidationErrors}</strong> 筆。這不等於模型語意準確率 100%。
      </p>
    </section>
  )
}
