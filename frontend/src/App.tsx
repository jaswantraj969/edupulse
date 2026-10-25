import { lazy, Suspense, type ReactNode } from 'react'
import { createBrowserRouter, Link, Navigate, Outlet, RouterProvider, useLocation } from 'react-router'
import { AppShell } from '@/components/AppShell'
import { EmptyState, LoadingState } from '@/components/ui'
import { buttonClass } from '@/components/buttonClass'
import { useAuth } from '@/lib/auth'

const LoginPage = lazy(() => import('@/pages/LoginPage'))
const DashboardPage = lazy(() => import('@/pages/dashboard/DashboardPage'))
const StudentsListPage = lazy(() => import('@/pages/students/StudentsListPage'))
const StudentDetailPage = lazy(() => import('@/pages/students/StudentDetailPage'))
const StudentCreatePage = lazy(() => import('@/pages/students/StudentForm').then((m) => ({ default: m.StudentCreatePage })))
const StudentEditPage = lazy(() => import('@/pages/students/StudentForm').then((m) => ({ default: m.StudentEditPage })))
const TeachersPage = lazy(() => import('@/pages/people/TeachersPage'))
const StaffPage = lazy(() => import('@/pages/people/StaffPage'))
const ClassesPage = lazy(() => import('@/pages/classes/ClassesPage'))
const ClassDetailPage = lazy(() => import('@/pages/classes/ClassDetailPage'))
const AttendancePage = lazy(() => import('@/pages/records/AttendancePage'))
const GradesPage = lazy(() => import('@/pages/records/GradesPage'))

function RequireAuth() {
  const { status } = useAuth()
  const location = useLocation()
  if (status === 'loading') return <LoadingState label="Signing in…" />
  if (status === 'anonymous') return <Navigate to="/login" replace state={{ from: location.pathname + location.search }} />
  return <Outlet />
}

function AdminOnly({ children }: { children: ReactNode }) {
  const { user } = useAuth()
  if (user?.role !== 'admin') {
    return <EmptyState title="Administrators only" description="Your account does not have access to this page." />
  }
  return children
}

function Page({ children }: { children: ReactNode }) {
  return <Suspense fallback={<LoadingState />}>{children}</Suspense>
}

function NotFound() {
  return (
    <EmptyState
      title="Page not found"
      description="The page you were looking for does not exist."
      action={
        <Link to="/" className={buttonClass('primary')}>
          Go to dashboard
        </Link>
      }
    />
  )
}

const router = createBrowserRouter([
  { path: '/login', element: <Page><LoginPage /></Page> },
  {
    element: <RequireAuth />,
    children: [
      {
        element: <AppShell />,
        children: [
          { index: true, element: <Page><DashboardPage /></Page> },
          { path: 'students', element: <Page><StudentsListPage /></Page> },
          { path: 'students/new', element: <Page><AdminOnly><StudentCreatePage /></AdminOnly></Page> },
          { path: 'students/:id', element: <Page><StudentDetailPage /></Page> },
          { path: 'students/:id/edit', element: <Page><AdminOnly><StudentEditPage /></AdminOnly></Page> },
          { path: 'teachers', element: <Page><TeachersPage /></Page> },
          { path: 'staff', element: <Page><AdminOnly><StaffPage /></AdminOnly></Page> },
          { path: 'classes', element: <Page><ClassesPage /></Page> },
          { path: 'classes/:id', element: <Page><ClassDetailPage /></Page> },
          { path: 'attendance', element: <Page><AttendancePage /></Page> },
          { path: 'grades', element: <Page><GradesPage /></Page> },
          { path: '*', element: <NotFound /> },
        ],
      },
    ],
  },
])

export default function App() {
  return <RouterProvider router={router} />
}
