import { boundaryContent, engineeringContent } from '../content/portfolioContent'
import type { PortfolioSnapshot } from '../types/portfolio'

function BoundaryList({ items }: { items: readonly string[] }) {
  return (
    <ul>
      {items.map((item) => (
        <li key={item}>{item}</li>
      ))}
    </ul>
  )
}

export function DeliverySections({ snapshot }: { snapshot: PortfolioSnapshot }) {
  return (
    <>
      <section id="delivery" className="engineering-section" aria-labelledby="engineering-title">
        <header className="section-heading section-heading--split">
          <p className="section-label">{engineeringContent.label}</p>
          <div>
            <h2 id="engineering-title">{engineeringContent.title}</h2>
            <p>{engineeringContent.introduction}</p>
          </div>
        </header>

        <div className="engineering-layout">
          <div className="artifact-structure" aria-label="專案交付結構">
            <p className="artifact-structure__root">notion-android-voc-analysis/</p>
            <dl>
              {engineeringContent.structure.map((item) => (
                <div key={item.path}>
                  <dt>{item.path}</dt>
                  <dd>{item.description}</dd>
                </div>
              ))}
            </dl>
          </div>

          <ol className="engineering-proofs">
            {engineeringContent.proofs.map((proof, index) => (
              <li key={proof.title}>
                <span>{String(index + 1).padStart(2, '0')}</span>
                <div>
                  <h3>{proof.title}</h3>
                  <p>{proof.description}</p>
                  {index === 3 && (
                    <p className="engineering-proofs__test-count">
                      <strong>{snapshot.engineering.analysisTestCount}</strong>
                      項分析測試通過
                    </p>
                  )}
                </div>
              </li>
            ))}
          </ol>
        </div>
      </section>

      <section className="boundary-section" aria-labelledby="boundary-title">
        <header>
          <p className="section-label">分析邊界</p>
          <h2 id="boundary-title">{boundaryContent.title}</h2>
        </header>

        <div className="boundary-bands">
          <article>
            <p className="boundary-bands__number">01</p>
            <h3>目前已建立的分析基礎</h3>
            <BoundaryList items={boundaryContent.foundation} />
          </article>
          <article>
            <p className="boundary-bands__number">02</p>
            <h3>解讀結果時需要注意</h3>
            <BoundaryList items={boundaryContent.cautions} />
          </article>
          <article className="boundary-bands__next">
            <p className="boundary-bands__number">03</p>
            <h3>後續可補強方向</h3>
            <BoundaryList items={boundaryContent.nextSteps} />
          </article>
        </div>
      </section>

      <footer className="site-footer">
        <p>Notion Android 使用者回饋分析</p>
        <p>可重跑 · 可驗證 · 可追溯</p>
      </footer>
    </>
  )
}
