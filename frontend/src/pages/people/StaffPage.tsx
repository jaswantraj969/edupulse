import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useMemo, useState } from 'react'
import { CsvImportDialog } from '@/components/CsvImportDialog'
import { DataTable, Pagination, type Column } from '@/components/DataTable'
import { ConfirmDialog } from '@/components/Dialog'
import { FilterSelect, ListToolbar, SearchBox } from '@/components/ListToolbar'
import { RecordFormDialog, type FieldSpec } from '@/components/RecordFormDialog'
import { Badge, Button, EmptyState, ErrorState, LoadingState, PageHeader } from '@/components/ui'
import { api, errorMessage } from '@/lib/api'
import { downloadText, formatDate, fullName } from '@/lib/format'
import { useListState } from '@/lib/hooks'
import { useToast } from '@/lib/toast'
import type { Page, StaffMember } from '@/lib/types'
import { staffSchema, type StaffFormValues } from './schemas'

const FILTERS = ['department']
const DEPARTMENTS = ['Administration', 'Facilities', 'Finance', 'Health', 'IT', 'Library', 'Science', 'Student Services']
const FIELDS: FieldSpec<StaffFormValues>[] = [
  { name: 'employee_no', label: 'Employee number', required: true },
  { name: 'job_title', label: 'Job title', required: true },
  { name: 'first_name', label: 'First name', required: true },
  { name: 'last_name', label: 'Last name', required: true },
  { name: 'email', label: 'E-mail', type: 'email', required: true },
  { name: 'phone', label: 'Phone', type: 'tel' },
  { name: 'department', label: 'Department', required: true },
  { name: 'hire_date', label: 'Hire date', type: 'date', required: true },
  { name: 'is_active', label: 'Active', type: 'checkbox' },
]
const EMPTY: StaffFormValues = {
  employee_no: '',
  first_name: '',
  last_name: '',
  email: '',
  phone: '',
  job_title: '',
  department: '',
  hire_date: '',
  is_active: true,
}

export default function StaffPage() {
  const toast = useToast()
  const queryClient = useQueryClient()
  const { params, update, toggleSort } = useListState('last_name', FILTERS)
  const [editing, setEditing] = useState<StaffMember | 'new' | null>(null)
  const [deleting, setDeleting] = useState<StaffMember | null>(null)
  const [importOpen, setImportOpen] = useState(false)

  const query = useQuery({
    queryKey: ['staff', params],
    queryFn: () => api.get<Page<StaffMember>>('/staff', params),
    placeholderData: keepPreviousData,
  })
  const invalidate = () => queryClient.invalidateQueries({ queryKey: ['staff'] })
  const remove = useMutation({
    mutationFn: (id: number) => api.delete(`/staff/${id}`),
    onSuccess: async () => {
      await invalidate()
      toast.success('Staff member deleted')
    },
    onError: (error) => toast.error(errorMessage(error)),
    onSettled: () => setDeleting(null),
  })

  const columns = useMemo<Column<StaffMember>[]>(
    () => [
      { key: 'name', header: 'Name', sortKey: 'last_name', render: (m) => <span className="font-medium">{m.last_name}, {m.first_name}</span> },
      { key: 'title', header: 'Job title', sortKey: 'job_title', render: (m) => m.job_title },
      { key: 'dept', header: 'Department', sortKey: 'department', render: (m) => m.department },
      { key: 'email', header: 'E-mail', render: (m) => m.email, hideOnMobile: true },
      { key: 'hired', header: 'Hired', sortKey: 'hire_date', render: (m) => formatDate(m.hire_date), hideOnMobile: true },
      { key: 'status', header: 'Status', render: (m) => <Badge tone={m.is_active ? 'green' : 'slate'}>{m.is_active ? 'Active' : 'Inactive'}</Badge> },
      {
        key: 'actions',
        header: 'Actions',
        render: (m) => (
          <span className="flex gap-1">
            <Button variant="ghost" className="min-h-8 px-2 py-1" onClick={() => setEditing(m)} aria-label={`Edit ${fullName(m)}`}>
              Edit
            </Button>
            <Button variant="ghost" className="min-h-8 px-2 py-1 text-red-700 dark:text-red-400" onClick={() => setDeleting(m)} aria-label={`Delete ${fullName(m)}`}>
              Delete
            </Button>
          </span>
        ),
      },
    ],
    [],
  )

  const save = async (values: ReturnType<typeof staffSchema.parse>) => {
    if (editing === 'new') await api.post('/staff', values)
    else if (editing) await api.patch(`/staff/${editing.id}`, values)
    await invalidate()
    toast.success(editing === 'new' ? 'Staff member added' : 'Changes saved')
  }

  return (
    <>
      <PageHeader
        title="Staff"
        description="Non-teaching staff."
        actions={
          <>
            <Button variant="secondary" onClick={() => void api.text('/staff/export').then((t) => downloadText('staff.csv', t), (e) => toast.error(errorMessage(e)))}>
              Export CSV
            </Button>
            <Button variant="secondary" onClick={() => setImportOpen(true)}>
              Import CSV
            </Button>
            <Button onClick={() => setEditing('new')}>Add staff member</Button>
          </>
        }
      />
      <div className="card overflow-hidden">
        <ListToolbar>
          <SearchBox label="Search" placeholder="Name, number, e-mail or title" value={params.q ?? ''} onChange={(q) => update({ q })} />
          <FilterSelect
            label="Department"
            value={String(params.department ?? '')}
            onChange={(department) => update({ department })}
            options={DEPARTMENTS.map((d) => ({ value: d, label: d }))}
          />
        </ListToolbar>
        {query.isPending ? (
          <LoadingState />
        ) : query.isError ? (
          <ErrorState error={query.error} onRetry={() => void query.refetch()} />
        ) : query.data.items.length === 0 ? (
          <EmptyState title="No staff found" />
        ) : (
          <>
            <DataTable
              caption="Staff"
              columns={columns}
              rows={query.data.items}
              rowKey={(m) => m.id}
              sort={params.sort}
              order={params.order}
              onSort={toggleSort}
              fetching={query.isFetching}
              mobileTitle={(m) => fullName(m)}
            />
            <Pagination page={query.data.page} pageSize={query.data.page_size} total={query.data.total} onPage={(page) => update({ page })} />
          </>
        )}
      </div>
      <RecordFormDialog
        open={editing !== null}
        title={editing === 'new' ? 'Add staff member' : 'Edit staff member'}
        submitLabel={editing === 'new' ? 'Add staff member' : 'Save changes'}
        schema={staffSchema}
        initial={editing && editing !== 'new' ? { ...editing, phone: editing.phone ?? '' } : EMPTY}
        fields={FIELDS}
        onSubmit={save}
        onClose={() => setEditing(null)}
      />
      <ConfirmDialog
        open={deleting !== null}
        title="Delete staff member?"
        message={<>Permanently delete <strong>{deleting ? fullName(deleting) : ''}</strong>?</>}
        confirmLabel="Delete"
        danger
        loading={remove.isPending}
        onConfirm={() => deleting && remove.mutate(deleting.id)}
        onCancel={() => setDeleting(null)}
      />
      <CsvImportDialog open={importOpen} onClose={() => setImportOpen(false)} resource="staff" />
    </>
  )
}
