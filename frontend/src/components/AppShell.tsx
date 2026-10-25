import { useState } from 'react'
import { NavLink, Outlet, useLocation } from 'react-router'
import { useAuth, useUser } from '@/lib/auth'
import { useTheme } from '@/lib/theme'
import { Dialog } from './Dialog'
import { Icon, type IconName } from './icons'

interface NavItem {
  to: string
  label: string
  icon: IconName
  adminOnly?: boolean
  primary?: boolean // shown in the mobile bottom bar
}

const NAV_ITEMS: NavItem[] = [
  { to: '/', label: 'Dashboard', icon: 'dashboard', primary: true },
  { to: '/students', label: 'Students', icon: 'students', primary: true },
  { to: '/attendance', label: 'Attendance', icon: 'attendance', primary: true },
  { to: '/grades', label: 'Grades', icon: 'grades', primary: true },
  { to: '/early-warning', label: 'Early warning', icon: 'risk' },
  { to: '/classes', label: 'Classes', icon: 'classes' },
  { to: '/teachers', label: 'Teachers', icon: 'teachers' },
  { to: '/staff', label: 'Staff', icon: 'staff', adminOnly: true },
  { to: '/audit', label: 'Audit log', icon: 'audit', adminOnly: true },
]

function navClass({ isActive }: { isActive: boolean }): string {
  return `flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors ${
    isActive
      ? 'bg-indigo-50 text-indigo-800 dark:bg-indigo-950 dark:text-indigo-200'
      : 'text-slate-700 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800'
  }`
}

function ThemeToggle() {
  const { resolved, setChoice } = useTheme()
  const next = resolved === 'dark' ? 'light' : 'dark'
  return (
    <button
      type="button"
      onClick={() => setChoice(next)}
      className="rounded-lg p-2 text-slate-700 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800"
      aria-label={`Switch to ${next} mode`}
      title={`Switch to ${next} mode`}
    >
      <Icon name={resolved === 'dark' ? 'sun' : 'moon'} />
    </button>
  )
}

export function AppShell() {
  const user = useUser()
  const { logout } = useAuth()
  const location = useLocation()
  const [moreOpen, setMoreOpen] = useState(false)
  const items = NAV_ITEMS.filter((item) => !item.adminOnly || user.role === 'admin')
  const secondary = items.filter((item) => !item.primary)

  return (
    <div className="min-h-dvh md:flex">
      <a
        href="#main"
        className="sr-only z-50 rounded bg-white px-4 py-2 text-indigo-800 focus:not-sr-only focus:fixed focus:top-2 focus:left-2"
      >
        Skip to content
      </a>

      {/* Sidebar (tablet and desktop) */}
      <aside className="sticky top-0 hidden h-dvh w-60 shrink-0 flex-col border-r border-slate-200 bg-white px-3 py-5 md:flex dark:border-slate-800 dark:bg-slate-900">
        <p className="px-3 text-lg font-bold tracking-tight text-indigo-700 dark:text-indigo-300">EduPulse</p>
        <nav aria-label="Main" className="mt-6 flex flex-1 flex-col gap-1">
          {items.map((item) => (
            <NavLink key={item.to} to={item.to} end={item.to === '/'} className={navClass}>
              <Icon name={item.icon} />
              {item.label}
            </NavLink>
          ))}
        </nav>
        <div className="border-t border-slate-200 pt-4 dark:border-slate-800">
          <p className="truncate px-3 text-sm font-medium">{user.full_name}</p>
          <p className="px-3 text-xs text-slate-600 capitalize dark:text-slate-400">{user.role}</p>
          <div className="mt-3 flex items-center justify-between px-1">
            <ThemeToggle />
            <button
              type="button"
              onClick={() => void logout()}
              className="flex items-center gap-2 rounded-lg px-3 py-2 text-sm text-slate-700 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800"
            >
              <Icon name="logout" />
              Sign out
            </button>
          </div>
        </div>
      </aside>

      <div className="flex min-w-0 flex-1 flex-col">
        {/* Top bar (mobile) */}
        <header className="sticky top-0 z-30 flex items-center justify-between border-b border-slate-200 bg-white/95 px-4 py-3 backdrop-blur md:hidden dark:border-slate-800 dark:bg-slate-900/95">
          <p className="text-lg font-bold tracking-tight text-indigo-700 dark:text-indigo-300">EduPulse</p>
          <ThemeToggle />
        </header>

        <main id="main" tabIndex={-1} className="mx-auto w-full max-w-6xl flex-1 px-4 pt-6 pb-28 md:px-8 md:pb-10">
          <Outlet />
        </main>
      </div>

      {/* Bottom navigation (mobile) */}
      <nav
        aria-label="Main"
        className="fixed inset-x-0 bottom-0 z-40 grid grid-cols-5 border-t border-slate-200 bg-white pb-[env(safe-area-inset-bottom)] md:hidden dark:border-slate-800 dark:bg-slate-900"
      >
        {items
          .filter((item) => item.primary)
          .map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.to === '/'}
              className={({ isActive }) =>
                `flex min-h-14 flex-col items-center justify-center gap-0.5 text-[11px] font-medium ${
                  isActive ? 'text-indigo-700 dark:text-indigo-300' : 'text-slate-600 dark:text-slate-400'
                }`
              }
            >
              <Icon name={item.icon} />
              {item.label}
            </NavLink>
          ))}
        <button
          type="button"
          onClick={() => setMoreOpen(true)}
          aria-haspopup="dialog"
          className={`flex min-h-14 flex-col items-center justify-center gap-0.5 text-[11px] font-medium ${
            secondary.some((i) => location.pathname.startsWith(i.to))
              ? 'text-indigo-700 dark:text-indigo-300'
              : 'text-slate-600 dark:text-slate-400'
          }`}
        >
          <Icon name="more" />
          More
        </button>
      </nav>

      <Dialog open={moreOpen} title="More" onClose={() => setMoreOpen(false)}>
        <p className="mb-3 text-sm">
          {user.full_name} <span className="text-slate-600 capitalize dark:text-slate-400">· {user.role}</span>
        </p>
        <nav aria-label="More" className="flex flex-col gap-1">
          {secondary.map((item) => (
            <NavLink key={item.to} to={item.to} className={navClass} onClick={() => setMoreOpen(false)}>
              <Icon name={item.icon} />
              {item.label}
            </NavLink>
          ))}
          <button
            type="button"
            onClick={() => void logout()}
            className="flex items-center gap-3 rounded-lg px-3 py-2 text-left text-sm font-medium text-slate-700 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800"
          >
            <Icon name="logout" />
            Sign out
          </button>
        </nav>
      </Dialog>
    </div>
  )
}
