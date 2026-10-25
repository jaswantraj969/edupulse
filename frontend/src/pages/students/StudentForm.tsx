import { zodResolver } from '@hookform/resolvers/zod'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { useForm, type Path } from 'react-hook-form'
import { useNavigate, useParams } from 'react-router'
import { z } from 'zod'
import { FormError, SelectField, TextField } from '@/components/Field'
import { BackLink, Button, ErrorState, LoadingState, PageHeader } from '@/components/ui'
import { ApiError, api, errorMessage } from '@/lib/api'
import { capitalize } from '@/lib/format'
import { useAllClasses } from '@/lib/queries'
import { useToast } from '@/lib/toast'
import type { Student } from '@/lib/types'

const today = () => new Date().toISOString().slice(0, 10)
const optional = <T extends z.ZodType<string>>(schema: T) => z.union([schema, z.literal('')])
const phone = z.string().trim().regex(/^[0-9+()\-. ]{5,40}$/, 'Use digits, spaces and + ( ) - . only')

const studentSchema = z
  .object({
    student_no: z.string().trim().regex(/^[A-Za-z0-9-]{2,20}$/, '2–20 letters, digits or hyphens'),
    first_name: z.string().trim().min(1, 'First name is required').max(100),
    last_name: z.string().trim().min(1, 'Last name is required').max(100),
    date_of_birth: z.string().min(1, 'Date of birth is required'),
    enrolled_on: z.string().min(1, 'Enrolment date is required'),
    email: optional(z.string().trim().pipe(z.email('Enter a valid e-mail address'))),
    phone: optional(phone),
    guardian_name: z.string().trim().max(200),
    guardian_phone: optional(phone),
    status: z.enum(['active', 'inactive', 'graduated', 'withdrawn']),
    prior_failures: z.coerce.number<string>().int().min(0, 'Between 0 and 3').max(3, 'Between 0 and 3'),
    class_id: z.string(),
  })
  .refine((v) => !v.date_of_birth || v.date_of_birth < today(), {
    path: ['date_of_birth'],
    message: 'Date of birth must be in the past',
  })
  .refine((v) => !v.date_of_birth || !v.enrolled_on || v.enrolled_on >= v.date_of_birth, {
    path: ['enrolled_on'],
    message: 'Enrolment cannot be before the date of birth',
  })

type StudentFormValues = z.input<typeof studentSchema>

const EMPTY: StudentFormValues = {
  student_no: '',
  first_name: '',
  last_name: '',
  date_of_birth: '',
  enrolled_on: today(),
  email: '',
  phone: '',
  guardian_name: '',
  guardian_phone: '',
  status: 'active',
  prior_failures: '0',
  class_id: '',
}

function toValues(s: Student): StudentFormValues {
  return {
    student_no: s.student_no,
    first_name: s.first_name,
    last_name: s.last_name,
    date_of_birth: s.date_of_birth,
    enrolled_on: s.enrolled_on,
    email: s.email ?? '',
    phone: s.phone ?? '',
    guardian_name: s.guardian_name ?? '',
    guardian_phone: s.guardian_phone ?? '',
    status: s.status,
    prior_failures: String(s.prior_failures),
    class_id: s.class_id ? String(s.class_id) : '',
  }
}

function toPayload(values: z.output<typeof studentSchema>) {
  const blank = (v: string) => (v.trim() === '' ? null : v.trim())
  return {
    student_no: values.student_no,
    first_name: values.first_name,
    last_name: values.last_name,
    date_of_birth: values.date_of_birth,
    enrolled_on: values.enrolled_on,
    email: blank(values.email),
    phone: blank(values.phone),
    guardian_name: blank(values.guardian_name),
    guardian_phone: blank(values.guardian_phone),
    status: values.status,
    prior_failures: values.prior_failures,
    ...(values.class_id ? { class_id: Number(values.class_id) } : {}),
  }
}

interface FormProps {
  initial: StudentFormValues
  submitLabel: string
  onSubmit: (payload: ReturnType<typeof toPayload>) => Promise<unknown>
}

export function StudentFormFields({ initial, submitLabel, onSubmit }: FormProps) {
  const classes = useAllClasses()
  const [serverError, setServerError] = useState<string | null>(null)
  const {
    register,
    handleSubmit,
    setError,
    formState: { errors, isSubmitting },
  } = useForm<StudentFormValues, unknown, z.output<typeof studentSchema>>({
    resolver: zodResolver(studentSchema),
    defaultValues: initial,
    mode: 'onBlur',
  })

  const submit = handleSubmit(async (values) => {
    setServerError(null)
    try {
      await onSubmit(toPayload(values))
    } catch (error) {
      if (error instanceof ApiError) {
        const fields = error.fieldErrors()
        for (const [field, message] of Object.entries(fields)) {
          if (field in initial) setError(field as Path<StudentFormValues>, { message })
        }
        const conflictField = (error.details as { field?: string } | null)?.field
        if (error.status === 409 && conflictField && conflictField in initial) {
          setError(conflictField as Path<StudentFormValues>, { message: error.message })
        }
      }
      setServerError(errorMessage(error))
    }
  })

  return (
    <form onSubmit={submit} noValidate className="card flex flex-col gap-6 p-4 sm:p-6">
      <FormError message={serverError} />
      <fieldset className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <legend className="mb-2 text-base font-semibold">Student</legend>
        <TextField label="Student number" required registration={register('student_no')} error={errors.student_no} />
        <SelectField
          label="Class"
          registration={register('class_id')}
          placeholder="Not enrolled"
          options={(classes.data ?? []).map((c) => ({ value: c.id, label: c.name }))}
        />
        <TextField label="First name" required autoComplete="off" registration={register('first_name')} error={errors.first_name} />
        <TextField label="Last name" required autoComplete="off" registration={register('last_name')} error={errors.last_name} />
        <TextField label="Date of birth" type="date" required registration={register('date_of_birth')} error={errors.date_of_birth} />
        <TextField label="Enrolled on" type="date" required registration={register('enrolled_on')} error={errors.enrolled_on} />
        <SelectField
          label="Status"
          required
          registration={register('status')}
          options={['active', 'inactive', 'graduated', 'withdrawn'].map((s) => ({ value: s, label: capitalize(s) }))}
        />
        <TextField
          label="Prior year failures"
          type="number"
          min={0}
          max={3}
          inputMode="numeric"
          hint="Number of school years previously failed (0–3)."
          registration={register('prior_failures')}
          error={errors.prior_failures}
        />
      </fieldset>
      <fieldset className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <legend className="mb-2 text-base font-semibold">Contact</legend>
        <TextField label="E-mail" type="email" registration={register('email')} error={errors.email} />
        <TextField label="Phone" type="tel" registration={register('phone')} error={errors.phone} />
        <TextField label="Guardian name" registration={register('guardian_name')} error={errors.guardian_name} />
        <TextField label="Guardian phone" type="tel" registration={register('guardian_phone')} error={errors.guardian_phone} />
      </fieldset>
      <div className="flex justify-end">
        <Button type="submit" loading={isSubmitting}>
          {submitLabel}
        </Button>
      </div>
    </form>
  )
}

export function StudentCreatePage() {
  const navigate = useNavigate()
  const toast = useToast()
  const queryClient = useQueryClient()
  const create = useMutation({
    mutationFn: (payload: ReturnType<typeof toPayload>) => api.post<Student>('/students', payload),
    onSuccess: async (student) => {
      await queryClient.invalidateQueries({ queryKey: ['students'] })
      toast.success(`${student.first_name} ${student.last_name} was added`)
      navigate(`/students/${student.id}`)
    },
  })
  return (
    <>
      <BackLink to="/students">Students</BackLink>
      <PageHeader title="Add student" />
      <StudentFormFields initial={EMPTY} submitLabel="Create student" onSubmit={(p) => create.mutateAsync(p)} />
    </>
  )
}

export function StudentEditPage() {
  const id = Number(useParams().id)
  const navigate = useNavigate()
  const toast = useToast()
  const queryClient = useQueryClient()
  const query = useQuery({ queryKey: ['students', id], queryFn: () => api.get<Student>(`/students/${id}`) })
  const save = useMutation({
    mutationFn: (payload: ReturnType<typeof toPayload>) => api.patch<Student>(`/students/${id}`, payload),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['students'] })
      toast.success('Changes saved')
      navigate(`/students/${id}`)
    },
  })
  return (
    <>
      <BackLink to={`/students/${id}`}>Back to student</BackLink>
      <PageHeader title="Edit student" />
      {query.isPending && <LoadingState />}
      {query.isError && <ErrorState error={query.error} onRetry={() => void query.refetch()} />}
      {query.data && (
        <StudentFormFields initial={toValues(query.data)} submitLabel="Save changes" onSubmit={(p) => save.mutateAsync(p)} />
      )}
    </>
  )
}
