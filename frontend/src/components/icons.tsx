// Small stroke icons drawn for EduPulse (24×24 grid). Decorative unless given a label.

const PATHS = {
  dashboard: 'M4 13h6V4H4zM14 20h6v-9h-6zM4 20h6v-4H4zM14 8h6V4h-6z',
  students: 'M12 12a4 4 0 1 0 0-8 4 4 0 0 0 0 8zM4 20c0-3.3 3.6-6 8-6s8 2.7 8 6',
  classes: 'M3 7l9-4 9 4-9 4zM7 9v5c0 1.7 2.2 3 5 3s5-1.3 5-3V9M21 7v6',
  attendance: 'M5 4h14v16H5zM9 2v4M15 2v4M8.5 13l2.5 2.5 4.5-5',
  grades: 'M5 20V10M12 20V4M19 20v-7',
  teachers: 'M9 11a3 3 0 1 0 0-6 3 3 0 0 0 0 6zM3 19c0-2.8 2.7-5 6-5s6 2.2 6 5M17 8h4M19 6v4',
  staff: 'M4 8h16v11H4zM9 8V5h6v3M4 13h16',
  more: 'M5 12h.01M12 12h.01M19 12h.01',
  sun: 'M12 16a4 4 0 1 0 0-8 4 4 0 0 0 0 8zM12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4',
  moon: 'M20 14.5A8 8 0 0 1 9.5 4 8 8 0 1 0 20 14.5z',
  logout: 'M15 4h4v16h-4M10 8l-4 4 4 4M6 12h10',
  close: 'M6 6l12 12M18 6L6 18',
  risk: 'M12 3l9 16H3zM12 10v4M12 17h.01',
  audit: 'M6 3h9l3 3v15H6zM9 9h6M9 13h6M9 17h3',
} as const

export type IconName = keyof typeof PATHS

export function Icon({ name, className = 'size-5', label }: { name: IconName; className?: string; label?: string }) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={1.8}
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
      aria-hidden={label ? undefined : true}
      role={label ? 'img' : undefined}
      aria-label={label}
    >
      <path d={PATHS[name]} />
    </svg>
  )
}
