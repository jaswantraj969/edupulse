import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useId, useMemo, useState } from 'react'
import { useSearchParams } from 'react-router'
import { z } from 'zod'
import { RecordFormDialog } from '@/components/RecordFormDialog'
import { Button, EmptyState, ErrorState, LoadingState, PageHeader } from '@/components/ui'
import { api, errorMessage } from '@/lib/api'
import { useUser } from '@/lib/auth'
import { capitalize, formatDate, fullName } from '@/lib/format'
import { useAcademicYears } from '@/lib/queries'
import { useToast } from '@/lib/toast'
import type { Assessment, Assignment, GradeSheet } from '@/lib/types'
import { ClassPicker } from './ClassPicker'

const KINDS = ['quiz', 'test', 'exam', 'assignment', 'project'] as const

const assessmentSchema = z
  .object({
    assignment_id: z.string().min(1, 'Choose a subject'),
    term_id: z.string().min(1, 'Choose a term'),
    title: z.string().trim().min(1, 'Title is required').max(120),
    kind: z.enum(KINDS),
    max_score: z.coerce.number<string>().gt(0, 'Must be greater than 0').max(1000),
    weight: z.coerce.number<string>().gt(0, 'Must be greater than 0').max(10),
    assessed_on: z.string().min(1, 'Date is required'),
  })
  .transform((v) => ({ ...v, assignment_id: Number(v.assignment_id), term_id: Number(v.term_id) }))
type AssessmentFormValues = z.input<typeof assessmentSchema>

function GradeSheetEditor({ assessmentId, canEdit }: { assessmentId: number; canEdit: (a: Assessment) => boolean }) {
  const toast = useToast()
  const queryClient = useQueryClient()
  const key = ['grades', assessmentId]
  const sheet = useQuery({ queryKey: key, queryFn: () => api.get<GradeSheet>(`/assessments/${assessmentId}/grades`) })
  const [draft, setDraft] = useState<Record<number, string>>({})

  const errors = useMemo(() => {
    const out: Record<number, string> = {}
    const max = sheet.data?.assessment.max_score ?? 0
    for (const [sid, text] of Object.entries(draft)) {
      if (text.trim() === '') continue
      const value = Number(text)
      if (Number.isNaN(value)) out[Number(sid)] = 'Enter a number'
      else if (value < 0) out[Number(sid)] = 'Cannot be negative'
      else if (value > max) out[Number(sid)] = `Maximum is ${max}`
    }
    return out
  }, [draft, sheet.data])
  const entries = Object.entries(draft).filter(([, text]) => text.trim() !== '')

  const save = useMutation({
    mutationFn: () =>
      api.put<GradeSheet>(`/assessments/${assessmentId}/grades`, {
        grades: entries.map(([student_id, text]) => ({ student_id: Number(student_id), score: Number(text) })),
      }),
    onSuccess: (data) => {
      queryClient.setQueryData(key, data)
      void queryClient.invalidateQueries({ queryKey: ['assessments'] })
      void queryClient.invalidateQueries({ queryKey: ['students'] })
      void queryClient.invalidateQueries({ queryKey: ['dashboard'] })
      setDraft({})
      toast.success('Grades saved')
    },
    onError: (error) => toast.error(errorMessage(error)),
  })

  if (sheet.isPending) return <LoadingState />
  if (sheet.isError) return <ErrorState error={sheet.error} onRetry={() => void sheet.refetch()} />
  const { assessment, grades } = sheet.data
  const editable = canEdit(assessment)
  const hasErrors = Object.keys(errors).length > 0

  return (
    <div className="card overflow-hidden">
      <div className="flex flex-col gap-2 border-b border-slate-200 p-4 sm:flex-row sm:items-center sm:justify-between dark:border-slate-800">
        <div>
          <h2 className="text-base font-semibold">{assessment.title}</h2>
          <p className="text-sm text-slate-600 dark:text-slate-400">
            {assessment.subject_name} · {capitalize(assessment.kind)} · out of {assessment.max_score} · {formatDate(assessment.assessed_on)}
          </p>
        </div>
        {editable ? (
          <Button onClick={() => save.mutate()} loading={save.isPending} disabled={entries.length === 0 || hasErrors}>
            Save grades
          </Button>
        ) : (
          <p className="text-sm text-slate-600 dark:text-slate-400">Read only — only the subject teacher can enter grades.</p>
        )}
      </div>
      <ul className="divide-y divide-slate-200 dark:divide-slate-800" aria-label={`Grades for ${assessment.title}`}>
        {grades.map((g) => {
          const inputId = `score-${g.student_id}`
          const error = errors[g.student_id]
          const value = draft[g.student_id] ?? (g.score === null ? '' : String(g.score))
          return (
            <li key={g.student_id} className="flex items-center justify-between gap-3 px-4 py-2.5">
              <label htmlFor={inputId} className="min-w-0 text-sm">
                <span className="block truncate font-medium">{fullName(g)}</span>
                <span className="font-mono text-xs text-slate-600 dark:text-slate-400">{g.student_no}</span>
              </label>
              <div className="flex flex-col items-end">
                <div className="flex items-center gap-2">
                  <input
                    id={inputId}
                    type="number"
                    inputMode="decimal"
                    step="0.1"
                    min={0}
                    max={assessment.max_score}
                    className="input w-24 text-right"
                    value={value}
                    disabled={!editable}
                    aria-invalid={error ? true : undefined}
                    aria-describedby={error ? `${inputId}-err` : undefined}
                    onChange={(e) => setDraft((prev) => ({ ...prev, [g.student_id]: e.target.value }))}
                  />
                  <span className="w-12 text-xs text-slate-600 dark:text-slate-400">/ {assessment.max_score}</span>
                </div>
                {error && (
                  <p id={`${inputId}-err`} className="mt-1 text-xs font-medium text-red-700 dark:text-red-400">
                    {error}
                  </p>
                )}
              </div>
            </li>
          )
        })}
      </ul>
    </div>
  )
}

export default function GradesPage() {
  const selectId = useId()
  const user = useUser()
  const toast = useToast()
  const queryClient = useQueryClient()
  const years = useAcademicYears()
  const [search, setSearch] = useSearchParams()
  const classId = search.get('class_id') ?? ''
  const assessmentId = search.get('assessment_id') ?? ''
  const [creating, setCreating] = useState(false)

  const setParams = (changes: Record<string, string>) =>
    setSearch((prev) => {
      const next = new URLSearchParams(prev)
      for (const [k, v] of Object.entries(changes)) {
        if (v) next.set(k, v)
        else next.delete(k)
      }
      return next
    })

  const assessments = useQuery({
    queryKey: ['assessments', classId],
    queryFn: () => api.get<Assessment[]>(`/classes/${classId}/assessments`),
    enabled: Boolean(classId),
  })
  const assignments = useQuery({
    queryKey: ['classes', Number(classId), 'assignments'],
    queryFn: () => api.get<Assignment[]>(`/classes/${classId}/assignments`),
    enabled: Boolean(classId),
  })

  const canEdit = (a: { teacher_id: number }) => user.role === 'admin' || a.teacher_id === user.teacher_id
  const myAssignments = (assignments.data ?? []).filter(canEdit)
  const terms = years.data?.[0]?.terms ?? []

  return (
    <>
      <PageHeader
        title="Grades"
        description="Enter and review assessment scores."
        actions={
          classId && myAssignments.length > 0 && <Button onClick={() => setCreating(true)}>New assessment</Button>
        }
      />
      <div className="card mb-4 flex flex-col gap-3 p-4 sm:flex-row sm:items-end">
        <ClassPicker value={classId} onChange={(v) => setParams({ class_id: v, assessment_id: '' })} />
        {classId && (
          <div className="flex min-w-0 flex-1 flex-col gap-1">
            <label htmlFor={selectId} className="text-xs font-medium text-slate-600 dark:text-slate-400">
              Assessment
            </label>
            <select
              id={selectId}
              className="input"
              value={assessmentId}
              onChange={(e) => setParams({ assessment_id: e.target.value })}
              disabled={assessments.isPending}
            >
              <option value="">{assessments.isPending ? 'Loading…' : 'Choose an assessment'}</option>
              {(assessments.data ?? []).map((a) => (
                <option key={a.id} value={a.id}>
                  {a.subject_name} — {a.title} ({a.graded_count} graded)
                </option>
              ))}
            </select>
          </div>
        )}
      </div>

      {!classId ? (
        <div className="card">
          <EmptyState title="Choose a class" description="Pick a class, then an assessment to enter or review grades." />
        </div>
      ) : assessments.isError ? (
        <ErrorState error={assessments.error} onRetry={() => void assessments.refetch()} />
      ) : !assessmentId ? (
        <div className="card">
          <EmptyState
            title={assessments.data?.length === 0 ? 'No assessments yet' : 'Choose an assessment'}
            description={myAssignments.length > 0 ? 'Or create a new assessment for a subject you teach.' : undefined}
          />
        </div>
      ) : (
        <GradeSheetEditor key={assessmentId} assessmentId={Number(assessmentId)} canEdit={canEdit} />
      )}

      <RecordFormDialog<AssessmentFormValues, ReturnType<typeof assessmentSchema.parse>>
        open={creating}
        title="New assessment"
        submitLabel="Create assessment"
        schema={assessmentSchema}
        initial={{
          assignment_id: myAssignments.length === 1 ? String(myAssignments[0]!.id) : '',
          term_id: '',
          title: '',
          kind: 'test',
          max_score: '20',
          weight: '1',
          assessed_on: '',
        }}
        fields={[
          {
            name: 'assignment_id',
            label: 'Subject',
            type: 'select',
            required: true,
            placeholder: 'Choose…',
            options: myAssignments.map((a) => ({ value: a.id, label: a.subject_name })),
          },
          { name: 'term_id', label: 'Term', type: 'select', required: true, placeholder: 'Choose…', options: terms.map((t) => ({ value: t.id, label: t.name })) },
          { name: 'title', label: 'Title', required: true },
          { name: 'kind', label: 'Type', type: 'select', required: true, options: KINDS.map((k) => ({ value: k, label: capitalize(k) })) },
          { name: 'max_score', label: 'Maximum score', type: 'number', required: true },
          { name: 'weight', label: 'Weight', type: 'number', required: true },
          { name: 'assessed_on', label: 'Date', type: 'date', required: true },
        ]}
        onSubmit={async (values) => {
          const created = await api.post<Assessment>('/assessments', values)
          await queryClient.invalidateQueries({ queryKey: ['assessments', classId] })
          setParams({ assessment_id: String(created.id) })
          toast.success('Assessment created')
        }}
        onClose={() => setCreating(false)}
      />
    </>
  )
}
