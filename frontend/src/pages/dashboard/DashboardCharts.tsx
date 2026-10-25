// Loaded lazily: Recharts is the largest dependency and only the dashboard needs it.
import { Bar, BarChart, CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { INK, SERIES, tooltipStyle } from '@/lib/chartTheme'
import { useTheme } from '@/lib/theme'
import type { DashboardSummary } from '@/lib/types'

const shortDate = (iso: string) =>
  new Date(`${iso}T00:00:00`).toLocaleDateString(undefined, { day: 'numeric', month: 'short' })
const percent = (value: number) => `${Math.round(value * 1000) / 10}%`

function TableView({ caption, headers, rows }: { caption: string; headers: [string, string]; rows: [string, string][] }) {
  return (
    <details className="mt-3 text-sm">
      <summary className="cursor-pointer text-indigo-700 hover:underline dark:text-indigo-300">Show data table</summary>
      <div className="mt-2 max-h-64 overflow-auto">
        <table className="w-full text-left">
          <caption className="sr-only">{caption}</caption>
          <thead>
            <tr className="border-b border-slate-200 dark:border-slate-700">
              <th scope="col" className="py-1 pr-4 font-medium">{headers[0]}</th>
              <th scope="col" className="py-1 font-medium">{headers[1]}</th>
            </tr>
          </thead>
          <tbody>
            {rows.map(([a, b]) => (
              <tr key={a} className="border-b border-slate-100 dark:border-slate-800">
                <td className="py-1 pr-4">{a}</td>
                <td className="py-1 tabular-nums">{b}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </details>
  )
}

export function AttendanceTrendChart({ data }: { data: DashboardSummary['attendance_trend'] }) {
  const { resolved } = useTheme()
  const ink = INK[resolved]
  const values = data.map((d) => d.attendance_rate)
  const min = Math.max(0, Math.floor((Math.min(...values) - 0.02) * 20) / 20)
  return (
    <figure>
      <figcaption className="sr-only">
        Weekly attendance rate, {data.length} weeks, from {percent(Math.min(...values))} to {percent(Math.max(...values))}.
      </figcaption>
      <div className="h-64" aria-hidden="true">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data} margin={{ top: 8, right: 12, bottom: 0, left: 0 }}>
            <CartesianGrid stroke={ink.grid} vertical={false} />
            <XAxis dataKey="week_start" tickFormatter={shortDate} tick={{ fill: ink.axis, fontSize: 12 }} tickLine={false} axisLine={{ stroke: ink.grid }} minTickGap={24} />
            <YAxis domain={[min, 1]} tickFormatter={percent} tick={{ fill: ink.axis, fontSize: 12 }} tickLine={false} axisLine={false} width={48} />
            <Tooltip
              formatter={(value) => [percent(Number(value)), 'Attendance']}
              labelFormatter={(label) => `Week of ${shortDate(String(label))}`}
              contentStyle={tooltipStyle(resolved)}
              cursor={{ stroke: ink.axis, strokeDasharray: '3 3' }}
            />
            <Line type="monotone" dataKey="attendance_rate" stroke={SERIES[resolved]} strokeWidth={2} dot={false} activeDot={{ r: 5, strokeWidth: 2, stroke: ink.tooltipBg }} />
          </LineChart>
        </ResponsiveContainer>
      </div>
      <TableView
        caption="Weekly attendance rate"
        headers={['Week starting', 'Attendance']}
        rows={data.map((d) => [d.week_start, percent(d.attendance_rate)])}
      />
    </figure>
  )
}

export function GradeDistributionChart({ data }: { data: DashboardSummary['grade_distribution'] }) {
  const { resolved } = useTheme()
  const ink = INK[resolved]
  const total = data.reduce((sum, d) => sum + d.students, 0)
  return (
    <figure>
      <figcaption className="sr-only">
        Number of students by average grade band, {total} students in total.
      </figcaption>
      <div className="h-64" aria-hidden="true">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} margin={{ top: 8, right: 12, bottom: 0, left: 0 }} barCategoryGap={2}>
            <CartesianGrid stroke={ink.grid} vertical={false} />
            <XAxis dataKey="label" tick={{ fill: ink.axis, fontSize: 12 }} tickLine={false} axisLine={{ stroke: ink.grid }} interval={0} angle={-30} textAnchor="end" height={44} />
            <YAxis allowDecimals={false} tick={{ fill: ink.axis, fontSize: 12 }} tickLine={false} axisLine={false} width={36} />
            <Tooltip
              formatter={(value) => [value, 'Students']}
              labelFormatter={(label) => `Average ${String(label)}%`}
              contentStyle={tooltipStyle(resolved)}
              cursor={{ fill: ink.grid, opacity: 0.6 }}
            />
            <Bar dataKey="students" fill={SERIES[resolved]} radius={[4, 4, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>
      <TableView
        caption="Students by average grade band"
        headers={['Average grade', 'Students']}
        rows={data.map((d) => [`${d.label}%`, String(d.students)])}
      />
    </figure>
  )
}
