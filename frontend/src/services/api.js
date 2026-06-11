const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

export async function uploadFile(file) {
  const form = new FormData()
  form.append('file', file)
  const res = await fetch(`${API_URL}/api/upload`, { method: 'POST', body: form })
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new Error(err.detail || `Falha no upload (${res.status})`)
  }
  return res.json()
}

/**
 * Envia o chat e consome o stream SSE via fetch (EventSource não suporta POST).
 * callbacks: { onMeta(convId), onChunk(text), onAudit(obj), onError(msg), onDone() }
 */
export async function fetchModels() {
  const res = await fetch(`${API_URL}/api/models`)
  if (!res.ok) return null
  return res.json()
}

export async function streamChat(messages, fileIds, conversationId, models, callbacks) {
  const res = await fetch(`${API_URL}/api/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      messages,
      files: fileIds,
      conversation_id: conversationId,
      main_model: models?.main,
      auditor_model: models?.auditor,
      rounds: models?.rounds || 2,
      booster: models?.booster || false,
    }),
  })
  if (!res.ok || !res.body) {
    throw new Error(`Erro na API de chat (${res.status})`)
  }

  const reader = res.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  const handleLine = (line) => {
    if (!line.startsWith('data: ')) return
    const payload = line.slice(6)
    if (payload === '[DONE]') {
      callbacks.onDone?.()
      return
    }
    if (payload.startsWith('[AUDIT]')) {
      try {
        callbacks.onAudit?.(JSON.parse(payload.slice(7)))
      } catch {
        callbacks.onAudit?.({ status: 'ERROR', comment: 'Auditoria ilegível' })
      }
      return
    }
    try {
      const data = JSON.parse(payload)
      if (data.type === 'chunk') callbacks.onChunk?.(data.text)
      else if (data.type === 'meta') callbacks.onMeta?.(data.conversation_id)
      else if (data.type === 'failover') callbacks.onFailover?.(data)
      else if (data.type === 'artifacts') callbacks.onArtifacts?.(data)
      else if (data.type === 'model_info') callbacks.onModelInfo?.(data)
      else if (data.type === 'debate') callbacks.onDebate?.(data)
      else if (data.type === 'revision_start') callbacks.onRevisionStart?.(data)
      else if (data.type === 'booster') callbacks.onBooster?.(data)
      else if (data.type === 'error') callbacks.onError?.(data.message)
    } catch {
      /* linha parcial/keep-alive — ignora */
    }
  }

  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })
    const parts = buffer.split('\n\n')
    buffer = parts.pop()
    for (const part of parts) {
      for (const line of part.split('\n')) handleLine(line)
    }
  }
  if (buffer.trim()) handleLine(buffer.trim())
}

export async function downloadResponse(format, content) {
  const res = await fetch(`${API_URL}/api/download/${format}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ content }),
  })
  if (!res.ok) throw new Error(`Falha ao gerar ${format} (${res.status})`)
  const blob = await res.blob()
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `resposta.${format}`
  document.body.appendChild(a)
  a.click()
  a.remove()
  URL.revokeObjectURL(url)
}

export async function executeCode(code) {
  const res = await fetch(`${API_URL}/api/execute`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ code }),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new Error(err.detail || `Falha na execução (${res.status})`)
  }
  return res.json()
}

export function artifactUrl(fileId) {
  return `${API_URL}/api/files/${fileId}`
}

export async function listConversations() {
  const res = await fetch(`${API_URL}/api/conversations`)
  if (!res.ok) return []
  return res.json()
}

export async function getConversation(id) {
  const res = await fetch(`${API_URL}/api/conversations/${id}`)
  if (!res.ok) throw new Error('Conversa não encontrada')
  return res.json()
}

export async function deleteConversation(id) {
  await fetch(`${API_URL}/api/conversations/${id}`, { method: 'DELETE' })
}
