import { keepPreviousData, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { Link } from 'react-router'
import { FilterSelect, ListToolbar, SearchBox } from '@/components/ListToolbar'
import { RecordFormDialog, type FieldSpec } from '@/components/RecordFormDialog'
import { Button, EmptyState, ErrorState, LoadingState, PageHeader } from '@/components/ui'
import { api } from '@/lib/api'
import { useUser } from '@/lib/auth'
import { useListState } from '@/lib/hooks'
import { useAcademicYears, useAllTeachers } from '@/lib/queries'
import { useToast } from '@/lib/toast'
import type { ClassGroup, Page } from '@/lib/types'
import { classSchema, type ClassFormValues } from './classSchema'


export default function ClassesPage() {
  const user = useUser()
  const toast = useToast()
  const queryClient = useQueryClient()
  const { params, update } = useListState('name', ['grade_level'], 100)
  const years = useAcademicYears()
  const teachers = useAllTeachers()
  const [creating, setCreating] = useState(false)
  const query = useQuery({
    queryKey: ['classes', params],
    queryFn: () => api.get<Page<ClassGroup>>('/classes', params),
    placeholderData: keepPreviousData,
  })

  const fields: FieldSpec<ClassFormValues>[] = [
    {
      name: 'academic_year_id',
      label: 'Academic year',
      type: 'select',
      required: true,
      options: (years.data ?? []).map((y) => ({ value: y.id, label: y.name })),
    },
    { name: 'grade_level', label: 'Grade', type: 'number', required: true },
    { name: 'section', label: 'Section', required: true },
    { name: 'room', label: 'Room' },
    {
      name: 'homeroom_teacher_id',
      label: 'Homeroom teacher',
      type: 'select',
      placeholder: 'None',
      options: (teachers.data ?? []).map((t) => ({ value: t.id, label: `${t.last_name}, ${t.first_name}` })),
    },
  ]

  return (
    <>
      <PageHeader
        title="Classes"
        description={user.role === 'admin' ? 'All classes this year.' : 'Classes you teach or are homeroom teacher of.'}
        actions={user.role === 'admin' && <Button onClick={() => setCreating(true)}>Add class</Button>}
      />
      <div className="card mb-4 overflow-hidden">
        <ListToolbar>
          <SearchBox label="Search" placeholder="Class or room" value={params.q ?? ''} onChange={(q) => update({ q })} />
          <FilterSelect
            label="Grade"
            value={String(params.grade_level ?? '')}
            onChange={(grade_level) => update({ grade_level })}
            options={[10, 11, 12].map((g) => ({ value: g, label: `Grade ${g}` }))}
          />
        </ListToolbar>
      </div>
      {query.isPending ? (
        <LoadingState />
      ) : query.isError ? (
        <ErrorState error={query.error} onRetry={() => void query.refetch()} />
      ) : query.data.items.length === 0 ? (
        <EmptyState title="No classes found" />
      ) : (
        <ul className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {query.data.items.map((c) => (
            <li key={c.id}>
              <Link to={`/classes/${c.id}`} className="card block p-4 transition-shadow hover:shadow-md">
                <p className="text-lg font-semibold">{c.name}</p>
                <p className="mt-1 text-sm text-slate-600 dark:text-slate-400">
                  {c.student_count} students · {c.room ?? 'No room'}
                </p>
                <p className="mt-1 text-sm text-slate-600 dark:text-slate-400">
                  Homeroom: {c.homeroom_teacher_name ?? '—'}
                </p>
              </Link>
            </li>
          ))}
        </ul>
      )}
      <RecordFormDialog
        open={creating}
        title="Add class"
        submitLabel="Create class"
        schema={classSchema}
        initial={{ academic_year_id: String(years.data?.[0]?.id ?? ''), grade_level: '10', section: '', room: '', homeroom_teacher_id: '' }}
        fields={fields}
        onSubmit={async (values) => {
          await api.post('/classes', values)
          await queryClient.invalidateQueries({ queryKey: ['classes'] })
          toast.success('Class created')
        }}
        onClose={() => setCreating(false)}
      />
    </>
  )
}
