import { useQuery } from '@tanstack/react-query'
import { lazy, Suspense } from 'react'
import { Link } from 'react-router'
import { EmptyState, ErrorState, LoadingState, PageHeader } from '@/components/ui'
import { api } from '@/lib/api'
import { useUser } from '@/lib/auth'
import type { DashboardSummary } from '@/lib/types'

const AttendanceTrendChart = lazy(() => import('./DashboardCharts').then((m) => ({ default: m.AttendanceTrendChart })))
const GradeDistributionChart = lazy(() => import('./DashboardCharts').then((m) => ({ default: m.GradeDistributionChart })))

function StatTile({ label, value, to }: { label: string; value: number; to?: string }) {
  const body = (
    <>
      <p className="text-sm text-slate-600 dark:text-slate-400">{label}</p>
      <p className="mt-1 text-3xl font-semibold tabular-nums">{value.toLocaleString()}</p>
    </>
  )
  return to ? (
    <Link to={to} className="card block p-4 transition-shadow hover:shadow-md">
      {body}
    </Link>
  ) : (
    <div className="card p-4">{body}</div>
  )
}

function ChartCard({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="card p-4 sm:p-5" aria-labelledby={`${title}-h`}>
      <h2 id={`${title}-h`} className="mb-3 text-base font-semibold">
        {title}
      </h2>
      <Suspense fallback={<LoadingState label="Loading chart…" />}>{children}</Suspense>
    </section>
  )
}

export default function DashboardPage() {
  const user = useUser()
  const query = useQuery({ queryKey: ['dashboard'], queryFn: () => api.get<DashboardSummary>('/dashboard') })

  return (
    <>
      <PageHeader
        title={`Welcome, ${user.full_name.split(' ')[0]}`}
        description={user.role === 'admin' ? 'School overview for the current academic year.' : 'Overview of your classes this academic year.'}
      />
      {query.isPending && <LoadingState />}
      {query.isError && <ErrorState error={query.error} onRetry={() => void query.refetch()} />}
      {query.data && (
        <div className="flex flex-col gap-6">
          <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
            <StatTile label="Students" value={query.data.counts.students} to="/students" />
            <StatTile label="Classes" value={query.data.counts.classes} to="/classes" />
            <StatTile label="Teachers" value={query.data.counts.teachers} to="/teachers" />
            <StatTile label="Staff" value={query.data.counts.staff} to={user.role === 'admin' ? '/staff' : undefined} />
          </div>
          <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
            <ChartCard title="Weekly attendance rate">
              {query.data.attendance_trend.length ? (
                <AttendanceTrendChart data={query.data.attendance_trend} />
              ) : (
                <EmptyState title="No attendance recorded yet" />
              )}
            </ChartCard>
            <ChartCard title="Students by average grade">
              {query.data.grade_distribution.some((b) => b.students > 0) ? (
                <GradeDistributionChart data={query.data.grade_distribution} />
              ) : (
                <EmptyState title="No grades entered yet" />
              )}
            </ChartCard>
          </div>
        </div>
      )}
    </>
  )
}
