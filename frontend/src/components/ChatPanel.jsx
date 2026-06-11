import { useEffect, useRef, useState } from 'react'
import MessageBubble from './MessageBubble.jsx'
import FileUpload from './FileUpload.jsx'
import ModelSelect from './ModelSelect.jsx'

export default function ChatPanel({
  className = '',
  messages,
  streaming,
  onSend,
  model,
  modelOptions = [],
  onModelChange,
  rounds = 2,
  onRoundsChange,
  booster = false,
  onBoosterChange,
}) {
  const [text, setText] = useState('')
  const [files, setFiles] = useState([]) // [{file_id, name, type, preview}]
  const bottomRef = useRef(null)
  const textareaRef = useRef(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const submit = () => {
    if (streaming || !text.trim()) return
    onSend(text, files)
    setText('')
    setFiles([])
    if (textareaRef.current) textareaRef.current.style.height = 'auto'
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      submit()
    }
  }

  const autoGrow = (e) => {
    e.target.style.height = 'auto'
    e.target.style.height = Math.min(e.target.scrollHeight, 180) + 'px'
  }

  return (
    <section className={`chat-panel ${className}`}>
      <div className="chat-header">
        <span className="chat-header-title">Claude</span>
        <ModelSelect
          value={model}
          options={modelOptions}
          disabled={streaming}
          onChange={onModelChange}
          title="Modelo da resposta principal (principais em ordem de capacidade/custo)"
        />
        <select
          className="model-select"
          value={rounds}
          disabled={streaming}
          onChange={(e) => onRoundsChange(parseInt(e.target.value, 10))}
          title="Rodadas do debate: em 4x+ a crítica do GPT volta ao Claude, que refina a resposta, e o GPT julga de novo. Mais rodadas = mais tokens/custo. Para antecipado se o GPT aprovar."
        >
          {[2, 4, 6, 8, 10].map((n) => (
            <option key={n} value={n}>
              {n === 2 ? '2x rodadas (Padrão)' : `${n}x rodadas`}
            </option>
          ))}
        </select>
        <button
          className={`booster-toggle ${booster ? 'on' : ''}`}
          disabled={streaming}
          onClick={() => onBoosterChange(!booster)}
          title="Booster: ao final do debate, os MELHORES modelos de cada provedor (ex.: claude-opus-4-8 e gpt-5.x) dão uma opinião final independente sobre a resposta. Custo extra de 2 chamadas."
        >
          ⭐ Booster {booster ? 'ON' : 'OFF'}
        </button>
      </div>
      <div className="messages">
        {messages.length === 0 ? (
          <div className="empty-state">
            <div className="logo">✳️</div>
            <div>Converse com o Claude — o GPT audita cada resposta</div>
          </div>
        ) : (
          messages.map((m, i) => (
            <MessageBubble
              key={i}
              message={m}
              isStreaming={streaming && i === messages.length - 1 && m.role === 'assistant'}
            />
          ))
        )}
        <div ref={bottomRef} />
      </div>

      <div className="input-area">
        <div className="input-box">
          <FileUpload files={files} setFiles={setFiles} disabled={streaming} />
          <div className="input-row">
            <FileUpload.Button files={files} setFiles={setFiles} disabled={streaming} />
            <textarea
              ref={textareaRef}
              rows={1}
              placeholder="Envie uma mensagem para o Claude..."
              value={text}
              onChange={(e) => setText(e.target.value)}
              onInput={autoGrow}
              onKeyDown={handleKeyDown}
              disabled={streaming}
            />
            <button
              className="icon-btn send-btn"
              onClick={submit}
              disabled={streaming || !text.trim()}
              title="Enviar"
            >
              ↑
            </button>
          </div>
        </div>
        <div className="input-hint">
          Enter envia · Shift+Enter quebra linha · anexos múltiplos: imagens, PDF, TXT, MD, DOCX, XLSX · cite arquivos por @nome
        </div>
      </div>
    </section>
  )
}
