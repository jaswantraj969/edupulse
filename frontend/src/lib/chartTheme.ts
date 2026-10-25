// Chart colours. The series colours were validated with the dataviz palette checker against each
// card surface (white in light mode, slate-900 in dark mode): lightness band, chroma and >= 3:1.
export const SERIES = { light: '#4f46e5', dark: '#6366f1' } as const

export const INK = {
  light: { grid: '#e2e8f0', axis: '#475569', tooltipBg: '#ffffff', tooltipBorder: '#cbd5e1', text: '#0f172a', marker: '#64748b' },
  dark: { grid: '#1e293b', axis: '#94a3b8', tooltipBg: '#0f172a', tooltipBorder: '#334155', text: '#f1f5f9', marker: '#94a3b8' },
} as const

export const tooltipStyle = (mode: 'light' | 'dark') => ({
  background: INK[mode].tooltipBg,
  border: `1px solid ${INK[mode].tooltipBorder}`,
  borderRadius: 8,
  color: INK[mode].text,
})
