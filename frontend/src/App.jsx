import { useCallback, useEffect, useState } from 'react'
import ChatPanel from './components/ChatPanel.jsx'
import AuditorPanel from './components/AuditorPanel.jsx'
import Sidebar from './components/Sidebar.jsx'
import {
  streamChat,
  listConversations,
  getConversation,
  deleteConversation,
  fetchModels,
} from './services/api.js'

export default function App() {
  // messages: [{role, content, attachments?}] — attachments só para exibição
  const [messages, setMessages] = useState([])
  // audits: um item por resposta do assistant, na mesma ordem
  const [audits, setAudits] = useState([])
  const [conversationId, setConversationId] = useState(null)
  const [conversations, setConversations] = useState([])
  const [streaming, setStreaming] = useState(false)
  const [mobileTab, setMobileTab] = useState('chat') // 'chat' | 'auditor'
  // modelos disponíveis (do backend) e selecionados (persistidos no localStorage)
  const [modelOptions, setModelOptions] = useState({ main: [], auditor: [] })
  const [mainModel, setMainModel] = useState(() => localStorage.getItem('mainModel') || '')
  const [auditorModel, setAuditorModel] = useState(() => localStorage.getItem('auditorModel') || '')
  const [rounds, setRounds] = useState(() => parseInt(localStorage.getItem('rounds') || '2', 10))
  const [booster, setBooster] = useState(() => localStorage.getItem('booster') === 'true')

  const refreshConversations = useCallback(async () => {
    setConversations(await listConversations().catch(() => []))
  }, [])

  useEffect(() => {
    refreshConversations()
    fetchModels().then((m) => {
      if (!m) return
      setModelOptions({ main: m.main, auditor: m.auditor })
      setMainModel((cur) => (m.main.includes(cur) ? cur : m.default_main))
      setAuditorModel((cur) => (m.auditor.includes(cur) ? cur : m.default_auditor))
    })
  }, [refreshConversations])

  useEffect(() => {
    if (mainModel) localStorage.setItem('mainModel', mainModel)
    if (auditorModel) localStorage.setItem('auditorModel', auditorModel)
    localStorage.setItem('rounds', String(rounds))
    localStorage.setItem('booster', String(booster))
  }, [mainModel, auditorModel, rounds, booster])

  const newConversation = () => {
    setMessages([])
    setAudits([])
    setConversationId(null)
    setMobileTab('chat')
  }

  const openConversation = async (id) => {
    try {
      const conv = await getConversation(id)
      setMessages(conv.messages)
      setAudits(conv.audits || [])
      setConversationId(conv.id)
      setMobileTab('chat')
    } catch {
      refreshConversations()
    }
  }

  const removeConversation = async (id) => {
    await deleteConversation(id)
    if (id === conversationId) newConversation()
    refreshConversations()
  }

  const sendMessage = async (text, files) => {
    if (streaming || !text.trim()) return

    const userMsg = {
      role: 'user',
      content: text,
      attachments: files.map((f) => ({ name: f.name, type: f.type, preview: f.preview })),
    }
    const history = [...messages, userMsg]
    setMessages([...history, { role: 'assistant', content: '' }])
    setAudits((prev) => [...prev, null]) // placeholder: auditoria pendente
    setStreaming(true)

    const apiMessages = history.map((m) => ({ role: m.role, content: m.content }))
    const fileIds = files.map((f) => f.file_id)

    const appendToLast = (updater) =>
      setMessages((prev) => {
        const next = [...prev]
        next[next.length - 1] = updater(next[next.length - 1])
        return next
      })

    try {
      await streamChat(apiMessages, fileIds, conversationId, { main: mainModel, auditor: auditorModel, rounds, booster }, {
        onMeta: (id) => setConversationId(id),
        onChunk: (chunk) =>
          appendToLast((m) => ({ ...m, content: m.content + chunk })),
        onDebate: (data) =>
          appendToLast((m) => ({ ...m, debate: [...(m.debate || []), data] })),
        onRevisionStart: (data) =>
          appendToLast((m) => ({ ...m, content: '', revising: data })),
        onBooster: (data) =>
          appendToLast((m) => ({ ...m, booster: data })),
        onFailover: (info) =>
          appendToLast((m) => ({
            ...m,
            notice: `${info.message} — ${info.took_over} assumiu esta resposta.`,
          })),
        onArtifacts: (data) =>
          appendToLast((m) => ({ ...m, artifacts: data })),
        onModelInfo: (data) =>
          appendToLast((m) => ({ ...m, model_used: data.used, metrics: data })),
        onAudit: (audit) =>
          setAudits((prev) => {
            const next = [...prev]
            next[next.length - 1] = audit
            return next
          }),
        onError: (msg) => {
          appendToLast((m) => ({
            ...m,
            content: m.content + `\n\n> ⚠️ Erro: ${msg}`,
          }))
          // marca a auditoria pendente como indisponível (o stream parou antes dela)
          setAudits((prev) => {
            const next = [...prev]
            if (next[next.length - 1] === null) {
              next[next.length - 1] = { status: 'ERROR', comment: 'Sem auditoria: o streaming falhou.' }
            }
            return next
          })
        },
        onDone: () => {},
      })
    } catch (e) {
      appendToLast((m) => ({ ...m, content: m.content || `⚠️ ${e.message}` }))
    } finally {
      setStreaming(false)
      refreshConversations()
    }
  }

  return (
    <div className="app">
      <Sidebar
        conversations={conversations}
        activeId={conversationId}
        onNew={newConversation}
        onOpen={openConversation}
        onDelete={removeConversation}
      />
      <div className="main">
        <div className="mobile-tabs">
          <button
            className={mobileTab === 'chat' ? 'active' : ''}
            onClick={() => setMobileTab('chat')}
          >
            Chat
          </button>
          <button
            className={mobileTab === 'auditor' ? 'active' : ''}
            onClick={() => setMobileTab('auditor')}
          >
            Auditoria
          </button>
        </div>
        <ChatPanel
          className={mobileTab !== 'chat' ? 'hidden-mobile' : ''}
          messages={messages}
          streaming={streaming}
          onSend={sendMessage}
          model={mainModel}
          modelOptions={modelOptions.main}
          onModelChange={setMainModel}
          rounds={rounds}
          onRoundsChange={setRounds}
          booster={booster}
          onBoosterChange={setBooster}
        />
        <AuditorPanel
          className={mobileTab !== 'auditor' ? 'hidden-mobile' : ''}
          messages={messages}
          audits={audits}
          streaming={streaming}
          model={auditorModel}
          modelOptions={modelOptions.auditor}
          onModelChange={setAuditorModel}
        />
      </div>
    </div>
  )
}
