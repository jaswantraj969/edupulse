import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useId, useMemo, useState } from 'react'
import { useSearchParams } from 'react-router'
import { Button, EmptyState, ErrorState, LoadingState, PageHeader } from '@/components/ui'
import { api, errorMessage } from '@/lib/api'
import { ATTENDANCE_LABEL, fullName } from '@/lib/format'
import { useAcademicYears } from '@/lib/queries'
import { useToast } from '@/lib/toast'
import type { AttendanceSheet, AttendanceStatus } from '@/lib/types'
import { ClassPicker } from './ClassPicker'

const STATUSES: AttendanceStatus[] = ['present', 'absent', 'late', 'excused']
const SELECTED: Record<AttendanceStatus, string> = {
  present: 'border-emerald-700 bg-emerald-700 text-white dark:border-emerald-400 dark:bg-emerald-400 dark:text-slate-950',
  absent: 'border-red-700 bg-red-700 text-white dark:border-red-400 dark:bg-red-400 dark:text-slate-950',
  late: 'border-amber-700 bg-amber-700 text-white dark:border-amber-300 dark:bg-amber-300 dark:text-slate-950',
  excused: 'border-indigo-700 bg-indigo-700 text-white dark:border-indigo-300 dark:bg-indigo-300 dark:text-slate-950',
}

const isoToday = () => new Date().toISOString().slice(0, 10)

function StatusChoice({ name, label, value, onChange }: { name: string; label: string; value: AttendanceStatus | null; onChange: (s: AttendanceStatus) => void }) {
  return (
    <fieldset className="flex flex-wrap gap-1.5">
      <legend className="sr-only">Attendance for {label}</legend>
      {STATUSES.map((status) => (
        <label
          key={status}
          className={`cursor-pointer rounded-lg border px-3 py-1.5 text-xs font-medium has-[:focus-visible]:outline-2 has-[:focus-visible]:outline-offset-2 has-[:focus-visible]:outline-indigo-600 ${
            value === status ? SELECTED[status] : 'border-slate-300 text-slate-700 hover:bg-slate-100 dark:border-slate-600 dark:text-slate-200 dark:hover:bg-slate-800'
          }`}
        >
          <input type="radio" className="sr-only" name={name} value={status} checked={value === status} onChange={() => onChange(status)} />
          {ATTENDANCE_LABEL[status]}
        </label>
      ))}
    </fieldset>
  )
}

export default function AttendancePage() {
  const dateId = useId()
  const toast = useToast()
  const queryClient = useQueryClient()
  const years = useAcademicYears()
  const [search, setSearch] = useSearchParams()
  const classId = search.get('class_id') ?? ''
  const year = years.data?.[0]
  const defaultDate = year && isoToday() > year.end_date ? year.end_date : isoToday()
  const day = search.get('date') ?? defaultDate
  const [changes, setChanges] = useState<Record<number, AttendanceStatus>>({})

  const setParam = (key: string, value: string) => {
    setChanges({})
    setSearch((prev) => {
      const next = new URLSearchParams(prev)
      if (value) next.set(key, value)
      else next.delete(key)
      return next
    })
  }

  const sheetKey = ['attendance', classId, day]
  const sheet = useQuery({
    queryKey: sheetKey,
    queryFn: () => api.get<AttendanceSheet>(`/classes/${classId}/attendance`, { date: day }),
    enabled: Boolean(classId && day),
  })

  const current = useMemo(() => {
    const out: Record<number, AttendanceStatus | null> = {}
    for (const r of sheet.data?.records ?? []) out[r.student_id] = changes[r.student_id] ?? r.status
    return out
  }, [sheet.data, changes])
  const dirty = Object.keys(changes).length
  const unmarked = Object.values(current).filter((s) => s === null).length

  const save = useMutation({
    mutationFn: () =>
      api.put<AttendanceSheet>(`/classes/${classId}/attendance`, {
        date: day,
        records: Object.entries(changes).map(([student_id, status]) => ({ student_id: Number(student_id), status })),
      }),
    onSuccess: (data) => {
      queryClient.setQueryData(sheetKey, data)
      // Per-student summaries and the dashboard aggregate this data.
      void queryClient.invalidateQueries({ queryKey: ['students'] })
      void queryClient.invalidateQueries({ queryKey: ['dashboard'] })
      setChanges({})
      toast.success(`Attendance saved for ${data.class_name}`)
    },
    onError: (error) => toast.error(errorMessage(error)),
  })

  const markAllPresent = () => {
    setChanges((prev) => {
      const next = { ...prev }
      for (const [sid, status] of Object.entries(current)) if (status === null) next[Number(sid)] = 'present'
      return next
    })
  }

  return (
    <>
      <PageHeader title="Attendance" description="Mark daily attendance for a class." />
      <div className="card mb-4 flex flex-col gap-3 p-4 sm:flex-row sm:items-end">
        <ClassPicker value={classId} onChange={(v) => setParam('class_id', v)} />
        <div className="flex flex-col gap-1">
          <label htmlFor={dateId} className="text-xs font-medium text-slate-600 dark:text-slate-400">
            Date
          </label>
          <input
            id={dateId}
            type="date"
            className="input sm:w-44"
            value={day}
            min={year?.start_date}
            max={year && year.end_date < isoToday() ? year.end_date : isoToday()}
            onChange={(e) => setParam('date', e.target.value)}
          />
        </div>
      </div>

      {!classId ? (
        <div className="card">
          <EmptyState title="Choose a class" description="Pick a class and a date to see its attendance sheet." />
        </div>
      ) : sheet.isPending ? (
        <LoadingState />
      ) : sheet.isError ? (
        <ErrorState error={sheet.error} onRetry={() => void sheet.refetch()} />
      ) : sheet.data.records.length === 0 ? (
        <div className="card">
          <EmptyState title="No students in this class" />
        </div>
      ) : (
        <div className="card overflow-hidden">
          <div className="flex flex-col gap-2 border-b border-slate-200 p-4 sm:flex-row sm:items-center sm:justify-between dark:border-slate-800">
            <p className="text-sm text-slate-600 dark:text-slate-400" aria-live="polite">
              {sheet.data.records.length} students · {unmarked} not marked{dirty ? ` · ${dirty} unsaved` : ''}
            </p>
            <div className="flex gap-2">
              <Button variant="secondary" onClick={markAllPresent} disabled={unmarked === 0}>
                Mark unmarked present
              </Button>
              <Button onClick={() => save.mutate()} loading={save.isPending} disabled={dirty === 0}>
                Save attendance
              </Button>
            </div>
          </div>
          <ul className="divide-y divide-slate-200 dark:divide-slate-800" aria-label={`Attendance for ${sheet.data.class_name}`}>
            {sheet.data.records.map((r) => (
              <li key={r.student_id} className="flex flex-col gap-2 px-4 py-3 sm:flex-row sm:items-center sm:justify-between">
                <div>
                  <p className="text-sm font-medium">{fullName(r)}</p>
                  <p className="font-mono text-xs text-slate-600 dark:text-slate-400">{r.student_no}</p>
                </div>
                <StatusChoice
                  name={`status-${r.student_id}`}
                  label={fullName(r)}
                  value={current[r.student_id] ?? null}
                  onChange={(status) => setChanges((prev) => ({ ...prev, [r.student_id]: status }))}
                />
              </li>
            ))}
          </ul>
        </div>
      )}
    </>
  )
}
