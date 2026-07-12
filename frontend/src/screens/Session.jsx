const ROUND_LABELS = {
  analyze: 'Reading you',
  render: 'Draping',
  round1: 'Round 1 · Temperature',
  round2: 'Round 2 · Depth',
  round3: 'Round 3 · Season',
  reveal: 'The reveal',
}

export default function SessionScreen({ trace }) {
  const renders = trace.filter((e) => e.render_url)
  const current = renders[renders.length - 1]

  return (
    <main className="session">
      <div className="session-mirror">
        {current ? (
          <img key={current.render_url} src={current.render_url} alt={`You, draped in ${current.name}`} />
        ) : (
          <div className="session-mirror-empty">
            <span className="spinner" aria-hidden="true" />
            reading your coloring…
          </div>
        )}
        {current && (
          <figcaption className="session-mirror-caption">
            <span className="swatch" style={{ background: current.measured }} />
            {current.name} · scored {current.score}
          </figcaption>
        )}
      </div>

      <ol className="trace" aria-live="polite">
        {trace.map((e, i) => (
          <li key={i} className={`trace-line trace-${e.round}`}>
            <span className="trace-tag">{ROUND_LABELS[e.round] || e.round}</span>
            <span className="trace-msg">
              {e.requested && <span className="swatch" style={{ background: e.requested }} />}
              {e.message}
            </span>
          </li>
        ))}
        <li className="trace-line trace-pending">
          <span className="spinner" aria-hidden="true" />
        </li>
      </ol>
    </main>
  )
}
