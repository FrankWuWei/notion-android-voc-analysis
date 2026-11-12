export type SentimentBucket = 'positive' | 'negative' | 'mixed_or_uncertain'

export interface EvidenceRecord {
  id: string
  quote: string
  reviewId: string
  reviewCreatedAt: string
  score: number
  appVersion: string | null
  batchId: string
  sentimentBucket: SentimentBucket
}

export interface ThemeRecord {
  id: string
  nameZh: string
  descriptionZh: string
  batchCoverage: number
  batchCoverageTotal: number
  evidenceCount: number
  evidence: EvidenceRecord[]
}

export interface PositiveValueRecord {
  id: string
  nameZh: string
  descriptionZh: string
  evidenceCount: number
  evidence: EvidenceRecord
}

export interface MonitoringEvidenceRecord {
  quote: string
  sourceReview: string
  reviewId: string
  reviewCreatedAt: string
  score: number
  appVersion: string | null
  period: 'pre' | 'post'
  matchedPhrases: string[]
}

export interface MonitoringWindowRecord {
  eligibleReviews: number
  matchedReviews: number
  matchRate: number
}

export interface PortfolioSnapshot {
  schemaVersion: number
  sourceDigestSha256: string
  scope: {
    platform: string
    store: string
    market: string
    language: string
    periodStart: string
    periodEnd: string
    rawReviews: number
    effectiveReviews: number
  }
  pipeline: {
    sentiment: {
      positive: number
      negative: number
      uncertain: number
    }
    deepAnalysisReviews: number
    llmBatches: number
    validatedBatchThemes: number
    sourceVerbatimEvidence: number
    uniqueEvidenceReviews: number
    canonicalThemes: number
    painThemes: number
    positiveValues: number
    validatedBatches: number
    expectedBatches: number
    sourceValidationErrors: number
  }
  qualityAudit: {
    reviewedNonVerbatimQuotes: number
    replacedWithSupportingVerbatimQuote: number
    droppedAsUnsupported: number
    correctedScores: number
  }
  qualityCase: {
    batchId: string
    themeId: string
    modelQuote: string
    sourceReview: string
    reviewId: string
    reviewCreatedAt: string
    score: number
    appVersion: string | null
    decision: 'drop'
    reasonZh: string
  }
  mainThemes: ThemeRecord[]
  positiveValues: PositiveValueRecord[]
  extendedValidation: {
    windowDays: number
    candidateCases: number
    ruleMatchedReviews: number
    scope: string
    example: {
      candidateId: string
      themeId: string
      themeNameZh: string
      releaseDate: string
      releaseTitle: string
      releaseScope: string
      windowDays: number
      before: MonitoringWindowRecord
      after: MonitoringWindowRecord
      rateChangePercentagePoints: number
      observationStatus: string
      rulePhrases: string[]
      evidence: MonitoringEvidenceRecord
    }
  }
  engineering: {
    analysisTestCount: number
    configVersion: number
    canonicalTaxonomyVersion: number
    quoteReviewVersion: number
  }
  countingBoundary: string
}
