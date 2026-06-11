import { useState } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter'
import { oneDark } from 'react-syntax-highlighter/dist/esm/styles/prism'
import DownloadMenu from './DownloadMenu.jsx'
import CodeRunner, { extractPythonCode } from './CodeRunner.jsx'
import FileCard, { ImageCard } from './FileCard.jsx'
import { artifactUrl } from '../services/api.js'
import { modelLabel } from '../services/models.js'

const FILE_MARKER = '# gerar-arquivo'

export function Markdown({ children }) {
  return (
    <ReactMarkdown
      remarkPlugins={[remarkGfm]}
      components={{
        code({ inline, className, children: code, ...props }) {
          const match = /language-(\w+)/.exec(className || '')
          if (!inline && match) {
            const text = String(code).replace(/\n$/, '')
            // Código de geração de arquivo: fica recolhido (o sistema já executou)
            if (text.trimStart().startsWith(FILE_MARKER)) {
              return (
                <details className="code-collapse">
                  <summary>Ver código usado para gerar o arquivo</summary>
                  <SyntaxHighlighter style={oneDark} language={match[1]} PreTag="div">
                    {text}
                  </SyntaxHighlighter>
                </details>
              )
            }
            return (
              <SyntaxHighlighter style={oneDark} language={match[1]} PreTag="div">
                {text}
              </SyntaxHighlighter>
            )
          }
          return (
            <code className={className} {...props}>
              {code}
            </code>
          )
        },
      }}
    >
      {children}
    </ReactMarkdown>
  )
}

export default function MessageBubble({ message, isStreaming }) {
  const [copied, setCopied] = useState(false)
  const isUser = message.role === 'user'

  const copy = async () => {
    await navigator.clipboard.writeText(message.content)
    setCopied(true)
    setTimeout(() => setCopied(false), 1500)
  }

  return (
    <div className="message">
      <div className={`avatar ${isUser ? 'user' : 'assistant'}`}>
        {isUser ? 'V' : 'C'}
      </div>
      <div className="message-body">
        <div className="message-role">
          {isUser ? 'Você' : 'Claude'}
          {!isUser && (message.model_used || message.metrics?.used) && (
            <span className="model-badge" title={`Modelo reportado pela API: ${message.model_used || message.metrics.used}`}>
              {modelLabel(message.model_used || message.metrics.used)}
            </span>
          )}
        </div>

        {isUser && message.attachments?.length > 0 && (
          <div className="msg-attachments">
            {message.attachments.map((a, i) =>
              a.type === 'image' ? (
                <ImageCard key={i} src={a.preview} name={a.name} size="md" />
              ) : (
                <FileCard key={i} name={a.name} />
              )
            )}
          </div>
        )}

        {message.notice && <div className="msg-notice">⚠️ {message.notice}</div>}

        {/* Indicador de rodada de refinamento (debate 4x+) */}
        {!isUser && isStreaming && message.revising && (
          <div className="artifacts-note generating">
            ✍️ Refinando a resposta com base na crítica do auditor (rodada {message.revising.round}/{message.revising.total})…
          </div>
        )}

        <div className={`message-content ${isStreaming ? 'cursor-blink' : ''}`}>
          {isUser ? (
            <p style={{ whiteSpace: 'pre-wrap' }}>{message.content}</p>
          ) : (
            <Markdown>{message.content}</Markdown>
          )}
        </div>

        {/* Arquivos gerados automaticamente pelo backend */}
        {!isUser && message.artifacts && (
          <div className="msg-artifacts">
            {message.artifacts.files?.length > 0 && (
              <div className="exec-files-grid">
                {message.artifacts.files.map((f) => (
                  <FileCard key={f.file_id} name={f.name} size={f.size} href={artifactUrl(f.file_id)} />
                ))}
              </div>
            )}
            {message.artifacts.auto_fixed && (
              <div className="artifacts-note">⚙️ o código tinha um erro e foi corrigido automaticamente</div>
            )}
            {message.artifacts.ok === false && (
              <div className="artifacts-note error">
                ✗ Falha ao gerar o arquivo: {message.artifacts.error}
              </div>
            )}
          </div>
        )}

        {/* Indicador enquanto o backend executa o código de geração */}
        {!isUser && !message.artifacts && message.content.includes(FILE_MARKER) && (
          <div className="artifacts-note generating">⏳ Gerando arquivo(s)…</div>
        )}

        {/* Métricas da resposta (tokens, tempo, velocidade, custo) */}
        {!isUser && !isStreaming && message.metrics && (
          <div className="metrics-line">
            {message.metrics.input_tokens != null && (
              <span title="Tokens de entrada / saída">
                ⇅ {message.metrics.input_tokens} in · {message.metrics.output_tokens} out
              </span>
            )}
            {message.metrics.duration_s != null && (
              <span title="Tempo total (primeiro token em ttft)">
                ⏱ {message.metrics.duration_s}s
              </span>
            )}
            {message.metrics.tokens_per_s != null && (
              <span title="Velocidade de geração">⚡ {message.metrics.tokens_per_s} tok/s</span>
            )}
            {message.metrics.cost_usd != null && (
              <span title="Custo estimado (tabela pública do provedor)">
                ~${message.metrics.cost_usd.toFixed(4)}
              </span>
            )}
            {message.metrics.rounds_total > 2 && (
              <span title="Rodadas do debate Claude ↔ GPT executadas">
                🔁 {message.metrics.rounds_executed}/{message.metrics.rounds_total} rodadas
              </span>
            )}
          </div>
        )}

        {!isUser && !isStreaming && message.content && (
          <>
            <div className="actions-bar">
              <button className="action-btn" onClick={copy}>
                {copied ? '✓ Copiado' : 'Copiar'}
              </button>
              <DownloadMenu content={message.content} />
            </div>
            {/* Botão manual só como FALLBACK (sem auto-execução do backend) */}
            {!message.artifacts && (() => {
              const code = extractPythonCode(message.content)
              return code && !code.trimStart().startsWith(FILE_MARKER)
                ? <CodeRunner code={code} />
                : null
            })()}
          </>
        )}
      </div>
    </div>
  )
}
