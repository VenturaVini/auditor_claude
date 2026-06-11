import { useState } from 'react'
import { executeCode, artifactUrl } from '../services/api.js'
import FileCard from './FileCard.jsx'

const PYTHON_BLOCK = /```python\n([\s\S]*?)```/g

export function extractPythonCode(markdown) {
  const blocks = []
  let m
  const re = new RegExp(PYTHON_BLOCK)
  while ((m = re.exec(markdown)) !== null) blocks.push(m[1])
  return blocks.join('\n\n')
}

/** Botão "Executar código" + resultado (stdout/stderr + arquivos gerados). */
export default function CodeRunner({ code }) {
  const [running, setRunning] = useState(false)
  const [result, setResult] = useState(null)

  const run = async () => {
    setRunning(true)
    setResult(null)
    try {
      setResult(await executeCode(code))
    } catch (e) {
      setResult({ ok: false, stdout: '', stderr: e.message, files: [] })
    } finally {
      setRunning(false)
    }
  }

  return (
    <div className="code-runner">
      <button className="action-btn run-btn" onClick={run} disabled={running}>
        {running ? '⏳ Executando…' : '▶ Executar código'}
      </button>

      {result && (
        <div className={`exec-result ${result.ok ? 'ok' : 'fail'}`}>
          <div className="exec-status">
            {result.ok ? '✓ Executado com sucesso' : '✗ Falhou'}
            {result.auto_fixed && (
              <span className="exec-autofix"> · ⚙️ o código tinha um erro e foi corrigido automaticamente</span>
            )}
          </div>
          {result.stdout && <pre className="exec-output">{result.stdout}</pre>}
          {result.stderr && <pre className="exec-output stderr">{result.stderr}</pre>}
          {result.files.length > 0 && (
            <div className="exec-files">
              <div className="exec-files-title">Arquivos gerados:</div>
              <div className="exec-files-grid">
                {result.files.map((f) => (
                  <FileCard
                    key={f.file_id}
                    name={f.name}
                    size={f.size}
                    href={artifactUrl(f.file_id)}
                  />
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
