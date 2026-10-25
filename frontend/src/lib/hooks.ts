import { useCallback, useEffect, useMemo, useState } from 'react'
import { useSearchParams } from 'react-router'
import type { ListParams } from './types'

export function useDebounced<T>(value: T, delay = 300): T {
  const [debounced, setDebounced] = useState(value)
  useEffect(() => {
    const id = window.setTimeout(() => setDebounced(value), delay)
    return () => window.clearTimeout(id)
  }, [value, delay])
  return debounced
}

/**
 * List state (page, sort, search and filters) kept in the URL so it survives reloads and can
 * be shared; changing anything but the page resets to page 1.
 */
export function useListState(defaultSort: string, filterKeys: string[] = [], pageSize = 20) {
  const [search, setSearch] = useSearchParams()

  const params = useMemo<ListParams>(() => {
    const out: ListParams = {
      page: Number(search.get('page') ?? '1') || 1,
      page_size: pageSize,
      sort: search.get('sort') ?? defaultSort,
      order: search.get('order') === 'desc' ? 'desc' : 'asc',
      q: search.get('q') ?? undefined,
    }
    for (const key of filterKeys) {
      const value = search.get(key)
      if (value) out[key] = value
    }
    return out
  }, [search, defaultSort, filterKeys, pageSize])

  const update = useCallback(
    (changes: Record<string, string | number | undefined>) => {
      setSearch(
        (prev) => {
          const next = new URLSearchParams(prev)
          for (const [key, value] of Object.entries(changes)) {
            if (value === undefined || value === '') next.delete(key)
            else next.set(key, String(value))
          }
          if (!('page' in changes)) next.delete('page')
          return next
        },
        { replace: true },
      )
    },
    [setSearch],
  )

  const toggleSort = useCallback(
    (key: string) => {
      const order = params.sort === key && params.order === 'asc' ? 'desc' : 'asc'
      update({ sort: key, order })
    },
    [params.sort, params.order, update],
  )

  return { params, update, toggleSort }
}
