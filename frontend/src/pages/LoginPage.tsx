import { zodResolver } from '@hookform/resolvers/zod'
import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { Link, Navigate, useLocation, useNavigate } from 'react-router'
import { z } from 'zod'
import { FormError, TextField } from '@/components/Field'
import { Button } from '@/components/ui'
import { ApiError, errorMessage } from '@/lib/api'
import { useAuth } from '@/lib/auth'
import { useMeta } from '@/lib/meta'
import type { DemoAccount } from '@/lib/types'

const schema = z.object({
  email: z.string().trim().min(1, 'Enter your e-mail address').pipe(z.email('Enter a valid e-mail address')),
  password: z.string().min(1, 'Enter your password'),
})
type Values = z.infer<typeof schema>

/** Demo installations only: the server lists these accounts only while demo_mode is on. */
function DemoAccounts({ accounts, onUse }: { accounts: DemoAccount[]; onUse: (account: DemoAccount) => void }) {
  return (
    <section aria-labelledby="demo-accounts-h" className="mt-6 rounded-xl border border-amber-300 bg-amber-50 p-4 text-sm text-amber-950 dark:border-amber-700 dark:bg-amber-950/60 dark:text-amber-100">
      <h2 id="demo-accounts-h" className="font-semibold">
        Demo accounts
      </h2>
      <p className="mt-1 text-xs">All people and records in this installation are synthetic.</p>
      <ul className="mt-3 flex flex-col gap-3">
        {accounts.map((account) => (
          <li key={account.email} className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
            <div className="min-w-0">
              <p className="font-medium">{account.label}</p>
              <p className="truncate font-mono text-xs">{account.email}</p>
              <p className="font-mono text-xs">
                <span className="font-sans">Password:</span> {account.password}
              </p>
            </div>
            <Button variant="secondary" onClick={() => onUse(account)} aria-label={`Use this account: ${account.label}`}>
              Use this account
            </Button>
          </li>
        ))}
      </ul>
    </section>
  )
}

export default function LoginPage() {
  const { status, login } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const [serverError, setServerError] = useState<string | null>(null)
  const meta = useMeta()
  const {
    register,
    handleSubmit,
    setValue,
    setFocus,
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

  const fillAccount = (account: DemoAccount) => {
    setValue('email', account.email, { shouldValidate: true })
    setValue('password', account.password, { shouldValidate: true })
    setFocus('password')
  }
  const demoAccounts = meta.data?.demo_mode ? meta.data.demo_accounts : []

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
        <p className="mt-6 text-center text-sm">
          New here?{' '}
          <Link to="/signup" className="font-medium text-indigo-700 hover:underline dark:text-indigo-300">
            Create account
          </Link>
        </p>
        {demoAccounts.length > 0 && <DemoAccounts accounts={demoAccounts} onUse={fillAccount} />}
      </div>
    </main>
  )
}
