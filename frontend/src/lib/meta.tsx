import { useQuery } from '@tanstack/react-query'
import { useMemo } from 'react'
import { api } from './api'
import type { Meta } from './types'

/** Public installation facts (demo mode, public demo, demo accounts). */
export function useMeta() {
  return useQuery({ queryKey: ['meta'], queryFn: () => api.get<Meta>('/meta'), retry: false, staleTime: 5 * 60_000 })
}

export const DEMO_LOCK_REASON_ID = 'public-demo-lock-reason'
export const DEMO_LOCK_REASON = 'Disabled in the public demo'

/** Props for a button whose action the server refuses in the public demo: disabled, with a
 * tooltip and an accessible description (the text lives in the public-demo banner). */
export function useDemoLock(): { disabled?: boolean; title?: string; 'aria-describedby'?: string } {
  const locked = Boolean(useMeta().data?.public_demo)
  return useMemo(
    () => (locked ? { disabled: true, title: DEMO_LOCK_REASON, 'aria-describedby': DEMO_LOCK_REASON_ID } : {}),
    [locked],
  )
}

/** Shown on every page of a public demo. */
export function PublicDemoBanner() {
  const meta = useMeta()
  if (!meta.data?.public_demo) return null
  return (
    <section
      id="public-demo-banner"
      aria-label="Public demo notice"
      className="sticky top-0 z-50 flex h-(--demo-banner-h) items-center justify-center border-b border-amber-300 bg-amber-100 px-4 text-center text-xs leading-tight font-medium text-amber-950 sm:text-sm dark:border-amber-700 dark:bg-amber-950 dark:text-amber-100"
    >
      Public demo — synthetic data, reset every {meta.data.demo_reset_hours} hours
      <span id={DEMO_LOCK_REASON_ID} hidden>
        {DEMO_LOCK_REASON}: deleting records, CSV import, account approval and creating administrators are switched off
        for everyone.
      </span>
    </section>
  )
}
