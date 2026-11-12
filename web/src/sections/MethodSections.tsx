import { decisionContent, processContent } from '../content/portfolioContent'
import type { PortfolioSnapshot } from '../types/portfolio'

function formatCount(value: number) {
  return value.toLocaleString('en-US')
}

export function MethodSections({ snapshot }: { snapshot: PortfolioSnapshot }) {
  const values = [
    `${formatCount(snapshot.scope.rawReviews)} → ${formatCount(snapshot.scope.effectiveReviews)}`,
    `${formatCount(snapshot.pipeline.sentiment.positive)} / ${formatCount(snapshot.pipeline.sentiment.negative)} / ${formatCount(snapshot.pipeline.sentiment.uncertain)}`,
    `${formatCount(snapshot.scope.effectiveReviews)} → ${formatCount(snapshot.pipeline.deepAnalysisReviews)}`,
    `${formatCount(snapshot.pipeline.deepAnalysisReviews)} → ${snapshot.pipeline.llmBatches} 批次`,
    `${snapshot.pipeline.validatedBatchThemes} 主題 / ${snapshot.pipeline.sourceVerbatimEvidence} 證據`,
    `${snapshot.pipeline.validatedBatchThemes} → ${snapshot.pipeline.canonicalThemes} 主題家族`,
  ]

  return (
    <>
      <section id="method" className="process-section" aria-labelledby="process-title">
        <header className="section-heading section-heading--split">
          <p className="section-label">{processContent.label}</p>
          <div>
            <h2 id="process-title">{processContent.title}</h2>
            <p>{processContent.introduction}</p>
          </div>
        </header>

        <ol className="process-list">
          {processContent.stages.map((stage, index) => (
            <li key={stage.number}>
              <div className="process-list__identity">
                <span>{stage.number}</span>
                <h3>{stage.title}</h3>
              </div>
              <p className="process-list__value">{values[index]}</p>
              <p className="process-list__detail">{stage.detail}</p>
            </li>
          ))}
        </ol>
        <p className="process-boundary">
          數字跟著資料處理階段出現；來源證據代表可逐字回查，不代表全部經過人工語意審核。
        </p>
      </section>

      <section className="decision-section" aria-labelledby="decision-title">
        <header className="section-heading section-heading--split">
          <p className="section-label">{decisionContent.label}</p>
          <div>
            <h2 id="decision-title">{decisionContent.title}</h2>
            <p>{decisionContent.introduction}</p>
          </div>
        </header>

        <ol className="decision-list">
          {decisionContent.items.map((item) => (
            <li key={item.number}>
              <div className="decision-list__title">
                <span>{item.number}</span>
                <h3>{item.title}</h3>
              </div>
              <dl>
                <div>
                  <dt>問題</dt>
                  <dd>{item.problem}</dd>
                </div>
                <div>
                  <dt>決定</dt>
                  <dd>{item.decision}</dd>
                </div>
                <div>
                  <dt>原因</dt>
                  <dd>{item.reason}</dd>
                </div>
                <div>
                  <dt>限制</dt>
                  <dd>{item.limitation}</dd>
                </div>
              </dl>
            </li>
          ))}
        </ol>
      </section>
    </>
  )
}
