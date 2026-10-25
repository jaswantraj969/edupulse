import { zodResolver } from '@hookform/resolvers/zod'
import { useState } from 'react'
import { useForm, useWatch } from 'react-hook-form'
import { Link, Navigate } from 'react-router'
import { z } from 'zod'
import { FormError, TextAreaField, TextField } from '@/components/Field'
import { Button } from '@/components/ui'
import { ApiError, api, errorMessage } from '@/lib/api'
import { useAuth } from '@/lib/auth'
import { PASSWORD_RULES, passwordProblems } from './passwordRules'

const schema = z
  .object({
    full_name: z.string().trim().min(1, 'Enter your full name').max(200, 'Use at most 200 characters'),
    email: z.string().trim().min(1, 'Enter your e-mail address').pipe(z.email('Enter a valid e-mail address')),
    password: z.string().superRefine((value, ctx) => {
      const problems = passwordProblems(value)
      if (problems.length) ctx.addIssue({ code: 'custom', message: `The password needs: ${problems.join(', ')}` })
    }),
    confirm: z.string().min(1, 'Repeat the password'),
    note: z.string().trim().max(500, 'Use at most 500 characters'),
  })
  .refine((v) => v.password === v.confirm, { path: ['confirm'], message: 'The passwords do not match' })
type Values = z.infer<typeof schema>

function PasswordRules({ value }: { value: string }) {
  return (
    <div>
      <p id="password-rules" className="text-xs font-medium text-slate-700 dark:text-slate-300">
        The password must have:
      </p>
      <ul className="mt-1 grid grid-cols-1 gap-1 text-xs sm:grid-cols-2" aria-labelledby="password-rules">
        {PASSWORD_RULES.map((rule) => {
          const met = rule.test(value)
          return (
            <li key={rule.id} className={met ? 'text-emerald-800 dark:text-emerald-300' : 'text-slate-600 dark:text-slate-400'}>
              <span aria-hidden="true">{met ? '✓' : '○'}</span> {rule.label}
              <span className="sr-only">{met ? ' (met)' : ' (not met yet)'}</span>
            </li>
          )
        })}
      </ul>
    </div>
  )
}

function Shell({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <main className="flex min-h-dvh items-center justify-center px-4 py-10">
      <div className="w-full max-w-md">
        <p className="text-center text-2xl font-bold tracking-tight text-indigo-700 dark:text-indigo-300">EduPulse</p>
        <h1 className="mt-2 text-center text-lg font-medium">{title}</h1>
        {children}
      </div>
    </main>
  )
}

export default function SignupPage() {
  const { status } = useAuth()
  const [sent, setSent] = useState(false)
  const [serverError, setServerError] = useState<string | null>(null)
  const {
    register,
    handleSubmit,
    control,
    formState: { errors, isSubmitting },
  } = useForm<Values>({
    resolver: zodResolver(schema),
    mode: 'onTouched',
    defaultValues: { full_name: '', email: '', password: '', confirm: '', note: '' },
  })
  const password = useWatch({ control, name: 'password' })

  if (status === 'authenticated') return <Navigate to="/" replace />

  if (sent) {
    return (
      <Shell title="Request sent">
        <div className="card mt-8 flex flex-col gap-4 p-6 text-sm" role="status">
          <p className="text-base font-semibold">Your request was sent; an administrator must approve it.</p>
          <p className="text-slate-700 dark:text-slate-300">
            You can sign in with your e-mail and password at any time to see whether it has been approved. Until then
            your account cannot see any school data.
          </p>
          <Link to="/login" className="font-medium text-indigo-700 hover:underline dark:text-indigo-300">
            Back to sign in
          </Link>
        </div>
      </Shell>
    )
  }

  const onSubmit = async (values: Values) => {
    setServerError(null)
    try {
      await api.post('/auth/signup', {
        full_name: values.full_name,
        email: values.email,
        password: values.password,
        note: values.note || null,
      })
      setSent(true)
    } catch (error) {
      setServerError(
        error instanceof ApiError && error.status === 429
          ? 'Too many requests from this device. Please try again later.'
          : errorMessage(error),
      )
    }
  }

  return (
    <Shell title="Request an account">
      <form onSubmit={handleSubmit(onSubmit)} noValidate className="card mt-8 flex flex-col gap-4 p-6">
        <p className="text-sm text-slate-700 dark:text-slate-300">
          An administrator reviews every request. You can sign in straight away, but you will only see school data once
          your account is approved.
        </p>
        <FormError message={serverError} />
        <TextField label="Full name" autoComplete="name" required registration={register('full_name')} error={errors.full_name} />
        <TextField label="E-mail" type="email" autoComplete="email" required registration={register('email')} error={errors.email} />
        <TextField
          label="Password"
          type="password"
          autoComplete="new-password"
          required
          registration={register('password')}
          error={errors.password}
        />
        <PasswordRules value={password} />
        <TextField
          label="Repeat password"
          type="password"
          autoComplete="new-password"
          required
          registration={register('confirm')}
          error={errors.confirm}
        />
        <TextAreaField
          label="Note for the administrator (optional)"
          hint='For example: "I teach biology in 10-A".'
          maxLength={500}
          registration={register('note')}
          error={errors.note}
        />
        <Button type="submit" loading={isSubmitting} className="mt-2 w-full">
          Send request
        </Button>
      </form>
      <p className="mt-6 text-center text-sm">
        Already have an account?{' '}
        <Link to="/login" className="font-medium text-indigo-700 hover:underline dark:text-indigo-300">
          Sign in
        </Link>
      </p>
    </Shell>
  )
}
