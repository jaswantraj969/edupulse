import { useQuery } from '@tanstack/react-query'
import { lazy, Suspense, useMemo } from 'react'
import { Link, useParams } from 'react-router'
import { DeferredRender } from '@/components/DeferredRender'
import { BackLink, EmptyState, ErrorState, LoadingState, PageHeader } from '@/components/ui'
import { api } from '@/lib/api'
import { formatDate, fullName, percent } from '@/lib/format'
import type { AttendanceSummary, StudentGrade, StudentRisk } from '@/lib/types'
import { BandBadge, ModelDetails, RiskDisclaimer } from './RiskParts'
import type { TrendPoint } from './RiskTrendCharts'

const TrendChart = lazy(() => import('./RiskTrendCharts'))

function attendanceTrend(summary: AttendanceSummary | undefined): TrendPoint[] {
  return (summary?.by_month ?? []).map((m) => {
    const total = m.present + m.absent + m.late + m.excused
    return { month: m.month, value: total ? (m.present + m.late) / total : 0 }
  })
}

function gradeTrend(grades: StudentGrade[] | undefined): TrendPoint[] {
  const months = new Map<string, number[]>()
  for (const g of grades ?? []) {
    const key = g.assessed_on.slice(0, 7)
    months.set(key, [...(months.get(key) ?? []), g.percentage / 100])
  }
  return [...months.entries()]
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([month, values]) => ({ month, value: values.reduce((s, v) => s + v, 0) / values.length }))
}

export default function StudentRiskPage() {
  const id = Number(useParams().id)
  const risk = useQuery({ queryKey: ['risk', 'student', id], queryFn: () => api.get<StudentRisk>(`/risk/students/${id}`) })
  const attendance = useQuery({ queryKey: ['students', id, 'attendance'], queryFn: () => api.get<AttendanceSummary>(`/students/${id}/attendance`) })
  const grades = useQuery({ queryKey: ['students', id, 'grades'], queryFn: () => api.get<StudentGrade[]>(`/students/${id}/grades`) })
  const attendancePoints = useMemo(() => attendanceTrend(attendance.data), [attendance.data])
  const gradePoints = useMemo(() => gradeTrend(grades.data), [grades.data])

  if (risk.isPending) return <LoadingState />
  if (risk.isError) return <ErrorState error={risk.error} onRetry={() => void risk.refetch()} />
  const r = risk.data
  const asOfMonth = r.as_of ? r.as_of.slice(0, 7) : null
  const scored = r.subjects.filter((x) => x.status === 'scored')

  return (
    <>
      <BackLink to={r.class_id ? `/early-warning?class_id=${r.class_id}` : '/early-warning'}>Early warning</BackLink>
      <PageHeader
        title={fullName(r)}
        description={`${r.student_no}${r.class_name ? ` · Class ${r.class_name}` : ''}${r.as_of ? ` · estimated after first-period grades (${formatDate(r.as_of)})` : ''}`}
        actions={
          <Link to={`/students/${r.student_id}`} className="text-sm font-medium text-indigo-700 hover:underline dark:text-indigo-300">
            Full student record
          </Link>
        }
      />
      <RiskDisclaimer model={r.model} />

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-5">
        <section className="card p-4 sm:p-6 lg:col-span-2" aria-labelledby="estimate-h">
          <h2 id="estimate-h" className="text-base font-semibold">
            Estimate
          </h2>
          {r.status === 'insufficient_data' ? (
            <EmptyState
              title="Not enough data"
              description="An estimate needs at least one Term 1 grade and a current class enrolment."
            />
          ) : (
            <>
              <div className="mt-3 flex items-center gap-3">
                <BandBadge band={r.band} />
                <p className="text-3xl font-semibold tabular-nums">{percent(r.probability)}</p>
              </div>
              <p className="mt-2 text-sm text-slate-600 dark:text-slate-400">
                Highest-risk subject: <span className="font-medium text-slate-900 dark:text-slate-100">{r.top_subject}</span>.
                Estimated chance of failing that subject if nothing changes. Bands: high ≥ {percent(r.model.thresholds.high)},
                medium ≥ {percent(r.model.thresholds.medium)}.
              </p>
              <dl className="mt-4 grid grid-cols-2 gap-2 text-sm">
                <div className="rounded-lg bg-slate-50 p-2 dark:bg-slate-800/60">
                  <dt className="text-xs text-slate-600 dark:text-slate-400">Subjects scored</dt>
                  <dd className="font-semibold tabular-nums">
                    {scored.length} of {r.subjects.length}
                  </dd>
                </div>
                <div className="rounded-lg bg-slate-50 p-2 dark:bg-slate-800/60">
                  <dt className="text-xs text-slate-600 dark:text-slate-400">Past failures</dt>
                  <dd className="font-semibold tabular-nums">{r.subjects[0]?.inputs.failures ?? '—'}</dd>
                </div>
              </dl>
            </>
          )}
        </section>

        <section className="card p-4 sm:p-6 lg:col-span-3" aria-labelledby="subjects-h">
          <h2 id="subjects-h" className="text-base font-semibold">
            Estimate by subject
          </h2>
          {r.subjects.length === 0 ? (
            <p className="mt-3 text-sm text-slate-600 dark:text-slate-400">No subjects available.</p>
          ) : (
            <ol className="mt-3 flex flex-col divide-y divide-slate-200 dark:divide-slate-700">
              {r.subjects.map((subject) => (
                <li key={subject.subject_id} className="py-3 first:pt-0 last:pb-0">
                  <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
                    <h3 className="font-medium">{subject.subject_name}</h3>
                    {subject.status === 'scored' ? (
                      <>
                        <BandBadge band={subject.band} />
                        <span className="text-sm tabular-nums">{percent(subject.probability)}</span>
                        <span className="text-xs text-slate-600 dark:text-slate-400">
                          Term 1 avg {subject.inputs.g1?.toFixed(1)}/20
                        </span>
                      </>
                    ) : (
                      <span className="text-sm text-slate-600 dark:text-slate-400">No Term 1 grades in this subject</span>
                    )}
                  </div>
                  {subject.factors.length > 0 && (
                    <ul className="mt-2 flex flex-col gap-2" aria-label={`What drives the ${subject.subject_name} estimate`}>
                      {subject.factors.map((f) => (
                        <li key={f.feature} className="flex gap-3 text-sm">
                          <span
                            className={`mt-0.5 inline-flex h-6 min-w-16 items-center justify-center rounded-full px-2 text-xs font-semibold ${
                              f.direction === 'raises'
                                ? 'bg-red-100 text-red-900 dark:bg-red-900/50 dark:text-red-200'
                                : 'bg-emerald-100 text-emerald-900 dark:bg-emerald-900/50 dark:text-emerald-200'
                            }`}
                          >
                            {f.direction === 'raises' ? '↑ Raises' : '↓ Lowers'}
                          </span>
                          <span>
                            <span className="font-medium">{f.label}.</span> {f.text}
                          </span>
                        </li>
                      ))}
                    </ul>
                  )}
                </li>
              ))}
            </ol>
          )}
          <p className="mt-4 text-xs text-slate-600 dark:text-slate-400">
            Each subject is scored separately, as the model was trained on one course at a time; the student&apos;s band is
            that of the highest-risk subject. Factors are listed by strength. They describe the model, not the student: talk
            to the student and their teachers before drawing conclusions. The estimate uses only the Term 1 subject average
            and previous failures; attendance is shown below for context but is not part of it.
          </p>
        </section>
      </div>

      <section className="card mt-6 p-4 sm:p-6" aria-labelledby="trend-h">
        <h2 id="trend-h" className="mb-4 text-base font-semibold">
          Attendance and grade trend
        </h2>
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
          <Suspense fallback={<LoadingState label="Loading chart…" />}>
            {attendance.isError ? (
              <ErrorState error={attendance.error} />
            ) : attendancePoints.length ? (
              <DeferredRender minHeight="16rem" label="Attendance chart">
                <TrendChart title="Attendance rate by month" seriesName="Attendance" data={attendancePoints} asOfMonth={asOfMonth} floor={0.5} />
              </DeferredRender>
            ) : (
              <EmptyState title={attendance.isPending ? 'Loading attendance…' : 'No attendance recorded'} />
            )}
            {grades.isError ? (
              <ErrorState error={grades.error} />
            ) : gradePoints.length ? (
              <DeferredRender minHeight="16rem" label="Grade chart">
                <TrendChart title="Average grade by month" seriesName="Average grade" data={gradePoints} asOfMonth={asOfMonth} />
              </DeferredRender>
            ) : (
              <EmptyState title={grades.isPending ? 'Loading grades…' : 'No grades recorded'} />
            )}
          </Suspense>
        </div>
      </section>
      <ModelDetails model={r.model} />
    </>
  )
}
