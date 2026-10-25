import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router'
import { ConfirmDialog } from '@/components/Dialog'
import { BackLink, Badge, Button, DefinitionList, EmptyState, ErrorState, LoadingState, PageHeader } from '@/components/ui'
import { buttonClass } from '@/components/buttonClass'
import { api, errorMessage } from '@/lib/api'
import { useUser } from '@/lib/auth'
import { capitalize, formatDate, fullName, STUDENT_STATUS_TONE } from '@/lib/format'
import { useToast } from '@/lib/toast'
import type { AttendanceSummary, Student, StudentGrade } from '@/lib/types'

function AttendanceCard({ id }: { id: number }) {
  const query = useQuery({ queryKey: ['students', id, 'attendance'], queryFn: () => api.get<AttendanceSummary>(`/students/${id}/attendance`) })
  return (
    <section className="card p-4 sm:p-6" aria-labelledby="att-h">
      <h2 id="att-h" className="mb-4 text-base font-semibold">Attendance</h2>
      {query.isPending ? (
        <LoadingState />
      ) : query.isError ? (
        <ErrorState error={query.error} onRetry={() => void query.refetch()} />
      ) : query.data.total === 0 ? (
        <EmptyState title="No attendance recorded" />
      ) : (
        <dl className="grid grid-cols-2 gap-3 sm:grid-cols-5">
          {(
            [
              ['Rate', query.data.attendance_rate === null ? '—' : `${(query.data.attendance_rate * 100).toFixed(1)}%`],
              ['Present', query.data.present],
              ['Absent', query.data.absent],
              ['Late', query.data.late],
              ['Excused', query.data.excused],
            ] as const
          ).map(([label, value]) => (
            <div key={label} className="rounded-lg bg-slate-50 p-3 dark:bg-slate-800/60">
              <dt className="text-xs text-slate-600 dark:text-slate-400">{label}</dt>
              <dd className="text-xl font-semibold tabular-nums">{value}</dd>
            </div>
          ))}
        </dl>
      )}
    </section>
  )
}

function GradesCard({ id }: { id: number }) {
  const query = useQuery({ queryKey: ['students', id, 'grades'], queryFn: () => api.get<StudentGrade[]>(`/students/${id}/grades`) })
  return (
    <section className="card p-4 sm:p-6" aria-labelledby="grades-h">
      <h2 id="grades-h" className="mb-4 text-base font-semibold">Grades</h2>
      {query.isPending ? (
        <LoadingState />
      ) : query.isError ? (
        <ErrorState error={query.error} onRetry={() => void query.refetch()} />
      ) : query.data.length === 0 ? (
        <EmptyState title="No grades yet" />
      ) : (
        <div className="max-h-96 overflow-auto">
          <table className="w-full text-left text-sm">
            <caption className="sr-only">Grades by assessment</caption>
            <thead className="sticky top-0 bg-white text-xs text-slate-600 uppercase dark:bg-slate-900 dark:text-slate-400">
              <tr>
                <th scope="col" className="py-2 pr-3">Subject</th>
                <th scope="col" className="py-2 pr-3">Assessment</th>
                <th scope="col" className="hidden py-2 pr-3 sm:table-cell">Date</th>
                <th scope="col" className="py-2 text-right">Score</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
              {query.data.map((g) => (
                <tr key={g.assessment_id}>
                  <td className="py-2 pr-3">{g.subject_name}</td>
                  <td className="py-2 pr-3">{g.title}</td>
                  <td className="hidden py-2 pr-3 sm:table-cell">{formatDate(g.assessed_on)}</td>
                  <td className="py-2 text-right tabular-nums">
                    {g.score}/{g.max_score} <span className="text-slate-600 dark:text-slate-400">({g.percentage}%)</span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  )
}

export default function StudentDetailPage() {
  const id = Number(useParams().id)
  const user = useUser()
  const navigate = useNavigate()
  const toast = useToast()
  const queryClient = useQueryClient()
  const [confirming, setConfirming] = useState(false)
  const query = useQuery({ queryKey: ['students', id], queryFn: () => api.get<Student>(`/students/${id}`) })
  const remove = useMutation({
    mutationFn: () => api.delete(`/students/${id}`),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['students'] })
      toast.success('Student deleted')
      navigate('/students')
    },
    onError: (error) => {
      setConfirming(false)
      toast.error(errorMessage(error))
    },
  })

  if (query.isPending) return <LoadingState />
  if (query.isError) return <ErrorState error={query.error} onRetry={() => void query.refetch()} />
  const s = query.data
  return (
    <>
      <BackLink to="/students">Students</BackLink>
      <PageHeader
        title={fullName(s)}
        description={`${s.student_no}${s.class_name ? ` · Class ${s.class_name}` : ''}`}
        actions={
          <>
            <Link to={`/early-warning/students/${id}`} className={buttonClass('secondary')}>
              Early warning
            </Link>
            {user.role === 'admin' && (
            <>
              <Link to={`/students/${id}/edit`} className={buttonClass('secondary')}>
                Edit
              </Link>
              <Button variant="danger" onClick={() => setConfirming(true)}>
                Delete
              </Button>
            </>
            )}
          </>
        }
      />
      <div className="flex flex-col gap-6">
        <section className="card p-4 sm:p-6" aria-label="Profile">
          <DefinitionList
            items={[
              ['Status', <Badge key="s" tone={STUDENT_STATUS_TONE[s.status]}>{capitalize(s.status)}</Badge>],
              ['Class', s.class_id ? <Link key="c" className="text-indigo-700 hover:underline dark:text-indigo-300" to={`/classes/${s.class_id}`}>{s.class_name}</Link> : '—'],
              ['Date of birth', formatDate(s.date_of_birth)],
              ['Enrolled on', formatDate(s.enrolled_on)],
              ['E-mail', s.email],
              ['Phone', s.phone],
              ['Guardian', s.guardian_name],
              ['Guardian phone', s.guardian_phone],
              ['Prior year failures', s.prior_failures],
            ]}
          />
        </section>
        <AttendanceCard id={id} />
        <GradesCard id={id} />
      </div>
      <ConfirmDialog
        open={confirming}
        title="Delete student?"
        message={
          <>
            This permanently deletes <strong>{fullName(s)}</strong> together with their attendance and grades. This cannot
            be undone.
          </>
        }
        confirmLabel="Delete student"
        danger
        loading={remove.isPending}
        onConfirm={() => remove.mutate()}
        onCancel={() => setConfirming(false)}
      />
    </>
  )
}
