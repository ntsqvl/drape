import { useEffect, useRef, useState } from 'react'
import { checkGarment, getCatalog, tryGarment } from '../api.js'

function GarmentCheck({ sid }) {
  const [check, setCheck] = useState(null) // {status, name, hex, match, reasons, garment_id, render_url, render_score}
  const inputRef = useRef(null)

  const submit = async (file) => {
    if (!file) return
    setCheck({ status: 'checking', name: file.name })
    try {
      const r = await checkGarment(sid, file)
      setCheck({ status: 'checked', name: file.name, ...r })
    } catch (e) {
      setCheck({ status: 'error', message: e.message })
    }
  }

  const tryOn = async () => {
    setCheck((c) => ({ ...c, status: 'rendering' }))
    try {
      const r = await tryGarment(sid, check.garment_id)
      setCheck((c) => ({ ...c, status: 'rendered', render_url: r.render_url, render_score: r.score }))
    } catch (e) {
      setCheck((c) => ({ ...c, status: 'checked', message: e.message }))
    }
  }

  return (
    <section className="garment-check">
      <h2 className="section-title">Eyeing something in another shop?</h2>
      <p className="garment-check-lede">
        Drop its product photo — we'll score the color against your palette before you buy.
        Checking is free; seeing it on you uses two API units.
      </p>
      {!check || check.status === 'error' ? (
        <>
          <button className="garment-drop" onClick={() => inputRef.current?.click()}
            onDragOver={(e) => e.preventDefault()}
            onDrop={(e) => { e.preventDefault(); submit(e.dataTransfer.files[0]) }}>
            + drop a product photo
          </button>
          {check?.status === 'error' && <p className="error" role="alert">{check.message}</p>}
        </>
      ) : (
        <div className="garment-result">
          <div className="garment-result-row">
            <span className="swatch swatch-lg" style={{ background: check.hex || check.measured_hex }} />
            <div className="garment-result-meta">
              <span className="rack-name">{check.name}</span>
              {check.status === 'checking' ? (
                <span className="shop-loading">Reading the fabric color…</span>
              ) : (
                <>
                  <span className={`match-badge ${check.match >= 60 ? 'match-good' : check.match >= 45 ? 'match-mid' : 'match-poor'}`}>
                    {Math.round(check.match)}% match
                  </span>
                  <span className="rack-reason">{check.reasons?.join('; ')}</span>
                </>
              )}
            </div>
            {check.status === 'checked' && (
              <div className="garment-result-actions">
                <button className="btn-primary" onClick={tryOn}>See it on you</button>
                <button className="btn-ghost" onClick={() => setCheck(null)}>Check another</button>
              </div>
            )}
            {check.status === 'rendering' && <span className="shop-loading"><span className="spinner" /> draping it on you…</span>}
          </div>
          {check.message && check.status === 'checked' && <p className="error" role="alert">{check.message}</p>}
          {check.status === 'rendered' && (
            <figure className="garment-render">
              <img src={check.render_url} alt="You, wearing the checked garment" />
              <figcaption>on you · drape score {check.render_score}</figcaption>
              <button className="btn-ghost" onClick={() => setCheck(null)}>Check another</button>
            </figure>
          )}
        </div>
      )}
      <input ref={inputRef} type="file" accept="image/jpeg,image/png" hidden
        onChange={(e) => submit(e.target.files[0])} />
    </section>
  )
}

export default function ShopScreen({ sid, verdict, onBack }) {
  const [catalog, setCatalog] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    getCatalog(sid).then(setCatalog).catch((e) => setError(e.message))
  }, [sid])

  return (
    <main className="shop">
      <button className="btn-ghost shop-back" onClick={onBack}>← Back to your verdict</button>
      <p className="eyebrow">the rack, re-sorted for {verdict.season_name}</p>
      <h1 className="shop-title">Every garment, scored against <em>your</em> palette</h1>

      <GarmentCheck sid={sid} />

      {error && <p className="error" role="alert">{error}</p>}
      {!catalog && !error && <p className="shop-loading">Scoring the rack…</p>}

      {catalog && (
        <div className="rack" role="list">
          {catalog.items.map((item) => (
            <article key={item.id} className="rack-card" role="listitem">
              <div className="rack-image">
                <img src={item.image_url} alt={item.name} loading="lazy" />
                <span
                  className={`match-badge ${item.match >= 60 ? 'match-good' : item.match >= 45 ? 'match-mid' : 'match-poor'}`}
                >
                  {Math.round(item.match)}% match
                </span>
              </div>
              <div className="rack-meta">
                <span className="rack-name">{item.name}</span>
                <span className="rack-price">${item.price}</span>
              </div>
              <p className="rack-reason">{item.reason}</p>
            </article>
          ))}
        </div>
      )}
    </main>
  )
}
