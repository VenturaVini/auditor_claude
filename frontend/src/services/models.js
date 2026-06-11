// Nomes amigáveis para os IDs de modelo (exibição; o value continua sendo o ID).
// "claude-sonnet-4-6" → "Claude Sonnet 4.6" · "gpt-4o-mini" → "GPT-4o mini"

const cap = (s) => s.charAt(0).toUpperCase() + s.slice(1)

export function modelLabel(id) {
  if (!id || typeof id !== 'string') return id

  if (id.startsWith('claude-')) {
    let parts = id.split('-').slice(1)
    // remove snapshot de data no final (8 dígitos)
    if (/^\d{8}$/.test(parts[parts.length - 1])) parts = parts.slice(0, -1)
    const name = cap(parts[0])
    const version = parts.slice(1).join('.')
    return version ? `Claude ${name} ${version}` : `Claude ${name}`
  }

  if (id.startsWith('gpt-')) {
    let rest = id.slice(4).replace(/-(\d{4}-\d{2}-\d{2})$/, '')
    const tokens = rest.split('-')
    const version = tokens.shift()
    const suffix = tokens
      .map((t) => (t === 'turbo' ? 'Turbo' : t === 'chat' ? 'Chat' : t))
      .join(' ')
    return suffix ? `GPT-${version} ${suffix}` : `GPT-${version}`
  }

  if (/^o\d/.test(id)) return `OpenAI ${id}`
  if (id.startsWith('chatgpt-')) return `ChatGPT ${id.slice(8)}`
  return id
}

// ===== Ranking (mais forte/custoso primeiro) e modelos principais =====

const CLAUDE_FAMILY_WEIGHT = { fable: 100, opus: 80, sonnet: 60, haiku: 40 }
const GPT_MODIFIER = { pro: 3, turbo: 1, '16k': 0.5, chat: -0.5, mini: -3, nano: -5 }

export function modelRank(id) {
  if (id.startsWith('claude-')) {
    let parts = id.split('-').slice(1)
    if (/^\d{8}$/.test(parts[parts.length - 1])) parts = parts.slice(0, -1)
    const weight = CLAUDE_FAMILY_WEIGHT[parts[0]] ?? 20
    const version = parseFloat(parts.slice(1).join('.')) || 0
    return 1000 + weight + version
  }
  if (id.startsWith('gpt-')) {
    const rest = id.slice(4).replace(/-(\d{4}-\d{2}-\d{2})$/, '')
    const tokens = rest.split('-')
    const version = parseFloat(tokens.shift()) || 0
    const mod = tokens.reduce((acc, t) => acc + (GPT_MODIFIER[t] ?? 0), 0)
    return version * 10 + mod
  }
  const o = id.match(/^o(\d)/)
  if (o) return 35 + parseInt(o[1], 10) + (id.includes('pro') ? 1 : id.includes('mini') ? -1 : 0)
  return 0
}

// Principais de cada provedor (match por prefixo, na ordem forte→barato)
const MAIN_PREFIXES = [
  'claude-fable-5', 'claude-opus-4-8', 'claude-sonnet-4-6', 'claude-haiku-4-5',
  'gpt-5.5', 'gpt-5.4', 'gpt-5', 'gpt-4o', 'gpt-4o-mini',
]

/** Separa {main, rest}, ambos ordenados do mais forte/custoso ao mais barato. */
export function organizeModels(options) {
  const sorted = [...options].sort((a, b) => modelRank(b) - modelRank(a))
  const main = []
  for (const pref of MAIN_PREFIXES) {
    // match exato primeiro (evita pegar variantes -pro/-mini); snapshot datado como fallback
    const hit =
      sorted.find((m) => m === pref && !main.includes(m)) ||
      sorted.find((m) => m.startsWith(pref + '-2') && !main.includes(m))
    if (hit) main.push(hit)
  }
  const rest = sorted.filter((m) => !main.includes(m))
  return { main, rest }
}
