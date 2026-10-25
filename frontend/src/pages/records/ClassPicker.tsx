import { useId } from 'react'
import { useAllClasses } from '@/lib/queries'

export function ClassPicker({ value, onChange }: { value: string; onChange: (classId: string) => void }) {
  const id = useId()
  const classes = useAllClasses()
  return (
    <div className="flex flex-col gap-1">
      <label htmlFor={id} className="text-xs font-medium text-slate-600 dark:text-slate-400">
        Class
      </label>
      <select id={id} className="input sm:w-48" value={value} onChange={(e) => onChange(e.target.value)} disabled={classes.isPending}>
        <option value="">{classes.isPending ? 'Loading…' : 'Choose a class'}</option>
        {(classes.data ?? []).map((c) => (
          <option key={c.id} value={c.id}>
            {c.name}
          </option>
        ))}
      </select>
    </div>
  )
}
