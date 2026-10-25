import { keepPreviousData, useQuery } from '@tanstack/react-query'
import { useMemo } from 'react'
import { DataTable, Pagination, type Column } from '@/components/DataTable'
import { FilterSelect, ListToolbar, SearchBox } from '@/components/ListToolbar'
import { EmptyState, ErrorState, LoadingState, PageHeader } from '@/components/ui'
import { api } from '@/lib/api'
import { useListState } from '@/lib/hooks'
import type { AuditLogEntry, Page } from '@/lib/types'

const FILTERS = ['action']
const ACTIONS: Record<AuditLogEntry['action'], string> = {
  'risk.view_class': 'Viewed class risk list',
  'risk.view_student': 'Viewed student risk panel',
  'risk.export_class': 'Exported class risk list',
  'account.approve': 'Approved account request',
  'account.reject': 'Rejected account request',
}

export default function AuditLogPage() {
  const { params, update, toggleSort } = useListState('created_at', FILTERS, 25, 'desc')
  const query = useQuery({
    queryKey: ['audit-logs', params],
    queryFn: () => api.get<Page<AuditLogEntry>>('/audit-logs', params),
    placeholderData: keepPreviousData,
  })
  const columns = useMemo<Column<AuditLogEntry>[]>(
    () => [
      {
        key: 'when',
        header: 'When',
        sortKey: 'created_at',
        render: (e) => <time dateTime={e.created_at}>{new Date(e.created_at).toLocaleString()}</time>,
      },
      { key: 'who', header: 'User', sortKey: 'user_email', render: (e) => e.user_email },
      { key: 'what', header: 'Action', render: (e) => ACTIONS[e.action] },
      { key: 'target', header: 'Target', render: (e) => `${e.target_type} ${e.detail ?? e.target_id}` },
      { key: 'ip', header: 'IP address', render: (e) => e.ip_address ?? '—', hideOnMobile: true },
    ],
    [],
  )
  return (
    <>
      <PageHeader title="Audit log" description="Who viewed or exported early-warning scores." />
      <div className="card overflow-hidden">
        <ListToolbar>
          <SearchBox label="Search" placeholder="User e-mail or target" value={params.q ?? ''} onChange={(q) => update({ q })} />
          <FilterSelect
            label="Action"
            value={String(params.action ?? '')}
            onChange={(action) => update({ action })}
            options={Object.entries(ACTIONS).map(([value, label]) => ({ value, label }))}
          />
        </ListToolbar>
        {query.isPending ? (
          <LoadingState />
        ) : query.isError ? (
          <ErrorState error={query.error} onRetry={() => void query.refetch()} />
        ) : query.data.items.length === 0 ? (
          <EmptyState title="No audit entries" />
        ) : (
          <>
            <DataTable
              caption="Audit log"
              columns={columns}
              rows={query.data.items}
              rowKey={(e) => e.id}
              sort={params.sort}
              order={params.order}
              onSort={toggleSort}
              fetching={query.isFetching}
              mobileTitle={(e) => ACTIONS[e.action]}
            />
            <Pagination page={query.data.page} pageSize={query.data.page_size} total={query.data.total} onPage={(page) => update({ page })} />
          </>
        )}
      </div>
    </>
  )
}
