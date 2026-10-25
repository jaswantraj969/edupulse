import { keepPreviousData, useQuery } from '@tanstack/react-query'
import { useMemo, useState } from 'react'
import { Link } from 'react-router'
import { DataTable, Pagination, type Column } from '@/components/DataTable'
import { FilterSelect, ListToolbar, SearchBox } from '@/components/ListToolbar'
import { CsvImportDialog } from '@/components/CsvImportDialog'
import { Badge, Button, EmptyState, ErrorState, LoadingState, PageHeader } from '@/components/ui'
import { buttonClass } from '@/components/buttonClass'
import { api, errorMessage } from '@/lib/api'
import { useUser } from '@/lib/auth'
import { capitalize, downloadText, formatDate, fullName, STUDENT_STATUS_TONE } from '@/lib/format'
import { useListState } from '@/lib/hooks'
import { useAllClasses } from '@/lib/queries'
import { useToast } from '@/lib/toast'
import type { Page, Student } from '@/lib/types'

const FILTERS = ['status', 'class_id']
const STATUSES = ['active', 'inactive', 'graduated', 'withdrawn'].map((s) => ({ value: s, label: capitalize(s) }))

export default function StudentsListPage() {
  const user = useUser()
  const toast = useToast()
  const isAdmin = user.role === 'admin'
  const { params, update, toggleSort } = useListState('last_name', FILTERS)
  const classes = useAllClasses()
  const [importOpen, setImportOpen] = useState(false)
  const [exporting, setExporting] = useState(false)

  const query = useQuery({
    queryKey: ['students', params],
    queryFn: () => api.get<Page<Student>>('/students', params),
    placeholderData: keepPreviousData,
  })

  const columns = useMemo<Column<Student>[]>(
    () => [
      {
        key: 'name',
        header: 'Name',
        sortKey: 'last_name',
        render: (s) => (
          <Link to={`/students/${s.id}`} className="font-medium text-indigo-700 hover:underline dark:text-indigo-300">
            {s.last_name}, {s.first_name}
          </Link>
        ),
      },
      { key: 'no', header: 'Student no.', sortKey: 'student_no', render: (s) => <span className="font-mono text-xs">{s.student_no}</span> },
      { key: 'class', header: 'Class', sortKey: 'class_name', render: (s) => s.class_name ?? '—' },
      { key: 'dob', header: 'Date of birth', sortKey: 'date_of_birth', render: (s) => formatDate(s.date_of_birth), hideOnMobile: true },
      {
        key: 'status',
        header: 'Status',
        sortKey: 'status',
        render: (s) => <Badge tone={STUDENT_STATUS_TONE[s.status]}>{capitalize(s.status)}</Badge>,
      },
    ],
    [],
  )

  const exportCsv = async () => {
    setExporting(true)
    try {
      downloadText('students.csv', await api.text('/students/export'))
    } catch (error) {
      toast.error(errorMessage(error))
    } finally {
      setExporting(false)
    }
  }

  return (
    <>
      <PageHeader
        title="Students"
        description={isAdmin ? 'All students in the school.' : 'Students in your classes.'}
        actions={
          <>
            <Button variant="secondary" onClick={() => void exportCsv()} loading={exporting}>
              Export CSV
            </Button>
            {isAdmin && (
              <>
                <Button variant="secondary" onClick={() => setImportOpen(true)}>
                  Import CSV
                </Button>
                <Link to="/students/new" className={buttonClass('primary')}>
                  Add student
                </Link>
              </>
            )}
          </>
        }
      />
      <div className="card overflow-hidden">
        <ListToolbar>
          <SearchBox label="Search" placeholder="Name, number or e-mail" value={params.q ?? ''} onChange={(q) => update({ q })} />
          <FilterSelect label="Status" value={String(params.status ?? '')} onChange={(status) => update({ status })} options={STATUSES} />
          <FilterSelect
            label="Class"
            value={String(params.class_id ?? '')}
            onChange={(class_id) => update({ class_id })}
            options={(classes.data ?? []).map((c) => ({ value: c.id, label: c.name }))}
          />
        </ListToolbar>
        {query.isPending ? (
          <LoadingState />
        ) : query.isError ? (
          <ErrorState error={query.error} onRetry={() => void query.refetch()} />
        ) : query.data.items.length === 0 ? (
          <EmptyState title="No students found" description="Try a different search or clear the filters." />
        ) : (
          <>
            <DataTable
              caption="Students"
              columns={columns}
              rows={query.data.items}
              rowKey={(s) => s.id}
              sort={params.sort}
              order={params.order}
              onSort={toggleSort}
              fetching={query.isFetching}
              mobileTitle={(s) => (
                <Link to={`/students/${s.id}`} className="text-indigo-700 hover:underline dark:text-indigo-300">
                  {fullName(s)}
                </Link>
              )}
            />
            <Pagination page={query.data.page} pageSize={query.data.page_size} total={query.data.total} onPage={(page) => update({ page })} />
          </>
        )}
      </div>
      {isAdmin && <CsvImportDialog open={importOpen} onClose={() => setImportOpen(false)} resource="students" />}
    </>
  )
}
