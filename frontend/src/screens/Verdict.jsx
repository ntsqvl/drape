import { useRef, useState } from 'react'
import { drapeSwatch, getCard } from '../api.js'

export default function VerdictScreen({ verdict, sid, onShop, onRestart }) {
  const [openSwatch, setOpenSwatch] = useState(0)
  const [cardBusy, setCardBusy] = useState(false)
  // The left panel is a live mirror: it starts on the verdict's best drape
  // and re-drapes when a palette swatch is clicked.
  const [mirror, setMirror] = useState({
    name: verdict.best.name,
    render_url: verdict.best.render_url,
    measured_hex: verdict.best.measured_hex,
    score: verdict.best.score.score,
    loading: false,
  })
  const requestSeq = useRef(0)
  const v = verdict

  const tryColor = async (i) => {
    setOpenSwatch(i)
    const color = v.palette[i]
    if (color.name === mirror.name && !mirror.loading) return
    const seq = ++requestSeq.current
    setMirror((m) => ({ ...m, loading: true, pending: color.name }))
    try {
      const d = await drapeSwatch(sid, color.name)
      if (seq !== requestSeq.current) return // a newer click superseded this one
      setMirror({
        name: d.name,
        render_url: d.render_url,
        measured_hex: d.measured_hex,
        score: d.score,
        loading: false,
      })
    } catch {
      if (seq === requestSeq.current) setMirror((m) => ({ ...m, loading: false }))
    }
  }

  return (
    <main className="verdict">
      <p className="eyebrow">the verdict · {v.confidence} confidence</p>
      <h1 className="verdict-season"><em>{v.season_name}</em></h1>
      <p className="verdict-tagline">{v.tagline}</p>
      {v.confidence_note && <p className="verdict-note">{v.confidence_note}</p>}

      <section className="reveal" aria-label="Your colors on your body">
        <figure className={`reveal-panel reveal-best ${mirror.loading ? 'reveal-loading' : ''}`}>
          <img key={mirror.render_url} src={mirror.render_url} alt={`You in ${mirror.name}`} />
          {mirror.loading && (
            <span className="reveal-spinner" role="status">
              <span className="spinner" aria-hidden="true" />
              draping {mirror.pending}…
            </span>
          )}
          <figcaption>
            <span className="swatch" style={{ background: mirror.measured_hex }} />
            <strong>{mirror.name}</strong> — yours · drape score {mirror.score}
          </figcaption>
        </figure>
        <figure className="reveal-panel reveal-worst">
          <img src={v.worst.render_url} alt={`You in ${v.worst.name}`} />
          <figcaption>
            <span className="swatch" style={{ background: v.worst.measured_hex }} />
            <strong>{v.worst.name}</strong> — not yours · drape score {v.worst.score.score}
          </figcaption>
        </figure>
      </section>

      <section className="fan-section">
        <h2 className="section-title">Your palette, ranked by fit</h2>
        <p className="fan-caption">
          Click any swatch to see it draped on you, live. Palette fit is scored from your
          measured coloring; drape scores come from the try-on renders themselves.
        </p>
        <div className="fan" role="list">
          {v.palette.map((p, i) => (
            <button
              key={p.hex}
              role="listitem"
              className={`fan-card ${openSwatch === i ? 'fan-open' : ''}`}
              style={{ '--swatch': p.hex, '--i': i, '--n': v.palette.length }}
              onClick={() => tryColor(i)}
              aria-label={`Drape ${p.name}, fit ${p.score}`}
            >
              <span className="fan-color" />
              <span className="fan-meta">
                <span className="fan-name">{p.name}</span>
                <span className="fan-score">{p.score}</span>
              </span>
            </button>
          ))}
        </div>
        <p className="fan-reason">
          <span className="swatch" style={{ background: v.palette[openSwatch].hex }} />
          <strong>{v.palette[openSwatch].name}</strong> · {v.palette[openSwatch].reasons.join('; ')}
        </p>
      </section>

      <section className="verdict-notes">
        <div>
          <h3>How the session read you</h3>
          <dl className="axes">
            <div><dt>temperature</dt><dd>{v.temperature}</dd></div>
            <div><dt>depth</dt><dd>{v.profile_axes.depth > 0.5 ? 'deep' : 'light'} ({v.profile_axes.depth})</dd></div>
            <div><dt>clarity</dt><dd>{v.profile_axes.clarity > 0.5 ? 'clear' : 'muted'} ({v.profile_axes.clarity})</dd></div>
          </dl>
        </div>
        <div>
          <h3>Today's skin, factored in</h3>
          <p>
            Redness {Math.round(v.skin_state.redness_severity)}/100 · dullness{' '}
            {Math.round(v.skin_state.dullness)}/100. Saturated reds were{' '}
            {v.skin_state.redness_severity > 40 ? 'demoted accordingly' : 'not a concern today'}.
          </p>
        </div>
        <div>
          <h3>The receipt</h3>
          <p>
            {v.renders_used} try-on renders instead of 16 — the agent narrowed your season in
            three rounds. A heuristic reading of the 12-season method, not a diagnosis.
          </p>
        </div>
      </section>

      <div className="verdict-actions">
        <button className="btn-primary" onClick={onShop}>Shop your colors</button>
        <button
          className="btn-ghost"
          disabled={cardBusy}
          onClick={async () => {
            setCardBusy(true)
            try {
              const { card_url } = await getCard(sid)
              const a = document.createElement('a')
              a.href = card_url
              a.download = `drape-${v.season_key}.png`
              a.click()
            } catch { /* non-fatal */ }
            setCardBusy(false)
          }}
        >
          {cardBusy ? 'Building your card…' : 'Save your card'}
        </button>
        <button className="btn-ghost" onClick={onRestart}>Drape someone else</button>
      </div>
    </main>
  )
}
