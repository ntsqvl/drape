export async function createSession({ file, persona }) {
  const form = new FormData()
  if (file) form.append('file', file)
  if (persona) form.append('persona', persona)
  const res = await fetch('/api/session', { method: 'POST', body: form })
  if (!res.ok) throw new Error((await res.json()).detail || 'Could not start the session.')
  return (await res.json()).session_id
}

export async function getSession(sid) {
  const res = await fetch(`/api/session/${sid}`)
  if (!res.ok) throw new Error('Session not found.')
  return res.json()
}

export async function getCatalog(sid) {
  const res = await fetch(`/api/catalog/${sid}`)
  if (!res.ok) throw new Error('Catalog unavailable.')
  return res.json()
}

export async function getPersonas() {
  const res = await fetch('/api/personas')
  if (!res.ok) return { personas: [] }
  return res.json()
}

export async function precheckPhoto(file) {
  const form = new FormData()
  form.append('file', file)
  const res = await fetch('/api/precheck', { method: 'POST', body: form })
  if (!res.ok) return { issues: [] } // precheck failing must never block the flow
  return res.json()
}

export async function drapeSwatch(sid, name) {
  const res = await fetch(`/api/session/${sid}/drape`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name }),
  })
  if (!res.ok) throw new Error((await res.json()).detail || 'Could not drape that color.')
  return res.json()
}

export async function checkGarment(sid, file) {
  const form = new FormData()
  form.append('file', file)
  const res = await fetch(`/api/session/${sid}/check-garment`, { method: 'POST', body: form })
  if (!res.ok) throw new Error((await res.json()).detail || 'Could not read that photo.')
  return res.json()
}

export async function tryGarment(sid, garmentId) {
  const res = await fetch(`/api/session/${sid}/try-garment`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ garment_id: garmentId }),
  })
  if (!res.ok) throw new Error((await res.json()).detail || 'Try-on failed.')
  return res.json()
}

export async function getCard(sid) {
  const res = await fetch(`/api/session/${sid}/card`)
  if (!res.ok) throw new Error('Could not build your card.')
  return res.json()
}

export async function getMode() {
  const res = await fetch('/api/mode')
  if (!res.ok) return { mock: null }
  return res.json()
}
