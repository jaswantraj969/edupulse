import { zodResolver } from '@hookform/resolvers/zod'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { useForm, useWatch } from 'react-hook-form'
import { Link } from 'react-router'
import { z } from 'zod'
import { DataTable, type Column } from '@/components/DataTable'
import { Dialog } from '@/components/Dialog'
import { FormError, SelectField, TextAreaField } from '@/components/Field'
import { Button, EmptyState, ErrorState, LoadingState, PageHeader } from '@/components/ui'
import { api, errorMessage } from '@/lib/api'
import { formatDate } from '@/lib/format'
import { useToast } from '@/lib/toast'
import type { AccountRequest, UnlinkedTeacher } from '@/lib/types'

const approveSchema = z
  .object({ role: z.enum(['teacher', 'admin']), teacher_id: z.string() })
  .refine((v) => v.role === 'admin' || v.teacher_id !== '', {
    path: ['teacher_id'],
    message: 'Choose the teacher profile for this account',
  })
type ApproveValues = z.infer<typeof approveSchema>

const rejectSchema = z.object({ reason: z.string().trim().max(500, 'Use at most 500 characters') })
type RejectValues = z.infer<typeof rejectSchema>

function useDone(message: string, onClose: () => void) {
  const queryClient = useQueryClient()
  const toast = useToast()
  return async () => {
    await queryClient.invalidateQueries({ queryKey: ['account-requests'] })
    toast.success(message)
    onClose()
  }
}

function ApproveDialog({ request, onClose }: { request: AccountRequest; onClose: () => void }) {
  const teachers = useQuery({
    queryKey: ['account-requests', 'unlinked-teachers'],
    queryFn: () => api.get<UnlinkedTeacher[]>('/account-requests/unlinked-teachers'),
  })
  const [serverError, setServerError] = useState<string | null>(null)
  const {
    register,
    handleSubmit,
    control,
    formState: { errors, isSubmitting },
  } = useForm<ApproveValues>({ resolver: zodResolver(approveSchema), defaultValues: { role: 'teacher', teacher_id: '' } })
  const role = useWatch({ control, name: 'role' })
  const done = useDone(`${request.full_name} approved`, onClose)

  const onSubmit = async (values: ApproveValues) => {
    setServerError(null)
    try {
      await api.post(`/account-requests/${request.id}/approve`, {
        role: values.role,
        teacher_id: values.role === 'teacher' ? Number(values.teacher_id) : null,
      })
      await done()
    } catch (error) {
      setServerError(errorMessage(error))
    }
  }

  const options = (teachers.data ?? []).map((t) => ({ value: t.id, label: `${t.full_name} (${t.employee_no}, ${t.email})` }))
  return (
    <Dialog
      open
      title={`Approve ${request.full_name}`}
      onClose={onClose}
      footer={
        <>
          <Button variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" form="approve-form" loading={isSubmitting}>
            Approve
          </Button>
        </>
      }
    >
      <form id="approve-form" onSubmit={handleSubmit(onSubmit)} noValidate className="flex flex-col gap-4">
        <p>
          {request.email}
          {request.signup_note ? ` — “${request.signup_note}”` : ''}
        </p>
        <FormError message={serverError} />
        <SelectField
          label="Role"
          required
          registration={register('role')}
          error={errors.role}
          options={[
            { value: 'teacher', label: 'Teacher — sees only their own classes' },
            { value: 'admin', label: 'Administrator — sees and manages everything' },
          ]}
        />
        {role === 'teacher' &&
          (teachers.isPending ? (
            <LoadingState label="Loading teacher profiles…" />
          ) : teachers.isError ? (
            <ErrorState error={teachers.error} />
          ) : (
            <SelectField
              label="Teacher profile"
              required
              placeholder="Choose a teacher"
              registration={register('teacher_id')}
              error={errors.teacher_id}
              options={options}
              hint={
                options.length
                  ? 'Only teacher profiles without an account are listed. The account sees exactly that teacher’s classes.'
                  : 'Every teacher profile already has an account. Add the teacher on the Teachers page first.'
              }
            />
          ))}
      </form>
    </Dialog>
  )
}

function RejectDialog({ request, onClose }: { request: AccountRequest; onClose: () => void }) {
  const [serverError, setServerError] = useState<string | null>(null)
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<RejectValues>({ resolver: zodResolver(rejectSchema), defaultValues: { reason: '' } })
  const done = useDone(`Request from ${request.full_name} rejected`, onClose)

  const onSubmit = async (values: RejectValues) => {
    setServerError(null)
    try {
      await api.post(`/account-requests/${request.id}/reject`, { reason: values.reason || null })
      await done()
    } catch (error) {
      setServerError(errorMessage(error))
    }
  }

  return (
    <Dialog
      open
      title={`Reject ${request.full_name}`}
      onClose={onClose}
      footer={
        <>
          <Button variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" form="reject-form" variant="danger" loading={isSubmitting}>
            Reject request
          </Button>
        </>
      }
    >
      <form id="reject-form" onSubmit={handleSubmit(onSubmit)} noValidate className="flex flex-col gap-4">
        <p>{request.email} will not be able to sign in.</p>
        <FormError message={serverError} />
        <TextAreaField
          label="Reason (optional)"
          hint="Kept with the account for other administrators."
          maxLength={500}
          registration={register('reason')}
          error={errors.reason}
        />
      </form>
    </Dialog>
  )
}

export default function AccountRequestsPage() {
  const query = useQuery({
    queryKey: ['account-requests', 'list'],
    queryFn: () => api.get<{ items: AccountRequest[]; total: number }>('/account-requests'),
  })
  const [dialog, setDialog] = useState<{ kind: 'approve' | 'reject'; request: AccountRequest } | null>(null)
  const close = () => setDialog(null)

  const columns: Column<AccountRequest>[] = [
    {
      key: 'name',
      header: 'Name',
      render: (r) => (
        <span>
          <span className="font-medium">{r.full_name}</span>
          <span className="block text-xs text-slate-600 dark:text-slate-400">{r.email}</span>
        </span>
      ),
    },
    { key: 'note', header: 'Note', render: (r) => r.signup_note ?? '—', className: 'max-w-sm whitespace-normal' },
    { key: 'requested', header: 'Requested', render: (r) => formatDate(r.created_at) },
    {
      key: 'actions',
      header: 'Decision',
      render: (r) => (
        <span className="flex flex-wrap gap-2">
          <Button onClick={() => setDialog({ kind: 'approve', request: r })} aria-label={`Approve ${r.full_name}`}>
            Approve
          </Button>
          <Button variant="secondary" onClick={() => setDialog({ kind: 'reject', request: r })} aria-label={`Reject ${r.full_name}`}>
            Reject
          </Button>
        </span>
      ),
    },
  ]

  return (
    <>
      <PageHeader
        title="Account requests"
        description="People who signed up themselves. Approve them as a teacher (linked to a teacher profile) or an administrator, or reject the request. Every decision is recorded in the audit log."
      />
      {query.isPending && <LoadingState />}
      {query.isError && <ErrorState error={query.error} onRetry={() => void query.refetch()} />}
      {query.data &&
        (query.data.items.length === 0 ? (
          <EmptyState
            title="No pending requests"
            description="New sign-ups appear here."
            action={
              <Link to="/audit?action=account.approve" className="text-sm font-medium text-indigo-700 hover:underline dark:text-indigo-300">
                See past decisions in the audit log
              </Link>
            }
          />
        ) : (
          <DataTable
            caption={`${query.data.total} pending account request${query.data.total === 1 ? '' : 's'}`}
            columns={columns}
            rows={query.data.items}
            rowKey={(r) => r.id}
            mobileTitle={(r) => r.full_name}
          />
        ))}
      {dialog?.kind === 'approve' && <ApproveDialog request={dialog.request} onClose={close} />}
      {dialog?.kind === 'reject' && <RejectDialog request={dialog.request} onClose={close} />}
    </>
  )
}
