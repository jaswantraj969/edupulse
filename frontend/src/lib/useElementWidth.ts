import { useEffect, useRef, useState } from 'react'

/** Width of an element, updated on resize (one ResizeObserver, no per-render layout reads). */
export function useElementWidth<T extends HTMLElement>() {
  const ref = useRef<T>(null)
  const [width, setWidth] = useState(0)
  useEffect(() => {
    const node = ref.current
    if (!node) return
    setWidth(Math.floor(node.clientWidth))
    if (typeof ResizeObserver === 'undefined') return
    const observer = new ResizeObserver((entries) => {
      const next = Math.floor(entries[0]?.contentRect.width ?? 0)
      setWidth((prev) => (Math.abs(prev - next) >= 1 ? next : prev))
    })
    observer.observe(node)
    return () => observer.disconnect()
  }, [])
  return [ref, width] as const
}
