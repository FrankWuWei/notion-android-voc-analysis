import { CoverageStrip } from '../components/CoverageStrip'
import { EvidenceQuote } from '../components/EvidenceQuote'
import { MonitoringEvidence } from '../components/MonitoringEvidence'
import {
  extendedValidationContent,
  findingContent,
  positiveContent,
} from '../content/portfolioContent'
import type { PortfolioSnapshot } from '../types/portfolio'

function formatRate(value: number) {
  const percentage = value * 100
  return percentage === 0 ? '0%' : `${percentage.toFixed(2)}%`
}

export function FindingsSections({ snapshot }: { snapshot: PortfolioSnapshot }) {
  const validationExample = snapshot.extendedValidation.example
  const validationExampleMatches =
    validationExample.before.matchedReviews + validationExample.after.matchedReviews

  return (
    <>
      <section id="findings" className="findings-section" aria-labelledby="findings-title">
        <header className="section-heading section-heading--split">
          <p className="section-label">{findingContent.label}</p>
          <div>
            <h2 id="findings-title">{findingContent.title}</h2>
            <p>{findingContent.introduction}</p>
          </div>
        </header>

        <div className="theme-findings">
          {snapshot.mainThemes.map((theme, index) => {
            const details =
              findingContent.themes[
                theme.id as keyof typeof findingContent.themes
              ]
            if (!details) return null

            return (
              <article className="theme-finding" key={theme.id}>
                <header className="theme-finding__header">
                  <p className="theme-finding__index">
                    {String(index + 1).padStart(2, '0')}
                  </p>
                  <div>
                    <h3>{details.title}</h3>
                    <p>{theme.descriptionZh}</p>
                  </div>
                  <div className="theme-finding__metrics">
                    <p>
                      <strong>{theme.batchCoverage} / {theme.batchCoverageTotal}</strong>
                      <span>分析批次</span>
                    </p>
                    <p>
                      <strong>{theme.evidenceCount}</strong>
                      <span>筆來源證據</span>
                    </p>
                  </div>
                </header>

                <div className="theme-finding__coverage">
                  <CoverageStrip
                    covered={theme.batchCoverage}
                    total={theme.batchCoverageTotal}
                  />
                  <p>代表主題出現在多少分析批次，不是評論發生率。</p>
                </div>

                <div className="theme-finding__evidence">
                  {theme.evidence.map((evidence) => (
                    <EvidenceQuote key={evidence.id} evidence={evidence} />
                  ))}
                </div>

                <div className="validation-direction">
                  <p>待驗證方向</p>
                  <p>{details.validation}</p>
                </div>
              </article>
            )
          })}
        </div>
      </section>

      <section className="positive-section" aria-labelledby="positive-title">
        <header className="section-heading section-heading--split">
          <p className="section-label">{positiveContent.label}</p>
          <div>
            <h2 id="positive-title">{positiveContent.title}</h2>
            <p>{positiveContent.introduction}</p>
          </div>
        </header>

        <div className="positive-values">
          {snapshot.positiveValues.map((value, index) => {
            const description =
              positiveContent.values[
                value.id as keyof typeof positiveContent.values
              ]
            if (!description) return null

            return (
              <article key={value.id}>
                <p className="positive-values__index">
                  {String(index + 1).padStart(2, '0')}
                </p>
                <h3>{value.nameZh}</h3>
                <p className="positive-values__description">{description}</p>
                <EvidenceQuote evidence={value.evidence} />
              </article>
            )
          })}
        </div>
      </section>

      <section className="extended-section" aria-labelledby="extended-title">
        <header className="section-heading section-heading--split">
          <p className="section-label">{extendedValidationContent.label}</p>
          <div>
            <h2 id="extended-title">{extendedValidationContent.title}</h2>
            <p>{extendedValidationContent.introduction}</p>
          </div>
        </header>

        <div className="extended-layout">
          <div>
            <p className="extended-layout__heading">監測方法</p>
            <ol className="monitoring-steps">
              {extendedValidationContent.steps.map((step, index) => (
                <li key={step}>
                  <span>{String(index + 1).padStart(2, '0')}</span>
                  <p>
                    {index === 1
                      ? step.replace('28', String(snapshot.extendedValidation.windowDays))
                      : step}
                  </p>
                </li>
              ))}
            </ol>
          </div>

          <aside className="validation-status" aria-label="目前延伸驗證狀態">
            <p className="validation-status__label">目前實際狀態</p>
            <div className="validation-status__numbers">
              <p>
                <strong>{snapshot.extendedValidation.candidateCases}</strong>
                <span>個候選案例</span>
              </p>
              <p>
                <strong>{snapshot.extendedValidation.ruleMatchedReviews}</strong>
                <span>筆規則命中評論</span>
              </p>
            </div>
            <h3>{extendedValidationContent.statusTitle}</h3>
            <p className="validation-status__summary">
              {extendedValidationContent.statusSummary}
            </p>
          </aside>
        </div>

        <article className="validation-example" aria-labelledby="validation-example-title">
          <header className="validation-example__header">
            <p className="section-label">{extendedValidationContent.exampleLabel}</p>
            <div>
              <h3 id="validation-example-title">{validationExample.themeNameZh}</h3>
              <p>
                固定時間切點 {validationExample.releaseDate} · 前後各{' '}
                {validationExample.windowDays} 天
              </p>
            </div>
          </header>

          <div className="validation-example__body">
            <div>
              <dl className="validation-example__context">
                <div>
                  <dt>時間切點</dt>
                  <dd>公開產品更新</dd>
                </div>
                <div>
                  <dt>主題規則</dt>
                  <dd>{validationExample.rulePhrases.join(' · ')}</dd>
                </div>
              </dl>

              <table
                className="validation-example__table"
                aria-label={`${validationExample.themeNameZh}前後觀察比較`}
              >
                <thead>
                  <tr>
                    <th scope="col">觀察期間</th>
                    <th scope="col">可比較評論</th>
                    <th scope="col">規則命中</th>
                    <th scope="col">命中率</th>
                  </tr>
                </thead>
                <tbody>
                  <tr>
                    <th scope="row">前 {validationExample.windowDays} 天</th>
                    <td>{validationExample.before.eligibleReviews}</td>
                    <td>{validationExample.before.matchedReviews}</td>
                    <td>{formatRate(validationExample.before.matchRate)}</td>
                  </tr>
                  <tr>
                    <th scope="row">後 {validationExample.windowDays} 天</th>
                    <td>{validationExample.after.eligibleReviews}</td>
                    <td>{validationExample.after.matchedReviews}</td>
                    <td>{formatRate(validationExample.after.matchRate)}</td>
                  </tr>
                </tbody>
              </table>

              <div className="validation-example__decision">
                <p>{extendedValidationContent.decisionLabel}</p>
                <h4>{extendedValidationContent.decision}</h4>
                <ul>
                  <li>整個案例只有 {validationExampleMatches} 筆規則命中評論。</li>
                  {extendedValidationContent.decisionReasons.map((reason) => (
                    <li key={reason}>{reason}</li>
                  ))}
                </ul>
              </div>
            </div>

            <MonitoringEvidence evidence={validationExample.evidence} />
          </div>
        </article>
      </section>
    </>
  )
}
