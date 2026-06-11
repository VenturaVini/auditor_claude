import { useEffect, useRef, useState } from 'react'
import { downloadResponse } from '../services/api.js'

export default function DownloadMenu({ content }) {
  const [open, setOpen] = useState(false)
  const [busy, setBusy] = useState(false)
  const ref = useRef(null)

  useEffect(() => {
    const close = (e) => {
      if (ref.current && !ref.current.contains(e.target)) setOpen(false)
    }
    document.addEventListener('mousedown', close)
    return () => document.removeEventListener('mousedown', close)
  }, [])

  const download = async (format) => {
    setBusy(true)
    setOpen(false)
    try {
      await downloadResponse(format, content)
    } catch (e) {
      alert(e.message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div ref={ref} style={{ position: 'relative' }}>
      <button className="action-btn" disabled={busy} onClick={() => setOpen(!open)}>
        {busy ? 'Gerando…' : 'Download ▾'}
      </button>
      {open && (
        <div className="download-menu">
          <button onClick={() => download('txt')}>TXT</button>
          <button onClick={() => download('md')}>MD</button>
          <button onClick={() => download('pdf')}>PDF</button>
        </div>
      )}
    </div>
  )
}
