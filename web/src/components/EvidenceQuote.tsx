import { useState } from 'react'
import type { EvidenceRecord } from '../types/portfolio'

function formatDate(value: string) {
  return value.slice(0, 10)
}

export function EvidenceQuote({ evidence }: { evidence: EvidenceRecord }) {
  const [expanded, setExpanded] = useState(false)
  const metadataId = `evidence-metadata-${evidence.id}`

  return (
    <figure className="evidence-quote">
      <blockquote>
        <p>“{evidence.quote}”</p>
      </blockquote>
      <figcaption>
        <button
          type="button"
          className="evidence-quote__toggle"
          aria-expanded={expanded}
          aria-controls={metadataId}
          onClick={() => setExpanded((value) => !value)}
        >
          {expanded ? '收合來源' : '查看來源'}
          <span aria-hidden="true">{expanded ? '−' : '+'}</span>
        </button>
        <div
          id={metadataId}
          className="evidence-quote__metadata"
          data-expanded={expanded || undefined}
        >
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
              <dt>分析批次</dt>
              <dd>{evidence.batchId}</dd>
            </div>
          </dl>
        </div>
      </figcaption>
    </figure>
  )
}
