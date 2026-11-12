import snapshotData from './data/portfolioSnapshot.json'
import { ChapterNavigation } from './components/ChapterNavigation'
import {
  approachContent,
  challengeContent,
  heroContent,
} from './content/portfolioContent'
import { DeliverySections } from './sections/DeliverySections'
import { FindingsSections } from './sections/FindingsSections'
import { MethodSections } from './sections/MethodSections'
import { QualitySection } from './sections/QualitySection'
import type { PortfolioSnapshot } from './types/portfolio'

const snapshot = snapshotData as PortfolioSnapshot

function App() {
  return (
    <div className="page-shell">
      <a className="skip-link" href="#main-content">跳至主要內容</a>
      <ChapterNavigation />

      <main id="main-content" className="case-study">
        <section id="overview" className="hero" aria-labelledby="project-title">
          <div className="hero__content">
            <p className="eyebrow">{heroContent.eyebrow}</p>
            <h1 id="project-title">{heroContent.title}</h1>
            <p className="hero__description">{heroContent.description}</p>
          </div>

          <div className="hero__scope" aria-label="分析資料範圍">
            <p className="hero__metric">
              <strong>{snapshot.scope.effectiveReviews.toLocaleString('en-US')}</strong>
              <span>納入分析的有效評論</span>
            </p>
            <dl className="scope-list">
              <div>
                <dt>來源</dt>
                <dd>{snapshot.scope.store} · {snapshot.scope.platform}</dd>
              </div>
              <div>
                <dt>範圍</dt>
                <dd>{snapshot.scope.market} English reviews</dd>
              </div>
              <div>
                <dt>期間</dt>
                <dd>{snapshot.scope.periodStart} — {snapshot.scope.periodEnd}</dd>
              </div>
            </dl>
          </div>

          <a className="scroll-cue" href="#approach">
            <span>向下閱讀</span>
            <span className="scroll-cue__line" aria-hidden="true" />
          </a>
        </section>

        <div
          id="approach"
          className="approach-bridge"
          role="region"
          aria-labelledby="approach-title"
        >
          <header className="approach-bridge__header">
            <div>
              <p className="section-label">{approachContent.label}</p>
              <h2 id="approach-title">{approachContent.title}</h2>
            </div>
            <p>
              {approachContent.introduction(
                snapshot.scope.rawReviews,
                snapshot.scope.effectiveReviews,
              )}
            </p>
          </header>

          <ol className="approach-steps">
            {approachContent.steps.map((step) => (
              <li key={step.number}>
                <span aria-hidden="true">{step.number}</span>
                <div>
                  <h3>{step.title}</h3>
                  <p>{step.description}</p>
                </div>
              </li>
            ))}
          </ol>

          <p className="approach-bridge__handoff">{approachContent.handoff}</p>
        </div>

        <section id="challenge" className="challenge" aria-labelledby="challenge-title">
          <div className="challenge__introduction">
            <p className="section-label">01 / {challengeContent.label}</p>
            <h2 id="challenge-title">{challengeContent.title}</h2>
            <p>{challengeContent.introduction}</p>
          </div>

          <ol className="challenge-list">
            {challengeContent.items.map((item) => (
              <li key={item.number}>
                <span className="challenge-list__number" aria-hidden="true">
                  {item.number}
                </span>
                <div>
                  <h3>{item.title}</h3>
                  <p>{item.description}</p>
                </div>
              </li>
            ))}
          </ol>
        </section>

        <MethodSections snapshot={snapshot} />
        <QualitySection snapshot={snapshot} />
        <FindingsSections snapshot={snapshot} />
        <DeliverySections snapshot={snapshot} />
      </main>
    </div>
  )
}

export default App
