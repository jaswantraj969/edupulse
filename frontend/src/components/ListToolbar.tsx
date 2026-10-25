import { useEffect, useId, useState, type ReactNode } from 'react'
import { useDebounced } from '@/lib/hooks'

interface SearchBoxProps {
  value: string
  onChange: (value: string) => void
  label: string
  placeholder?: string
}

export function SearchBox({ value, onChange, label, placeholder }: SearchBoxProps) {
  const id = useId()
  const [text, setText] = useState(value)
  const debounced = useDebounced(text)
  useEffect(() => {
    if (debounced !== value) onChange(debounced)
    // eslint-disable-next-line react-hooks/exhaustive-deps -- only react to the debounced text
  }, [debounced])
  return (
    <div className="flex min-w-0 flex-1 flex-col gap-1 sm:max-w-xs">
      <label htmlFor={id} className="text-xs font-medium text-slate-600 dark:text-slate-400">
        {label}
      </label>
      <input
        id={id}
        type="search"
        className="input"
        value={text}
        placeholder={placeholder}
        onChange={(e) => setText(e.target.value)}
      />
    </div>
  )
}

interface FilterSelectProps {
  label: string
  value: string
  onChange: (value: string) => void
  options: { value: string | number; label: string }[]
  allLabel?: string
}

export function FilterSelect({ label, value, onChange, options, allLabel = 'All' }: FilterSelectProps) {
  const id = useId()
  return (
    <div className="flex flex-col gap-1">
      <label htmlFor={id} className="text-xs font-medium text-slate-600 dark:text-slate-400">
        {label}
      </label>
      <select id={id} className="input sm:w-44" value={value} onChange={(e) => onChange(e.target.value)}>
        <option value="">{allLabel}</option>
        {options.map((o) => (
          <option key={o.value} value={o.value}>
            {o.label}
          </option>
        ))}
      </select>
    </div>
  )
}

export function ListToolbar({ children }: { children: ReactNode }) {
  return (
    <div className="flex flex-col gap-3 border-b border-slate-200 p-4 sm:flex-row sm:flex-wrap sm:items-end dark:border-slate-800">
      {children}
    </div>
  )
}
