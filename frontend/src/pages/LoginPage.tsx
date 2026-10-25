import { zodResolver } from '@hookform/resolvers/zod'
import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { Navigate, useLocation, useNavigate } from 'react-router'
import { z } from 'zod'
import { FormError, TextField } from '@/components/Field'
import { Button } from '@/components/ui'
import { ApiError, errorMessage } from '@/lib/api'
import { useAuth } from '@/lib/auth'

const schema = z.object({
  email: z.string().trim().min(1, 'Enter your e-mail address').pipe(z.email('Enter a valid e-mail address')),
  password: z.string().min(1, 'Enter your password'),
})
type Values = z.infer<typeof schema>

export default function LoginPage() {
  const { status, login } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const [serverError, setServerError] = useState<string | null>(null)
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<Values>({ resolver: zodResolver(schema), defaultValues: { email: '', password: '' } })

  const from = (location.state as { from?: string } | null)?.from ?? '/'
  if (status === 'authenticated') return <Navigate to={from} replace />

  const onSubmit = async (values: Values) => {
    setServerError(null)
    try {
      await login(values.email, values.password)
      navigate(from, { replace: true })
    } catch (error) {
      setServerError(
        error instanceof ApiError && error.status === 429
          ? 'Too many failed attempts. Please wait a minute and try again.'
          : errorMessage(error),
      )
    }
  }

  return (
    <main className="flex min-h-dvh items-center justify-center px-4 py-10">
      <div className="w-full max-w-sm">
        <p className="text-center text-2xl font-bold tracking-tight text-indigo-700 dark:text-indigo-300">EduPulse</p>
        <h1 className="mt-2 text-center text-lg font-medium">Sign in to your school account</h1>
        <form onSubmit={handleSubmit(onSubmit)} noValidate className="card mt-8 flex flex-col gap-4 p-6">
          <FormError message={serverError} />
          <TextField
            label="E-mail"
            type="email"
            autoComplete="username"
            required
            registration={register('email')}
            error={errors.email}
          />
          <TextField
            label="Password"
            type="password"
            autoComplete="current-password"
            required
            registration={register('password')}
            error={errors.password}
          />
          <Button type="submit" loading={isSubmitting} className="mt-2 w-full">
            Sign in
          </Button>
        </form>
        <p className="mt-6 text-center text-xs text-slate-600 dark:text-slate-400">
          Demo installation: all people and records are synthetic. Demo accounts use the{' '}
          <span className="font-mono">@edupulse.example</span> domain.
        </p>
      </div>
    </main>
  )
}
