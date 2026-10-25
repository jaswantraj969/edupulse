import { zodResolver } from '@hookform/resolvers/zod'
import { useId, useState } from 'react'
import { useForm, type FieldValues, type Path, type DefaultValues } from 'react-hook-form'
import type { z } from 'zod'
import { ApiError, errorMessage } from '@/lib/api'
import { Dialog } from './Dialog'
import { FormError, SelectField, TextField } from './Field'
import { Button } from './ui'

export interface FieldSpec<V> {
  name: Path<V>
  label: string
  type?: 'text' | 'email' | 'date' | 'tel' | 'number' | 'select' | 'checkbox'
  required?: boolean
  options?: { value: string | number; label: string }[]
  placeholder?: string
}

interface Props<V extends FieldValues, O> {
  open: boolean
  title: string
  submitLabel: string
  schema: z.ZodType<O, V>
  initial: V
  fields: FieldSpec<V>[]
  onSubmit: (values: O) => Promise<unknown>
  onClose: () => void
}

/** A modal form driven by a field list and a Zod schema; maps server errors onto fields. */
export function RecordFormDialog<V extends FieldValues, O>(props: Props<V, O>) {
  // Mounted only while open, so the form starts from `initial` every time it opens.
  return props.open ? <OpenForm {...props} /> : null
}

function OpenForm<V extends FieldValues, O>({ title, submitLabel, schema, initial, fields, onSubmit, onClose }: Props<V, O>) {
  const formId = useId()
  const [serverError, setServerError] = useState<string | null>(null)
  const {
    register,
    handleSubmit,
    setError,
    formState: { errors, isSubmitting },
  } = useForm<V, unknown, O>({ resolver: zodResolver(schema), defaultValues: initial as DefaultValues<V>, mode: 'onBlur' })

  const names = new Set(fields.map((f) => String(f.name)))
  const submit = handleSubmit(async (values) => {
    setServerError(null)
    try {
      await onSubmit(values)
      onClose()
    } catch (error) {
      if (error instanceof ApiError) {
        for (const [field, message] of Object.entries(error.fieldErrors())) {
          if (names.has(field)) setError(field as Path<V>, { message })
        }
        const conflict = (error.details as { field?: string } | null)?.field
        if (error.status === 409 && conflict && names.has(conflict)) setError(conflict as Path<V>, { message: error.message })
      }
      setServerError(errorMessage(error))
    }
  })

  return (
    <Dialog
      open
      title={title}
      onClose={onClose}
      footer={
        <>
          <Button variant="secondary" onClick={onClose} disabled={isSubmitting}>
            Cancel
          </Button>
          <Button type="submit" form={formId} loading={isSubmitting}>
            {submitLabel}
          </Button>
        </>
      }
    >
      <form id={formId} onSubmit={submit} noValidate className="flex max-h-[60dvh] flex-col gap-4 overflow-y-auto p-1">
        <FormError message={serverError} />
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          {fields.map((field) => {
            const error = errors[field.name] as { message?: string } | undefined
            const fieldError = error?.message ? { type: 'server', message: error.message } : undefined
            if (field.type === 'checkbox') {
              return (
                <label key={field.name} className="flex items-center gap-2 self-end py-2 text-sm font-medium">
                  <input type="checkbox" className="size-4 accent-indigo-600" {...register(field.name)} />
                  {field.label}
                </label>
              )
            }
            if (field.type === 'select') {
              return (
                <SelectField
                  key={field.name}
                  label={field.label}
                  required={field.required}
                  placeholder={field.placeholder}
                  options={field.options ?? []}
                  registration={register(field.name)}
                  error={fieldError}
                />
              )
            }
            return (
              <TextField
                key={field.name}
                label={field.label}
                type={field.type ?? 'text'}
                required={field.required}
                registration={register(field.name)}
                error={fieldError}
              />
            )
          })}
        </div>
      </form>
    </Dialog>
  )
}
