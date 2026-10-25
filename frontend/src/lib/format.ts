import type { BadgeTone } from '@/components/ui'
import type { AttendanceStatus, StudentStatus } from './types'

export function formatDate(iso: string | null | undefined): string {
  if (!iso) return '—'
  const date = new Date(iso.length === 10 ? `${iso}T00:00:00` : iso)
  return date.toLocaleDateString(undefined, { year: 'numeric', month: 'short', day: 'numeric' })
}

export function fullName(p: { first_name: string; last_name: string }): string {
  return `${p.first_name} ${p.last_name}`
}

export const STUDENT_STATUS_TONE: Record<StudentStatus, BadgeTone> = {
  active: 'green',
  inactive: 'slate',
  graduated: 'indigo',
  withdrawn: 'amber',
}

export const ATTENDANCE_LABEL: Record<AttendanceStatus, string> = {
  present: 'Present',
  absent: 'Absent',
  late: 'Late',
  excused: 'Excused',
}

export function capitalize(text: string): string {
  return text.charAt(0).toUpperCase() + text.slice(1)
}

/** Trigger a browser download of text content. */
export function downloadText(filename: string, content: string, type = 'text/csv'): void {
  const url = URL.createObjectURL(new Blob([content], { type }))
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  link.click()
  URL.revokeObjectURL(url)
}
