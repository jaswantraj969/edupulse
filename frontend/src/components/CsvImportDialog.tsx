import { useQueryClient } from '@tanstack/react-query'
import { useId, useState } from 'react'
import { ApiError, api, errorMessage } from '@/lib/api'
import { useToast } from '@/lib/toast'
import type { ImportResult, RowError } from '@/lib/types'
import { Dialog } from './Dialog'
import { Button } from './ui'

interface Props {
  open: boolean
  onClose: () => void
  resource: 'students' | 'teachers' | 'staff'
}

/** Two-step import: validate (dry run) first, then import. Row errors are listed per line. */
export function CsvImportDialog({ open, onClose, resource }: Props) {
  const inputId = useId()
  const toast = useToast()
  const queryClient = useQueryClient()
  const [file, setFile] = useState<File | null>(null)
  const [busy, setBusy] = useState(false)
  const [rowErrors, setRowErrors] = useState<RowError[]>([])
  const [message, setMessage] = useState<string | null>(null)
  const [validated, setValidated] = useState<ImportResult | null>(null)

  const reset = () => {
    setFile(null)
    setRowErrors([])
    setMessage(null)
    setValidated(null)
  }
  const close = () => {
    reset()
    onClose()
  }

  const run = async (dryRun: boolean) => {
    if (!file) return
    setBusy(true)
    setRowErrors([])
    setMessage(null)
    try {
      const result = await api.upload<ImportResult>(`/${resource}/import?dry_run=${dryRun}`, file)
      if (dryRun) {
        setValidated(result)
      } else {
        toast.success(`Imported ${result.created} ${resource}`)
        await queryClient.invalidateQueries({ queryKey: [resource] })
        close()
      }
    } catch (error) {
      setValidated(null)
      if (error instanceof ApiError && error.code === 'csv_validation_error') {
        setRowErrors((error.details as ImportResult).errors)
      }
      setMessage(errorMessage(error))
    } finally {
      setBusy(false)
    }
  }

  return (
    <Dialog
      open={open}
      title={`Import ${resource} from CSV`}
      onClose={close}
      footer={
        <>
          <Button variant="secondary" onClick={close} disabled={busy}>
            Cancel
          </Button>
          {validated ? (
            <Button onClick={() => void run(false)} loading={busy}>
              Import {validated.total_rows} rows
            </Button>
          ) : (
            <Button onClick={() => void run(true)} loading={busy} disabled={!file}>
              Validate file
            </Button>
          )}
        </>
      }
    >
      <p>
        The file is checked completely first. If any row has a problem, nothing is imported and every problem is listed
        with its line number.
      </p>
      <label htmlFor={inputId} className="mt-4 block text-sm font-medium text-slate-900 dark:text-slate-100">
        CSV file (UTF-8, with header row)
      </label>
      <input
        id={inputId}
        type="file"
        accept=".csv,text/csv"
        className="mt-1 block w-full text-sm file:mr-3 file:rounded-lg file:border-0 file:bg-indigo-50 file:px-3 file:py-2 file:text-indigo-800 dark:file:bg-indigo-950 dark:file:text-indigo-200"
        onChange={(e) => {
          reset()
          setFile(e.target.files?.[0] ?? null)
        }}
      />
      {validated && (
        <p role="status" className="mt-4 rounded-lg bg-emerald-50 px-3 py-2 text-emerald-900 dark:bg-emerald-950 dark:text-emerald-100">
          All {validated.total_rows} rows are valid and ready to import.
        </p>
      )}
      {message && (
        <div role="alert" className="mt-4">
          <p className="font-medium text-red-800 dark:text-red-300">{message}</p>
          {rowErrors.length > 0 && (
            <div tabIndex={0} role="region" aria-label="Rows with errors" className="mt-2 max-h-56 overflow-auto rounded-lg border border-slate-200 dark:border-slate-700">
              <table className="w-full text-left text-xs">
                <caption className="sr-only">Rows with errors</caption>
                <thead className="bg-slate-50 dark:bg-slate-800">
                  <tr>
                    <th scope="col" className="px-3 py-2">Line</th>
                    <th scope="col" className="px-3 py-2">Column</th>
                    <th scope="col" className="px-3 py-2">Problem</th>
                  </tr>
                </thead>
                <tbody>
                  {rowErrors.map((e, i) => (
                    <tr key={i} className="border-t border-slate-200 dark:border-slate-700">
                      <td className="px-3 py-1.5 tabular-nums">{e.row}</td>
                      <td className="px-3 py-1.5 font-mono">{e.field ?? '—'}</td>
                      <td className="px-3 py-1.5">{e.message}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}
    </Dialog>
  )
}
