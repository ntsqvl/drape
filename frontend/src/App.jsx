import { useCallback, useEffect, useRef, useState } from 'react'
import { createSession, getMode, getSession } from './api.js'
import UploadScreen from './screens/Upload.jsx'
import SessionScreen from './screens/Session.jsx'
import VerdictScreen from './screens/Verdict.jsx'
import ShopScreen from './screens/Shop.jsx'

const POLL_MS = 1200

export default function App() {
  const [screen, setScreen] = useState('upload') // upload | session | verdict | shop
  const [sid, setSid] = useState(null)
  const [trace, setTrace] = useState([])
  const [verdict, setVerdict] = useState(null)
  const [error, setError] = useState(null)
  const [mode, setMode] = useState(null)
  const pollRef = useRef(null)

  // After the verdict, the interface dresses itself in your best color.
  useEffect(() => {
    const accent = verdict?.palette?.[0]?.hex
    if (accent) document.documentElement.style.setProperty('--accent', accent)
  }, [verdict])

  const stopPolling = () => {
    if (pollRef.current) clearInterval(pollRef.current)
    pollRef.current = null
  }

  const attachPolling = useCallback((id) => {
    pollRef.current = setInterval(async () => {
      try {
        const s = await getSession(id)
        setTrace(s.trace)
        if (s.status === 'done') {
          stopPolling()
          setVerdict(s.verdict)
          setTimeout(() => setScreen('verdict'), 1400) // let the last trace line land
        } else if (s.status === 'error') {
          stopPolling()
          setError(s.error)
          setScreen('upload')
          window.location.hash = ''
        }
      } catch {
        /* transient poll failure: keep polling */
      }
    }, POLL_MS)
  }, [])

  const start = useCallback(async ({ file, persona }) => {
    setError(null)
    setTrace([])
    setVerdict(null)
    try {
      const id = await createSession({ file, persona })
      setSid(id)
      setScreen('session')
      window.location.hash = id // refresh-safe: the session survives a reload
      attachPolling(id)
    } catch (e) {
      setError(e.message)
    }
  }, [attachPolling])

  // Resume a session from the URL hash (reload mid-session, or a kept link).
  useEffect(() => {
    getMode().then(setMode)
    const id = window.location.hash.slice(1)
    if (!id) return
    getSession(id)
      .then((s) => {
        setSid(id)
        setTrace(s.trace)
        if (s.status === 'done') {
          setVerdict(s.verdict)
          setScreen('verdict')
        } else if (s.status === 'running') {
          setScreen('session')
          attachPolling(id)
        }
      })
      .catch(() => {
        window.location.hash = ''
      })
    return stopPolling
  }, [attachPolling])

  const reset = () => {
    stopPolling()
    document.documentElement.style.removeProperty('--accent')
    window.location.hash = ''
    setScreen('upload')
    setSid(null)
    setTrace([])
    setVerdict(null)
    setError(null)
  }

  return (
    <div className="app">
      <header className="masthead">
        <button className="wordmark" onClick={reset}>DRAPE</button>
        <span className="masthead-note">a personal color draping studio</span>
        {mode !== null && (
          <span className="mode-chip">
            {mode.mock
              ? 'demo mode · no API units used'
              : `live${mode.units != null ? ` · ${Math.round(mode.units)} units` : ''}`}
          </span>
        )}
      </header>
      {screen === 'upload' && <UploadScreen onStart={start} error={error} />}
      {screen === 'session' && <SessionScreen trace={trace} />}
      {screen === 'verdict' && (
        <VerdictScreen verdict={verdict} sid={sid} onShop={() => setScreen('shop')} onRestart={reset} />
      )}
      {screen === 'shop' && <ShopScreen sid={sid} verdict={verdict} onBack={() => setScreen('verdict')} />}
    </div>
  )
}
