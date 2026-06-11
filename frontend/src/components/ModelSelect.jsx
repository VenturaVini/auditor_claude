import { useState } from 'react'
import { modelLabel, organizeModels } from '../services/models.js'

/** Seletor de modelo: mostra os principais (forte→barato) + "mostrar todos". */
export default function ModelSelect({ value, options = [], onChange, disabled, title }) {
  const [showAll, setShowAll] = useState(false)
  const { main, rest } = organizeModels(options)

  let visible
  if (showAll || rest.length === 0) {
    visible = [...main, ...rest]
  } else {
    visible = [...main]
    // garante que o valor selecionado sempre aparece
    if (value && !visible.includes(value) && options.includes(value)) visible.push(value)
  }

  return (
    <select
      className="model-select"
      value={value}
      disabled={disabled}
      title={title}
      onChange={(e) => {
        if (e.target.value === '__all__') {
          setShowAll(true)
          return
        }
        onChange(e.target.value)
      }}
    >
      {visible.map((m) => (
        <option key={m} value={m}>{modelLabel(m)}</option>
      ))}
      {!showAll && rest.length > 0 && (
        <option value="__all__">▾ mostrar todos ({options.length} modelos)</option>
      )}
    </select>
  )
}
