import { startTransition, useEffect, useRef, useState, type ReactNode } from 'react'

interface Props {
  children: ReactNode
  /** Reserved height while waiting, so nothing shifts when the content appears. */
  minHeight: string
  label: string
}

/**
 * Renders heavy, non-essential content (charts) only once it is near the viewport, and inside a
 * transition so React can split the work into small tasks. Keeps first load responsive on phones.
 */
export function DeferredRender({ children, minHeight, label }: Props) {
  const ref = useRef<HTMLDivElement>(null)
  const [visible, setVisible] = useState(false)

  useEffect(() => {
    const node = ref.current
    if (!node || visible) return
    if (typeof IntersectionObserver === 'undefined') {
      startTransition(() => setVisible(true))
      return
    }
    const observer = new IntersectionObserver(
      (entries) => {
        if (entries.some((e) => e.isIntersecting)) {
          observer.disconnect()
          startTransition(() => setVisible(true))
        }
      },
      { rootMargin: '200px 0px' },
    )
    observer.observe(node)
    return () => observer.disconnect()
  }, [visible])

  return (
    <div ref={ref} style={{ minHeight }}>
      {visible ? children : <p className="sr-only">{label}</p>}
    </div>
  )
}
