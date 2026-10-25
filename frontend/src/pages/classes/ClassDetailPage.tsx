import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router'
import { ConfirmDialog } from '@/components/Dialog'
import { RecordFormDialog } from '@/components/RecordFormDialog'
import { BackLink, Button, DefinitionList, EmptyState, ErrorState, LoadingState, PageHeader } from '@/components/ui'
import { buttonClass } from '@/components/buttonClass'
import { api, errorMessage } from '@/lib/api'
import { useUser } from '@/lib/auth'
import { fullName } from '@/lib/format'
import { useAllTeachers } from '@/lib/queries'
import { useToast } from '@/lib/toast'
import type { Assignment, ClassGroup, StudentBrief } from '@/lib/types'
import { classSchema, type ClassFormValues } from './classSchema'

export default function ClassDetailPage() {
  const id = Number(useParams().id)
  const user = useUser()
  const isAdmin = user.role === 'admin'
  const navigate = useNavigate()
  const toast = useToast()
  const queryClient = useQueryClient()
  const teachers = useAllTeachers()
  const [editing, setEditing] = useState(false)
  const [deleting, setDeleting] = useState(false)

  const cls = useQuery({ queryKey: ['classes', id], queryFn: () => api.get<ClassGroup>(`/classes/${id}`) })
  const roster = useQuery({ queryKey: ['classes', id, 'students'], queryFn: () => api.get<StudentBrief[]>(`/classes/${id}/students`) })
  const assignments = useQuery({ queryKey: ['classes', id, 'assignments'], queryFn: () => api.get<Assignment[]>(`/classes/${id}/assignments`) })
  const remove = useMutation({
    mutationFn: () => api.delete(`/classes/${id}`),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['classes'] })
      toast.success('Class deleted')
      navigate('/classes')
    },
    onError: (error) => {
      setDeleting(false)
      toast.error(errorMessage(error))
    },
  })

  if (cls.isPending) return <LoadingState />
  if (cls.isError) return <ErrorState error={cls.error} onRetry={() => void cls.refetch()} />
  const c = cls.data

  return (
    <>
      <BackLink to="/classes">Classes</BackLink>
      <PageHeader
        title={`Class ${c.name}`}
        description={`${c.academic_year} · ${c.student_count} students`}
        actions={
          <>
            <Link to={`/attendance?class_id=${id}`} className={buttonClass('secondary')}>
              Mark attendance
            </Link>
            <Link to={`/grades?class_id=${id}`} className={buttonClass('secondary')}>
              Grades
            </Link>
            {isAdmin && (
              <>
                <Button variant="secondary" onClick={() => setEditing(true)}>
                  Edit
                </Button>
                <Button variant="danger" onClick={() => setDeleting(true)}>
                  Delete
                </Button>
              </>
            )}
          </>
        }
      />
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <section className="card p-4 sm:p-6 lg:col-span-1" aria-label="Class details">
          <DefinitionList
            items={[
              ['Grade', c.grade_level],
              ['Section', c.section],
              ['Room', c.room],
              ['Homeroom teacher', c.homeroom_teacher_name],
            ]}
          />
          <h2 className="mt-6 mb-2 text-base font-semibold">Subjects</h2>
          {assignments.isPending ? (
            <LoadingState />
          ) : assignments.isError ? (
            <ErrorState error={assignments.error} />
          ) : assignments.data.length === 0 ? (
            <p className="text-sm text-slate-600 dark:text-slate-400">No subjects assigned.</p>
          ) : (
            <ul className="divide-y divide-slate-100 text-sm dark:divide-slate-800">
              {assignments.data.map((a) => (
                <li key={a.id} className="flex justify-between gap-3 py-2">
                  <span>{a.subject_name}</span>
                  <span className="text-right text-slate-600 dark:text-slate-400">{a.teacher_name}</span>
                </li>
              ))}
            </ul>
          )}
        </section>
        <section className="card p-4 sm:p-6 lg:col-span-2" aria-labelledby="roster-h">
          <h2 id="roster-h" className="mb-3 text-base font-semibold">
            Students
          </h2>
          {roster.isPending ? (
            <LoadingState />
          ) : roster.isError ? (
            <ErrorState error={roster.error} onRetry={() => void roster.refetch()} />
          ) : roster.data.length === 0 ? (
            <EmptyState title="No students enrolled" />
          ) : (
            <ol className="grid grid-cols-1 gap-x-6 text-sm sm:grid-cols-2">
              {roster.data.map((s) => (
                <li key={s.id} className="flex items-center justify-between gap-3 border-b border-slate-100 py-2 dark:border-slate-800">
                  <Link to={`/students/${s.id}`} className="text-indigo-700 hover:underline dark:text-indigo-300">
                    {s.last_name}, {s.first_name}
                  </Link>
                  <span className="font-mono text-xs text-slate-600 dark:text-slate-400">{s.student_no}</span>
                </li>
              ))}
            </ol>
          )}
        </section>
      </div>
      {isAdmin && (
        <>
          <RecordFormDialog<ClassFormValues, ReturnType<typeof classSchema.parse>>
            open={editing}
            title={`Edit class ${c.name}`}
            submitLabel="Save changes"
            schema={classSchema}
            initial={{
              academic_year_id: String(c.academic_year_id),
              grade_level: String(c.grade_level),
              section: c.section,
              room: c.room ?? '',
              homeroom_teacher_id: c.homeroom_teacher_id ? String(c.homeroom_teacher_id) : '',
            }}
            fields={[
              { name: 'grade_level', label: 'Grade', type: 'number', required: true },
              { name: 'section', label: 'Section', required: true },
              { name: 'room', label: 'Room' },
              {
                name: 'homeroom_teacher_id',
                label: 'Homeroom teacher',
                type: 'select',
                placeholder: 'None',
                options: (teachers.data ?? []).map((t) => ({ value: t.id, label: fullName(t) })),
              },
            ]}
            onSubmit={async ({ academic_year_id: _year, ...changes }) => {
              await api.patch(`/classes/${id}`, changes)
              await queryClient.invalidateQueries({ queryKey: ['classes'] })
              toast.success('Class updated')
            }}
            onClose={() => setEditing(false)}
          />
          <ConfirmDialog
            open={deleting}
            title={`Delete class ${c.name}?`}
            message="Only classes without enrolled students can be deleted. Its subjects and assessments are removed too."
            confirmLabel="Delete class"
            danger
            loading={remove.isPending}
            onConfirm={() => remove.mutate()}
            onCancel={() => setDeleting(false)}
          />
        </>
      )}
    </>
  )
}
