import { useRef, useState } from 'react'
import { uploadFile } from '../services/api.js'
import FileCard, { ImageCard } from './FileCard.jsx'

const ACCEPT = '.png,.jpg,.jpeg,.gif,.webp,.pdf,.txt,.md,.docx,.xlsx,.csv,.json'

/** Lista de previews dos arquivos anexados (fica dentro da caixa de input). */
export default function FileUpload({ files, setFiles }) {
  if (files.length === 0) return null
  return (
    <div className="file-previews">
      {files.map((f) =>
        f.type === 'image' ? (
          <ImageCard
            key={f.file_id}
            src={f.preview}
            name={f.name}
            onRemove={() => setFiles(files.filter((x) => x.file_id !== f.file_id))}
          />
        ) : (
          <FileCard
            key={f.file_id}
            name={f.name}
            onRemove={() => setFiles(files.filter((x) => x.file_id !== f.file_id))}
          />
        )
      )}
    </div>
  )
}

/** Botão de clipe que dispara o upload. */
FileUpload.Button = function FileUploadButton({ files, setFiles, disabled }) {
  const inputRef = useRef(null)
  const [uploading, setUploading] = useState(false)

  const handleChange = async (e) => {
    const selected = Array.from(e.target.files || [])
    e.target.value = ''
    if (selected.length === 0) return
    setUploading(true)
    for (const file of selected) {
      try {
        const meta = await uploadFile(file)
        setFiles((prev) => [...prev, meta])
      } catch (err) {
        alert(err.message)
      }
    }
    setUploading(false)
  }

  return (
    <>
      <input
        ref={inputRef}
        type="file"
        accept={ACCEPT}
        multiple
        hidden
        onChange={handleChange}
      />
      <button
        className="icon-btn"
        title="Anexar arquivos (múltiplos)"
        disabled={disabled || uploading}
        onClick={() => inputRef.current?.click()}
      >
        {uploading ? '…' : '📎'}
      </button>
    </>
  )
}
