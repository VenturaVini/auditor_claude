import { useState } from 'react'

export default function Sidebar({ conversations, activeId, onNew, onOpen, onDelete }) {
  const [confirmingId, setConfirmingId] = useState(null)

  return (
    <aside className="sidebar">
      <h1>Claude + Auditor GPT</h1>
      <button className="new-chat-btn" onClick={onNew}>
        ＋ Nova conversa
      </button>
      <div className="conv-list">
        {conversations.map((c) =>
          confirmingId === c.id ? (
            <div key={c.id} className="conv-item confirming">
              <span className="conv-title">Apagar esta conversa?</span>
              <button
                className="confirm-yes"
                onClick={(e) => {
                  e.stopPropagation()
                  setConfirmingId(null)
                  onDelete(c.id)
                }}
              >
                Sim
              </button>
              <button
                className="confirm-no"
                onClick={(e) => {
                  e.stopPropagation()
                  setConfirmingId(null)
                }}
              >
                Não
              </button>
            </div>
          ) : (
            <div
              key={c.id}
              className={`conv-item ${c.id === activeId ? 'active' : ''}`}
              onClick={() => onOpen(c.id)}
            >
              <span className="conv-title">{c.title}</span>
              <button
                className="conv-delete"
                title="Apagar conversa"
                onClick={(e) => {
                  e.stopPropagation()
                  setConfirmingId(c.id)
                }}
              >
                ✕
              </button>
            </div>
          )
        )}
      </div>
    </aside>
  )
}
