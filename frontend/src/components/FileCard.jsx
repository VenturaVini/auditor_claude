// Cards de arquivo no estilo Claude.ai/ChatGPT — usados nos previews do input,
// nos anexos das mensagens e nos artefatos para download.

const EXT_STYLE = {
  pdf: { icon: '📄', color: '#e5635a', label: 'PDF' },
  docx: { icon: '📝', color: '#4a8fe7', label: 'DOCX' },
  doc: { icon: '📝', color: '#4a8fe7', label: 'DOC' },
  xlsx: { icon: '📊', color: '#3ecf8e', label: 'XLSX' },
  csv: { icon: '📊', color: '#3ecf8e', label: 'CSV' },
  txt: { icon: '📃', color: '#b0b0b0', label: 'TXT' },
  md: { icon: '📃', color: '#b48ee0', label: 'MD' },
  png: { icon: '🖼️', color: '#e0a84a', label: 'PNG' },
  jpg: { icon: '🖼️', color: '#e0a84a', label: 'JPG' },
  jpeg: { icon: '🖼️', color: '#e0a84a', label: 'JPEG' },
  gif: { icon: '🖼️', color: '#e0a84a', label: 'GIF' },
  webp: { icon: '🖼️', color: '#e0a84a', label: 'WEBP' },
}

export function formatSize(bytes) {
  if (bytes == null) return null
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`
}

/** Card de documento (ou artefato baixável, quando `href` é passado). */
export default function FileCard({ name, size, href, onRemove }) {
  const ext = (name.split('.').pop() || '').toLowerCase()
  const s = EXT_STYLE[ext] || { icon: '📎', color: '#9a9a9a', label: ext.toUpperCase() || 'ARQUIVO' }
  const meta = [s.label, formatSize(size)].filter(Boolean).join(' · ')

  const inner = (
    <>
      <div className="file-card-icon" style={{ background: `${s.color}22`, color: s.color }}>
        {s.icon}
      </div>
      <div className="file-card-info">
        <div className="file-card-name" title={name}>{name}</div>
        <div className="file-card-meta">{href ? `${meta} · baixar` : meta}</div>
      </div>
      {href && <div className="file-card-dl">⬇</div>}
      {onRemove && (
        <button
          className="file-card-remove"
          title="Remover"
          onClick={(e) => {
            e.preventDefault()
            onRemove()
          }}
        >
          ✕
        </button>
      )}
    </>
  )

  return href ? (
    <a className="file-card downloadable" href={href} download={name}>{inner}</a>
  ) : (
    <div className="file-card">{inner}</div>
  )
}

/** Thumbnail de imagem com nome, estilo Claude.ai. */
export function ImageCard({ src, name, onRemove, size = 'sm' }) {
  return (
    <div className={`image-card ${size}`}>
      <img src={src} alt={name} title={name} />
      {onRemove && (
        <button className="image-card-remove" title="Remover" onClick={onRemove}>
          ✕
        </button>
      )}
    </div>
  )
}
