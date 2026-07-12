import { useEffect, useRef, useState } from 'react'
import { getPersonas, precheckPhoto } from '../api.js'

export default function UploadScreen({ onStart, error }) {
  const [personas, setPersonas] = useState([])
  const [dragOver, setDragOver] = useState(false)
  const [busy, setBusy] = useState(false)
  // Preview step: file chosen but not yet confirmed.
  const [pending, setPending] = useState(null) // { file, url, issues, checking }
  const inputRef = useRef(null)
  const cameraRef = useRef(null)

  useEffect(() => {
    getPersonas().then((d) => setPersonas(d.personas))
    return () => pending && URL.revokeObjectURL(pending.url)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const choose = async (file) => {
    if (!file || busy) return
    const url = URL.createObjectURL(file)
    setPending({ file, url, issues: [], checking: true })
    const { issues } = await precheckPhoto(file)
    setPending((p) => (p && p.url === url ? { ...p, issues, checking: false } : p))
  }

  const confirm = async () => {
    if (!pending || busy) return
    setBusy(true)
    await onStart({ file: pending.file })
    setBusy(false)
  }

  const discard = () => {
    if (pending) URL.revokeObjectURL(pending.url)
    setPending(null)
    if (inputRef.current) inputRef.current.value = ''
    if (cameraRef.current) cameraRef.current.value = ''
  }

  const blocked = pending?.issues.some((i) => i.level === 'block')

  return (
    <main className="upload">
      <p className="eyebrow">a draping session, from one selfie</p>
      <h1 className="upload-title">
        Which colors were
        <br />
        <em>made for you?</em>
      </h1>
      <p className="upload-lede">
        Colorists answer this by holding fabric drapes to your face — a $200 studio
        appointment. DRAPE runs the same session on your own photo: eight AI try-on
        renders, measured in Lab color space, narrowed round by round.
      </p>

      {!pending ? (
        <>
          <button
            type="button"
            className={`mirror ${dragOver ? 'mirror-over' : ''}`}
            onClick={() => inputRef.current?.click()}
            onDragOver={(e) => {
              e.preventDefault()
              setDragOver(true)
            }}
            onDragLeave={() => setDragOver(false)}
            onDrop={(e) => {
              e.preventDefault()
              setDragOver(false)
              choose(e.dataTransfer.files[0])
            }}
          >
            <span className="mirror-inner">
              <span className="mirror-plus">+</span>
              Step to the mirror
              <span className="mirror-hint">drop a selfie or click to choose</span>
            </span>
          </button>
          <div className="upload-alt">
            <button className="btn-ghost" onClick={() => cameraRef.current?.click()}>
              Use my camera instead
            </button>
          </div>
        </>
      ) : (
        <div className="mirror mirror-preview" aria-live="polite">
          <img src={pending.url} alt="Your selfie, ready for the session" />
          <span className="mirror-guide" aria-hidden="true" />
        </div>
      )}

      <input
        ref={inputRef}
        type="file"
        accept="image/jpeg,image/png"
        hidden
        onChange={(e) => choose(e.target.files[0])}
      />
      <input
        ref={cameraRef}
        type="file"
        accept="image/*"
        capture="user"
        hidden
        onChange={(e) => choose(e.target.files[0])}
      />

      {!pending && (
        <p className="mirror-specs">
          Face forward, good light, face filling most of the frame — chest up.
        </p>
      )}

      {pending && (
        <div className="precheck">
          {pending.checking && <p className="precheck-checking">Checking the photo…</p>}
          {!pending.checking && pending.issues.length === 0 && (
            <p className="precheck-ok">Good light, good size — ready to drape.</p>
          )}
          {pending.issues.map((i) => (
            <p key={i.code} className={`precheck-issue precheck-${i.level}`} role="alert">
              {i.message}
            </p>
          ))}
          <div className="precheck-actions">
            {!blocked && (
              <button className="btn-primary" onClick={confirm} disabled={busy || pending.checking}>
                {busy ? 'Starting your session…' : 'Begin draping'}
              </button>
            )}
            <button className="btn-ghost" onClick={discard} disabled={busy}>
              Choose another photo
            </button>
          </div>
        </div>
      )}

      {error && <p className="error" role="alert">{error}</p>}

      {personas.length > 0 && !pending && (
        <div className="personas">
          <span className="personas-label">No selfie handy? Drape a demo persona:</span>
          <div className="persona-chips">
            {personas.map((p) => (
              <button key={p.name} className="persona-chip" onClick={() => onStart({ persona: p.name })}>
                <img src={p.image_url} alt="" />
                {p.name}
              </button>
            ))}
          </div>
        </div>
      )}
    </main>
  )
}
