import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useMemo, useState } from 'react'
import { CsvImportDialog } from '@/components/CsvImportDialog'
import { DataTable, Pagination, type Column } from '@/components/DataTable'
import { ConfirmDialog } from '@/components/Dialog'
import { FilterSelect, ListToolbar, SearchBox } from '@/components/ListToolbar'
import { RecordFormDialog, type FieldSpec } from '@/components/RecordFormDialog'
import { Badge, Button, EmptyState, ErrorState, LoadingState, PageHeader } from '@/components/ui'
import { api, errorMessage } from '@/lib/api'
import { useUser } from '@/lib/auth'
import { downloadText, formatDate, fullName } from '@/lib/format'
import { useListState } from '@/lib/hooks'
import { useToast } from '@/lib/toast'
import type { Page, Teacher } from '@/lib/types'
import { teacherSchema, type TeacherFormValues } from './schemas'
import { useDemoLock } from '@/lib/meta'

const FILTERS = ['is_active']
const FIELDS: FieldSpec<TeacherFormValues>[] = [
  { name: 'employee_no', label: 'Employee number', required: true },
  { name: 'specialization', label: 'Specialisation' },
  { name: 'first_name', label: 'First name', required: true },
  { name: 'last_name', label: 'Last name', required: true },
  { name: 'email', label: 'E-mail', type: 'email', required: true },
  { name: 'phone', label: 'Phone', type: 'tel' },
  { name: 'hire_date', label: 'Hire date', type: 'date', required: true },
  { name: 'is_active', label: 'Active', type: 'checkbox' },
]
const EMPTY: TeacherFormValues = {
  employee_no: '',
  first_name: '',
  last_name: '',
  email: '',
  phone: '',
  hire_date: '',
  specialization: '',
  is_active: true,
}

function toValues(t: Teacher): TeacherFormValues {
  return { ...t, phone: t.phone ?? '', specialization: t.specialization ?? '' }
}

export default function TeachersPage() {
  const lock = useDemoLock()
  const user = useUser()
  const isAdmin = user.role === 'admin'
  const toast = useToast()
  const queryClient = useQueryClient()
  const { params, update, toggleSort } = useListState('last_name', FILTERS)
  const [editing, setEditing] = useState<Teacher | 'new' | null>(null)
  const [deleting, setDeleting] = useState<Teacher | null>(null)
  const [importOpen, setImportOpen] = useState(false)

  const query = useQuery({
    queryKey: ['teachers', params],
    queryFn: () => api.get<Page<Teacher>>('/teachers', params),
    placeholderData: keepPreviousData,
  })
  const invalidate = () => queryClient.invalidateQueries({ queryKey: ['teachers'] })
  const remove = useMutation({
    mutationFn: (id: number) => api.delete(`/teachers/${id}`),
    onSuccess: async () => {
      await invalidate()
      toast.success('Teacher deleted')
    },
    onError: (error) => toast.error(errorMessage(error)),
    onSettled: () => setDeleting(null),
  })

  const columns = useMemo<Column<Teacher>[]>(() => {
    const cols: Column<Teacher>[] = [
      { key: 'name', header: 'Name', sortKey: 'last_name', render: (t) => <span className="font-medium">{t.last_name}, {t.first_name}</span> },
      { key: 'no', header: 'Employee no.', sortKey: 'employee_no', render: (t) => <span className="font-mono text-xs">{t.employee_no}</span> },
      { key: 'spec', header: 'Specialisation', sortKey: 'specialization', render: (t) => t.specialization ?? '—' },
      { key: 'email', header: 'E-mail', render: (t) => t.email, hideOnMobile: true },
      { key: 'hired', header: 'Hired', sortKey: 'hire_date', render: (t) => formatDate(t.hire_date), hideOnMobile: true },
      { key: 'status', header: 'Status', render: (t) => <Badge tone={t.is_active ? 'green' : 'slate'}>{t.is_active ? 'Active' : 'Inactive'}</Badge> },
    ]
    if (isAdmin) {
      cols.push({
        key: 'actions',
        header: 'Actions',
        render: (t) => (
          <span className="flex gap-1">
            <Button variant="ghost" className="min-h-8 px-2 py-1" onClick={() => setEditing(t)} aria-label={`Edit ${fullName(t)}`}>
              Edit
            </Button>
            <Button variant="ghost" className="min-h-8 px-2 py-1 text-red-700 dark:text-red-400" onClick={() => setDeleting(t)} aria-label={`Delete ${fullName(t)}`} {...lock}>
              Delete
            </Button>
          </span>
        ),
      })
    }
    return cols
  }, [isAdmin, lock])

  const save = async (values: ReturnType<typeof teacherSchema.parse>) => {
    if (editing === 'new') await api.post('/teachers', values)
    else if (editing) await api.patch(`/teachers/${editing.id}`, values)
    await invalidate()
    toast.success(editing === 'new' ? 'Teacher added' : 'Changes saved')
  }

  return (
    <>
      <PageHeader
        title="Teachers"
        description="Teaching staff directory."
        actions={
          isAdmin && (
            <>
              <Button variant="secondary" onClick={() => void api.text('/teachers/export').then((t) => downloadText('teachers.csv', t), (e) => toast.error(errorMessage(e)))}>
                Export CSV
              </Button>
              <Button variant="secondary" onClick={() => setImportOpen(true)} {...lock}>
                Import CSV
              </Button>
              <Button onClick={() => setEditing('new')}>Add teacher</Button>
            </>
          )
        }
      />
      <div className="card overflow-hidden">
        <ListToolbar>
          <SearchBox label="Search" placeholder="Name, number or e-mail" value={params.q ?? ''} onChange={(q) => update({ q })} />
          <FilterSelect
            label="Status"
            value={String(params.is_active ?? '')}
            onChange={(is_active) => update({ is_active })}
            options={[
              { value: 'true', label: 'Active' },
              { value: 'false', label: 'Inactive' },
            ]}
          />
        </ListToolbar>
        {query.isPending ? (
          <LoadingState />
        ) : query.isError ? (
          <ErrorState error={query.error} onRetry={() => void query.refetch()} />
        ) : query.data.items.length === 0 ? (
          <EmptyState title="No teachers found" />
        ) : (
          <>
            <DataTable
              caption="Teachers"
              columns={columns}
              rows={query.data.items}
              rowKey={(t) => t.id}
              sort={params.sort}
              order={params.order}
              onSort={toggleSort}
              fetching={query.isFetching}
              mobileTitle={(t) => fullName(t)}
            />
            <Pagination page={query.data.page} pageSize={query.data.page_size} total={query.data.total} onPage={(page) => update({ page })} />
          </>
        )}
      </div>
      {isAdmin && (
        <>
          <RecordFormDialog
            open={editing !== null}
            title={editing === 'new' ? 'Add teacher' : 'Edit teacher'}
            submitLabel={editing === 'new' ? 'Add teacher' : 'Save changes'}
            schema={teacherSchema}
            initial={editing && editing !== 'new' ? toValues(editing) : EMPTY}
            fields={FIELDS}
            onSubmit={save}
            onClose={() => setEditing(null)}
          />
          <ConfirmDialog
            open={deleting !== null}
            title="Delete teacher?"
            message={
              <>
                Delete <strong>{deleting ? fullName(deleting) : ''}</strong>? Their login account is removed too. Teachers who
                still teach classes cannot be deleted.
              </>
            }
            confirmLabel="Delete teacher"
            danger
            loading={remove.isPending}
            onConfirm={() => deleting && remove.mutate(deleting.id)}
            onCancel={() => setDeleting(null)}
          />
          <CsvImportDialog open={importOpen} onClose={() => setImportOpen(false)} resource="teachers" />
        </>
      )}
    </>
  )
}
