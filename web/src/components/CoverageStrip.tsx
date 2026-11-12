export function CoverageStrip({
  covered,
  total,
}: {
  covered: number
  total: number
}) {
  return (
    <div
      className="coverage-strip"
      role="img"
      aria-label={`主題出現在 ${total} 個分析批次中的 ${covered} 個，不代表評論發生率`}
    >
      {Array.from({ length: total }, (_, index) => (
        <span
          key={index}
          className="coverage-strip__cell"
          data-covered={index < covered || undefined}
          aria-hidden="true"
        />
      ))}
    </div>
  )
}
