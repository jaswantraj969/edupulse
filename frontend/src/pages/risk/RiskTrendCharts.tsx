// Loaded lazily with Recharts. Two separate single-series charts (never a dual axis):
// monthly attendance rate and monthly average grade, with the prediction moment marked.
import { CartesianGrid, Line, LineChart, ReferenceLine, Tooltip, XAxis, YAxis } from 'recharts'
import { INK, SERIES, tooltipStyle } from '@/lib/chartTheme'
import { useTheme } from '@/lib/theme'
import { useElementWidth } from '@/lib/useElementWidth'

export interface TrendPoint {
  month: string // YYYY-MM
  value: number // 0-1
}

const monthYear = new Intl.DateTimeFormat(undefined, { month: 'short', year: '2-digit' })
const monthLabel = (m: string) => monthYear.format(new Date(`${m}-01T00:00:00`))
const Y_TICKS = [0, 0.25, 0.5, 0.75, 1]
const pct = (v: number) => `${Math.round(v * 100)}%`

interface Props {
  title: string
  seriesName: string
  data: TrendPoint[]
  asOfMonth: string | null
  floor?: number
}

export default function TrendChart({ title, seriesName, data, asOfMonth, floor = 0 }: Props) {
  const { resolved } = useTheme()
  const ink = INK[resolved]
  const [box, width] = useElementWidth<HTMLDivElement>()
  const values = data.map((d) => d.value)
  const min = Math.min(floor, Math.floor(Math.min(...values) * 10) / 10)
  return (
    <figure>
      <figcaption className="mb-2 text-sm font-medium">{title}</figcaption>
      <div ref={box} className="h-48" aria-hidden="true">
        {width > 0 && (
          <LineChart width={width} height={192} accessibilityLayer={false} data={data} margin={{ top: 16, right: 12, bottom: 0, left: 0 }}>
            <CartesianGrid stroke={ink.grid} vertical={false} />
            <XAxis dataKey="month" tickFormatter={monthLabel} tick={{ fill: ink.axis, fontSize: 12 }} tickLine={false} axisLine={{ stroke: ink.grid }} interval={Math.max(0, Math.ceil(data.length / 6) - 1)} />
            <YAxis domain={[min, 1]} ticks={Y_TICKS.filter((t) => t >= min)} interval={0} tickFormatter={pct} tick={{ fill: ink.axis, fontSize: 12 }} tickLine={false} axisLine={false} width={44} />
            {asOfMonth && (
              <ReferenceLine x={asOfMonth} stroke={ink.marker} strokeDasharray="4 4" label={{ value: 'Prediction moment', position: 'insideTopRight', fill: ink.axis, fontSize: 11 }} />
            )}
            <Tooltip formatter={(v) => [pct(Number(v)), seriesName]} labelFormatter={(l) => monthLabel(String(l))} contentStyle={tooltipStyle(resolved)} />
            <Line isAnimationActive={false} type="monotone" dataKey="value" stroke={SERIES[resolved]} strokeWidth={2} dot={{ r: 3 }} activeDot={{ r: 5 }} />
          </LineChart>
        )}
      </div>
      <details className="mt-2 text-sm">
        <summary className="cursor-pointer text-indigo-700 hover:underline dark:text-indigo-300">Show data table</summary>
        <table className="mt-2 w-full text-left">
          <caption className="sr-only">{title}</caption>
          <thead>
            <tr>
              <th scope="col" className="py-1 pr-4 font-medium">Month</th>
              <th scope="col" className="py-1 font-medium">{seriesName}</th>
            </tr>
          </thead>
          <tbody>
            {data.map((d) => (
              <tr key={d.month} className="border-t border-slate-100 dark:border-slate-800">
                <td className="py-1 pr-4">{monthLabel(d.month)}</td>
                <td className="py-1 tabular-nums">{pct(d.value)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </details>
    </figure>
  )
}
