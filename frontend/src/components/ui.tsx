import type { ButtonHTMLAttributes, ReactNode } from 'react'
import { Link } from 'react-router'
import { errorMessage } from '@/lib/api'
import { buttonClass, type Variant } from './buttonClass'

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant
  loading?: boolean
}

export function Button({ variant = 'primary', loading = false, className = '', children, disabled, ...rest }: ButtonProps) {
  return (
    <button
      type="button"
      className={buttonClass(variant, className)}
      disabled={disabled || loading}
      aria-busy={loading || undefined}
      {...rest}
    >
      {loading && <Spinner small />}
      {children}
    </button>
  )
}

export function Spinner({ small = false }: { small?: boolean }) {
  return (
    <span
      aria-hidden="true"
      className={`inline-block animate-spin rounded-full border-2 border-current border-r-transparent ${small ? 'size-4' : 'size-6'}`}
    />
  )
}

export function PageHeader({ title, description, actions }: { title: string; description?: string; actions?: ReactNode }) {
  return (
    <div className="mb-6 flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">{title}</h1>
        {description && <p className="mt-1 text-sm text-slate-600 dark:text-slate-400">{description}</p>}
      </div>
      {actions && <div className="flex flex-wrap gap-2">{actions}</div>}
    </div>
  )
}

export function LoadingState({ label = 'Loading…' }: { label?: string }) {
  return (
    <div role="status" className="flex items-center justify-center gap-3 py-16 text-slate-600 dark:text-slate-400">
      <Spinner />
      <span>{label}</span>
    </div>
  )
}

export function EmptyState({ title, description, action }: { title: string; description?: string; action?: ReactNode }) {
  return (
    <div className="flex flex-col items-center justify-center gap-2 px-4 py-16 text-center">
      <p className="text-base font-medium">{title}</p>
      {description && <p className="max-w-md text-sm text-slate-600 dark:text-slate-400">{description}</p>}
      {action && <div className="mt-2">{action}</div>}
    </div>
  )
}

export function ErrorState({ error, onRetry }: { error: unknown; onRetry?: () => void }) {
  return (
    <div role="alert" className="flex flex-col items-center justify-center gap-3 px-4 py-16 text-center">
      <p className="text-base font-medium text-red-800 dark:text-red-300">Could not load data</p>
      <p className="max-w-md text-sm text-slate-600 dark:text-slate-400">{errorMessage(error)}</p>
      {onRetry && (
        <Button variant="secondary" onClick={onRetry}>
          Try again
        </Button>
      )}
    </div>
  )
}

const BADGE_TONES = {
  green: 'bg-emerald-100 text-emerald-900 dark:bg-emerald-900/50 dark:text-emerald-200',
  red: 'bg-red-100 text-red-900 dark:bg-red-900/50 dark:text-red-200',
  amber: 'bg-amber-100 text-amber-900 dark:bg-amber-900/50 dark:text-amber-200',
  slate: 'bg-slate-200 text-slate-800 dark:bg-slate-700 dark:text-slate-100',
  indigo: 'bg-indigo-100 text-indigo-900 dark:bg-indigo-900/50 dark:text-indigo-200',
} as const

export type BadgeTone = keyof typeof BADGE_TONES

export function Badge({ tone = 'slate', children }: { tone?: BadgeTone; children: ReactNode }) {
  return (
    <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${BADGE_TONES[tone]}`}>
      {children}
    </span>
  )
}

export function BackLink({ to, children }: { to: string; children: ReactNode }) {
  return (
    <Link
      to={to}
      className="mb-4 inline-flex items-center gap-1 text-sm font-medium text-indigo-700 hover:underline dark:text-indigo-300"
    >
      <span aria-hidden="true">←</span> {children}
    </Link>
  )
}

export function DefinitionList({ items }: { items: [string, ReactNode][] }) {
  return (
    <dl className="grid grid-cols-1 gap-x-6 gap-y-4 sm:grid-cols-2">
      {items.map(([term, value]) => (
        <div key={term}>
          <dt className="text-xs font-medium tracking-wide text-slate-600 uppercase dark:text-slate-400">{term}</dt>
          <dd className="mt-1 text-sm break-words">{value ?? '—'}</dd>
        </div>
      ))}
    </dl>
  )
}
