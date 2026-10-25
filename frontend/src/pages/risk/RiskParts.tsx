import { Badge, type BadgeTone } from '@/components/ui'
import { percent } from '@/lib/format'
import type { CiValue, RiskBand, RiskModelInfo } from '@/lib/types'

const BAND: Record<RiskBand, { tone: BadgeTone; label: string }> = {
  high: { tone: 'red', label: 'High' },
  medium: { tone: 'amber', label: 'Medium' },
  low: { tone: 'green', label: 'Low' },
}

/** The band is always written out; colour is never the only signal. */
export function BandBadge({ band }: { band: RiskBand | null }) {
  if (!band) return <Badge tone="slate">Not scored</Badge>
  return <Badge tone={BAND[band].tone}>{BAND[band].label} risk</Badge>
}

/** Visible on every early-warning screen. */
export function RiskDisclaimer({ model }: { model: RiskModelInfo }) {
  return (
    <div role="note" className="mb-6 rounded-xl border border-amber-300 bg-amber-50 p-4 text-sm text-amber-950 dark:border-amber-700 dark:bg-amber-950/60 dark:text-amber-100">
      <p className="font-semibold">Decision support; review with the student's context.</p>
      <p className="mt-1">{model.disclaimer}</p>
      {model.data_notice && (
        <p className="mt-2">
          <span className="mr-2 inline-flex rounded-full bg-amber-200 px-2 py-0.5 text-xs font-semibold tracking-wide text-amber-950 uppercase dark:bg-amber-800 dark:text-amber-50">
            Demo — synthetic data
          </span>
          {model.data_notice}
        </p>
      )}
    </div>
  )
}

const ci = (v?: CiValue) => (v ? `${v.estimate.toFixed(2)} (95% CI ${v.ci_low.toFixed(2)}–${v.ci_high.toFixed(2)})` : '—')

export function ModelDetails({ model }: { model: RiskModelInfo }) {
  return (
    <details className="card mt-6 p-4 text-sm">
      <summary className="cursor-pointer font-medium">About this model (v{model.version})</summary>
      <dl className="mt-3 grid grid-cols-1 gap-3 sm:grid-cols-2">
        <div>
          <dt className="text-xs text-slate-600 uppercase dark:text-slate-400">Prediction moment</dt>
          <dd>{model.prediction_moment}</dd>
        </div>
        <div>
          <dt className="text-xs text-slate-600 uppercase dark:text-slate-400">Bands</dt>
          <dd>
            High ≥ {percent(model.thresholds.high)} · Medium ≥ {percent(model.thresholds.medium)} · Low below
          </dd>
        </div>
        <div>
          <dt className="text-xs text-slate-600 uppercase dark:text-slate-400">Average precision (test)</dt>
          <dd>{ci(model.evaluation.average_precision)}</dd>
        </div>
        <div>
          <dt className="text-xs text-slate-600 uppercase dark:text-slate-400">Recall / precision at “high”</dt>
          <dd>
            {ci(model.evaluation.recall)} / {ci(model.evaluation.precision)}
          </dd>
        </div>
        <div className="sm:col-span-2">
          <dt className="text-xs text-slate-600 uppercase dark:text-slate-400">Training data</dt>
          <dd>{model.training_data}</dd>
        </div>
      </dl>
    </details>
  )
}
