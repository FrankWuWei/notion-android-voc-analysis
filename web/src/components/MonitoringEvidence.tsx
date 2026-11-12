import { useState } from 'react'
import type { MonitoringEvidenceRecord } from '../types/portfolio'

function formatDate(value: string) {
  return value.slice(0, 10)
}

export function MonitoringEvidence({
  evidence,
}: {
  evidence: MonitoringEvidenceRecord
}) {
  const [expanded, setExpanded] = useState(false)
  const sourceId = `monitoring-evidence-${evidence.reviewId}`

  return (
    <figure className="monitoring-evidence">
      <p className="monitoring-evidence__label">實際命中評論</p>
      <blockquote>
        <p>“{evidence.quote}”</p>
      </blockquote>
      <figcaption>
        <button
          type="button"
          className="evidence-quote__toggle"
          aria-expanded={expanded}
          aria-controls={sourceId}
          onClick={() => setExpanded((value) => !value)}
        >
          {expanded ? '收合案例來源' : '查看案例來源'}
          <span aria-hidden="true">{expanded ? '−' : '+'}</span>
        </button>
        <div
          id={sourceId}
          className="evidence-quote__metadata monitoring-evidence__source"
          data-expanded={expanded || undefined}
        >
          <blockquote>
            <p>“{evidence.sourceReview}”</p>
          </blockquote>
          <dl>
            <div>
              <dt>Review ID</dt>
              <dd>{evidence.reviewId}</dd>
            </div>
            <div>
              <dt>評論日期</dt>
              <dd>{formatDate(evidence.reviewCreatedAt)}</dd>
            </div>
            <div>
              <dt>星等</dt>
              <dd>{evidence.score} / 5</dd>
            </div>
            <div>
              <dt>App 版本</dt>
              <dd>{evidence.appVersion ?? '資料未提供'}</dd>
            </div>
            <div>
              <dt>觀察期間</dt>
              <dd>{evidence.period === 'pre' ? '時間切點前' : '時間切點後'}</dd>
            </div>
            <div>
              <dt>命中詞組</dt>
              <dd>{evidence.matchedPhrases.join(' · ')}</dd>
            </div>
          </dl>
        </div>
      </figcaption>
    </figure>
  )
}
