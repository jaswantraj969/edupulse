import { Button } from '@/components/ui'
import { useAuth, useUser } from '@/lib/auth'

/** Shown instead of the app while an account waits for approval; the API refuses all data. */
export default function PendingPage() {
  const user = useUser()
  const { logout } = useAuth()
  return (
    <main className="flex min-h-dvh items-center justify-center px-4 py-10">
      <div className="w-full max-w-md">
        <p className="text-center text-2xl font-bold tracking-tight text-indigo-700 dark:text-indigo-300">EduPulse</p>
        <div className="card mt-8 flex flex-col gap-4 p-6 text-sm">
          <h1 className="text-lg font-semibold">Waiting for approval</h1>
          <p className="text-slate-700 dark:text-slate-300">
            Your account <span className="font-medium text-slate-900 dark:text-slate-100">{user.email}</span> has been
            created, but an administrator must approve it before you can see any school data. Sign in again later to
            check.
          </p>
          <Button variant="secondary" onClick={() => void logout()} className="w-full">
            Sign out
          </Button>
        </div>
      </div>
    </main>
  )
}
