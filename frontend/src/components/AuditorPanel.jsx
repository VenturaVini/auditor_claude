import { Markdown } from './MessageBubble.jsx'
import CodeRunner, { extractPythonCode } from './CodeRunner.jsx'
import { modelLabel } from '../services/models.js'
import ModelSelect from './ModelSelect.jsx'

function AuditCard({ question, audit, pending, roundLabel, isBooster = false }) {
  return (
    <div className={`audit-card ${isBooster ? 'booster-card' : ''}`}>
      {question && <div className="audit-question" title={question}>❝ {question}</div>}
      {roundLabel && <div className="audit-round">{roundLabel}</div>}
      {pending ? (
        <div className="audit-waiting">Aguardando o Claude terminar para auditar…</div>
      ) : audit.status === 'OK' ? (
        <>
          <div className="audit-badge ok">✓ Concordou com o Claude</div>
          {audit.early_stop && (
            <div className="audit-early-stop">
              Debate encerrado antecipadamente: aprovado na rodada {audit.round}/{audit.total}.
            </div>
          )}
          <div className="audit-comment">{audit.comment}</div>
        </>
      ) : audit.status === 'REVIEW' ? (
        <>
          <div className="audit-badge review">⚠ Discordou / complementou</div>
          <div className="audit-comment">{audit.comment}</div>
          {audit.response && (
            <div className="audit-response message-content">
              <Markdown>{audit.response}</Markdown>
              {(() => {
                const code = extractPythonCode(audit.response)
                return code ? <CodeRunner code={code} /> : null
              })()}
            </div>
          )}
        </>
      ) : (
        <>
          <div className="audit-badge error">Auditoria indisponível</div>
          <div className="audit-comment">{audit.comment}</div>
        </>
      )}
      {audit?.via && !pending && (
        <div className="audit-via">
          auditado por: {audit.via.includes(' ') ? audit.via : modelLabel(audit.via)}
          {audit.usage && (
            <> · {audit.usage.input_tokens} in / {audit.usage.output_tokens} out tokens</>
          )}
        </div>
      )}
    </div>
  )
}

export default function AuditorPanel({
  className = '',
  messages,
  audits,
  streaming,
  model,
  modelOptions = [],
  onModelChange,
}) {
  // Pareia cada turno: pergunta do usuário + mensagem do assistant (debate) + auditoria final
  const userQuestions = messages.filter((m) => m.role === 'user').map((m) => m.content)
  const assistantMsgs = messages.filter((m) => m.role === 'assistant')

  return (
    <aside className={`auditor-panel ${className}`}>
      <div className="auditor-header">
        <span className="dot" />
        <span style={{ flex: 1 }}>ChatGPT — Auditoria</span>
        <ModelSelect
          value={model}
          options={modelOptions}
          disabled={streaming}
          onChange={onModelChange}
          title="Modelo do auditor (principais em ordem de capacidade/custo)"
        />
      </div>
      <div className="auditor-body">
        {audits.length === 0 ? (
          <div className="auditor-empty">
            As auditorias do GPT aparecem aqui depois que o Claude responde.
            Em 4x+ rodadas, cada crítica intermediária do debate também aparece.
          </div>
        ) : (
          audits.map((audit, i) => {
            // debate: vindo do stream ({round,total,audit}) ou do Redis ({round,audit})
            const debate = (assistantMsgs[i]?.debate || []).map((d) => ({
              round: d.round,
              total: d.total || d.audit?.total,
              audit: d.audit,
            }))
            return (
              <div key={i} className="audit-group">
                {debate.map((d) => (
                  <AuditCard
                    key={`d${d.round}`}
                    question={d.round === 2 ? userQuestions[i] || '' : ''}
                    audit={d.audit || {}}
                    pending={false}
                    roundLabel={`Rodada ${d.round}/${d.total} — crítica intermediária`}
                  />
                ))}
                <AuditCard
                  question={debate.length === 0 ? userQuestions[i] || '' : ''}
                  audit={audit || {}}
                  pending={audit === null && (streaming ? i === audits.length - 1 : false)}
                  roundLabel={
                    audit?.round && audit?.total > 2
                      ? `Rodada ${audit.round}/${audit.total} — veredito final`
                      : null
                  }
                />
                {assistantMsgs[i]?.booster?.claude && (
                  <AuditCard
                    audit={assistantMsgs[i].booster.claude}
                    pending={false}
                    roundLabel={`Parecer final independente · ${modelLabel(assistantMsgs[i].booster.claude.via)}`}
                    isBooster
                  />
                )}
                {assistantMsgs[i]?.booster?.gpt && (
                  <AuditCard
                    audit={assistantMsgs[i].booster.gpt}
                    pending={false}
                    roundLabel={`Parecer final independente · ${modelLabel(assistantMsgs[i].booster.gpt.via)}`}
                    isBooster
                  />
                )}
              </div>
            )
          })
        )}
      </div>
    </aside>
  )
}
