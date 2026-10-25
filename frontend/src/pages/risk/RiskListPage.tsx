import { keepPreviousData, useQuery } from '@tanstack/react-query'
import { useMemo, useState } from 'react'
import { Link, useSearchParams } from 'react-router'
import { DataTable, type Column } from '@/components/DataTable'
import { Button, EmptyState, ErrorState, LoadingState, PageHeader } from '@/components/ui'
import { api, errorMessage } from '@/lib/api'
import { downloadText, formatDate, fullName, percent } from '@/lib/format'
import { useToast } from '@/lib/toast'
import type { ClassRisk, StudentRiskRow } from '@/lib/types'
import { ClassPicker } from '../records/ClassPicker'
import { BandBadge, ModelDetails, RiskDisclaimer } from './RiskParts'

export default function RiskListPage() {
  const toast = useToast()
  const [search, setSearch] = useSearchParams()
  const classId = search.get('class_id') ?? ''
  const sort = search.get('sort') === 'name' ? 'name' : 'probability'
  const order = search.get('order') === 'asc' ? 'asc' : 'desc'
  const [exporting, setExporting] = useState(false)

  const update = (changes: Record<string, string>) =>
    setSearch((prev) => {
      const next = new URLSearchParams(prev)
      for (const [k, v] of Object.entries(changes)) {
        if (v) next.set(k, v)
        else next.delete(k)
      }
      return next
    })

  const query = useQuery({
    queryKey: ['risk', 'class', classId, sort, order],
    queryFn: () => api.get<ClassRisk>(`/risk/classes/${classId}`, { sort, order }),
    enabled: Boolean(classId),
    placeholderData: keepPreviousData,
  })

  const columns = useMemo<Column<StudentRiskRow>[]>(
    () => [
      {
        key: 'name',
        header: 'Student',
        sortKey: 'name',
        render: (r) => (
          <Link to={`/early-warning/students/${r.student_id}`} className="font-medium text-indigo-700 hover:underline dark:text-indigo-300">
            {r.last_name}, {r.first_name}
          </Link>
        ),
      },
      { key: 'band', header: 'Band', render: (r) => <BandBadge band={r.band} /> },
      {
        key: 'probability',
        header: 'Estimate',
        sortKey: 'probability',
        render: (r) => <span className="tabular-nums">{percent(r.probability)}</span>,
      },
      {
        key: 'subject',
        header: 'Highest-risk subject',
        render: (r) => r.top_subject ?? '—',
      },
      {
        key: 'g1',
        header: 'Term 1 avg (subject)',
        render: (r) => (r.inputs?.g1 == null ? '—' : `${r.inputs.g1.toFixed(1)}/20`),
        hideOnMobile: true,
      },
      {
        key: 'factor',
        header: 'Main factor',
        render: (r) => (
          <span className="text-slate-700 dark:text-slate-300">
            {r.status === 'insufficient_data' ? 'No Term 1 grades yet' : r.top_factor}
          </span>
        ),
        className: 'max-w-md whitespace-normal',
      },
    ],
    [],
  )

  const exportCsv = async () => {
    setExporting(true)
    try {
      const name = query.data?.class_name ?? classId
      downloadText(`risk-${name}.csv`, await api.text(`/risk/classes/${classId}/export`))
      toast.info('Export recorded in the audit log')
    } catch (error) {
      toast.error(errorMessage(error))
    } finally {
      setExporting(false)
    }
  }

  const counts = query.data?.students.reduce<Record<string, number>>((acc, s) => {
    const key = s.band ?? 'unscored'
    acc[key] = (acc[key] ?? 0) + 1
    return acc
  }, {})

  return (
    <>
      <PageHeader
        title="Early warning"
        description="Students who may need support, estimated per subject after first-period (Term 1) grades. Each student is shown with their highest-risk subject."
        actions={
          classId && (
            <Button variant="secondary" onClick={() => void exportCsv()} loading={exporting} disabled={!query.data}>
              Export CSV
            </Button>
          )
        }
      />
      {query.data && <RiskDisclaimer model={query.data.model} />}
      <div className="card mb-4 flex flex-col gap-3 p-4 sm:flex-row sm:items-end sm:justify-between">
        <ClassPicker value={classId} onChange={(v) => update({ class_id: v })} />
        {query.data && counts && (
          <p className="text-sm text-slate-600 dark:text-slate-400" aria-live="polite">
            As of {formatDate(query.data.as_of)} · {counts.high ?? 0} high · {counts.medium ?? 0} medium · {counts.low ?? 0} low
            {counts.unscored ? ` · ${counts.unscored} not scored` : ''}
          </p>
        )}
      </div>
      {!classId ? (
        <div className="card">
          <EmptyState title="Choose a class" description="Pick one of your classes to see its early-warning list." />
        </div>
      ) : query.isPending ? (
        <LoadingState />
      ) : query.isError ? (
        <ErrorState error={query.error} onRetry={() => void query.refetch()} />
      ) : query.data.students.length === 0 ? (
        <div className="card">
          <EmptyState title="No students in this class" />
        </div>
      ) : (
        <>
          <div className="card overflow-hidden">
            <DataTable
              caption={`Early-warning list for ${query.data.class_name}`}
              columns={columns}
              rows={query.data.students}
              rowKey={(r) => r.student_id}
              sort={sort}
              order={order}
              onSort={(key) => update({ sort: key, order: sort === key && order === 'desc' ? 'asc' : 'desc' })}
              fetching={query.isFetching}
              mobileTitle={(r) => (
                <Link to={`/early-warning/students/${r.student_id}`} className="text-indigo-700 hover:underline dark:text-indigo-300">
                  {fullName(r)}
                </Link>
              )}
            />
          </div>
          <ModelDetails model={query.data.model} />
        </>
      )}
    </>
  )
}
