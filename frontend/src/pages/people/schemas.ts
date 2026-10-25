import { z } from 'zod'

const code = z.string().trim().regex(/^[A-Za-z0-9-]{2,20}$/, '2–20 letters, digits or hyphens')
const name = (label: string) => z.string().trim().min(1, `${label} is required`).max(100)
const email = z.string().trim().min(1, 'E-mail is required').pipe(z.email('Enter a valid e-mail address'))
const phone = z.union([z.literal(''), z.string().trim().regex(/^[0-9+()\-. ]{5,40}$/, 'Use digits, spaces and + ( ) - . only')])
const date = (label: string) => z.string().min(1, `${label} is required`)
const blankToNull = (v: string) => (v.trim() === '' ? null : v.trim())

export const teacherSchema = z
  .object({
    employee_no: code,
    first_name: name('First name'),
    last_name: name('Last name'),
    email,
    phone,
    hire_date: date('Hire date'),
    specialization: z.string().trim().max(100),
    is_active: z.boolean(),
  })
  .transform((v) => ({ ...v, phone: blankToNull(v.phone), specialization: blankToNull(v.specialization) }))

export type TeacherFormValues = z.input<typeof teacherSchema>

export const staffSchema = z
  .object({
    employee_no: code,
    first_name: name('First name'),
    last_name: name('Last name'),
    email,
    phone,
    job_title: name('Job title'),
    department: name('Department'),
    hire_date: date('Hire date'),
    is_active: z.boolean(),
  })
  .transform((v) => ({ ...v, phone: blankToNull(v.phone) }))

export type StaffFormValues = z.input<typeof staffSchema>
