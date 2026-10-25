import type { ReactNode } from 'react'
import { Spinner } from './ui'

export interface Column<T> {
  key: string
  header: string
  render: (row: T) => ReactNode
  /** When set, the header becomes a sort button using this field name. */
  sortKey?: string
  /** Hide this column in the stacked mobile layout. */
  hideOnMobile?: boolean
  className?: string
}

interface DataTableProps<T> {
  caption: string
  columns: Column<T>[]
  rows: T[]
  rowKey: (row: T) => string | number
  sort?: string
  order?: 'asc' | 'desc'
  onSort?: (sortKey: string) => void
  /** Renders the row's primary cell (usually a link) in the mobile card layout. */
  mobileTitle: (row: T) => ReactNode
  fetching?: boolean
}

function SortIcon({ direction }: { direction: 'asc' | 'desc' | null }) {
  return (
    <span aria-hidden="true" className="text-xs text-slate-500">
      {direction === 'asc' ? '▲' : direction === 'desc' ? '▼' : '↕'}
    </span>
  )
}

/** Accessible data table on wide screens, a stacked card list on narrow ones. */
export function DataTable<T>({ caption, columns, rows, rowKey, sort, order, onSort, mobileTitle, fetching }: DataTableProps<T>) {
  return (
    <div className="relative">
      {fetching && (
        <div className="absolute top-2 right-3 text-indigo-600 dark:text-indigo-400" aria-hidden="true">
          <Spinner small />
        </div>
      )}
      <table className="hidden w-full text-left text-sm md:table">
        <caption className="sr-only">{caption}</caption>
        <thead className="border-b border-slate-200 text-xs tracking-wide text-slate-600 uppercase dark:border-slate-700 dark:text-slate-400">
          <tr>
            {columns.map((col) => {
              const active = col.sortKey !== undefined && col.sortKey === sort
              const ariaSort = active ? (order === 'desc' ? 'descending' : 'ascending') : undefined
              return (
                <th key={col.key} scope="col" aria-sort={col.sortKey ? (ariaSort ?? 'none') : undefined} className={`px-4 py-3 font-medium ${col.className ?? ''}`}>
                  {col.sortKey && onSort ? (
                    <button
                      type="button"
                      onClick={() => onSort(col.sortKey!)}
                      className="inline-flex items-center gap-1 rounded uppercase hover:text-slate-900 dark:hover:text-slate-100"
                    >
                      {col.header}
                      <SortIcon direction={active ? (order ?? 'asc') : null} />
                    </button>
                  ) : (
                    col.header
                  )}
                </th>
              )
            })}
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-200 dark:divide-slate-800">
          {rows.map((row) => (
            <tr key={rowKey(row)} className="hover:bg-slate-50 dark:hover:bg-slate-800/50">
              {columns.map((col) => (
                <td key={col.key} className={`px-4 py-3 align-middle ${col.className ?? ''}`}>
                  {col.render(row)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>

      <ul className="divide-y divide-slate-200 md:hidden dark:divide-slate-800" aria-label={caption}>
        {rows.map((row) => (
          <li key={rowKey(row)} className="px-4 py-3">
            <div className="font-medium">{mobileTitle(row)}</div>
            <dl className="mt-1 grid grid-cols-2 gap-x-3 gap-y-1 text-xs text-slate-600 dark:text-slate-400">
              {columns
                .filter((c) => !c.hideOnMobile)
                .slice(1)
                .map((col) => (
                  <div key={col.key} className="min-w-0">
                    <dt className="sr-only">{col.header}</dt>
                    <dd className="truncate">{col.render(row)}</dd>
                  </div>
                ))}
            </dl>
          </li>
        ))}
      </ul>
    </div>
  )
}

interface PaginationProps {
  page: number
  pageSize: number
  total: number
  onPage: (page: number) => void
}

export function Pagination({ page, pageSize, total, onPage }: PaginationProps) {
  const pages = Math.max(1, Math.ceil(total / pageSize))
  const from = total === 0 ? 0 : (page - 1) * pageSize + 1
  const to = Math.min(total, page * pageSize)
  return (
    <nav aria-label="Pagination" className="flex items-center justify-between gap-3 border-t border-slate-200 px-4 py-3 text-sm dark:border-slate-800">
      <p className="text-slate-600 dark:text-slate-400" aria-live="polite">
        {from}–{to} of {total}
      </p>
      <div className="flex items-center gap-2">
        <button
          type="button"
          className="rounded-lg border border-slate-300 px-3 py-1.5 disabled:opacity-50 dark:border-slate-600"
          onClick={() => onPage(page - 1)}
          disabled={page <= 1}
        >
          Previous
        </button>
        <span className="hidden sm:inline">
          Page {page} of {pages}
        </span>
        <button
          type="button"
          className="rounded-lg border border-slate-300 px-3 py-1.5 disabled:opacity-50 dark:border-slate-600"
          onClick={() => onPage(page + 1)}
          disabled={page >= pages}
        >
          Next
        </button>
      </div>
    </nav>
  )
}
