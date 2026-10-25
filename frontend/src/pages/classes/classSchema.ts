import { z } from 'zod'

export const classSchema = z
  .object({
    academic_year_id: z.string().min(1, 'Choose an academic year'),
    grade_level: z.coerce.number<string>().int().min(1, 'Grade 1–13').max(13, 'Grade 1–13'),
    section: z.string().trim().regex(/^[A-Za-z0-9]{1,5}$/, '1–5 letters or digits'),
    room: z.string().trim().max(20),
    homeroom_teacher_id: z.string(),
  })
  .transform((v) => ({
    academic_year_id: Number(v.academic_year_id),
    grade_level: v.grade_level,
    section: v.section.toUpperCase(),
    room: v.room || null,
    homeroom_teacher_id: v.homeroom_teacher_id ? Number(v.homeroom_teacher_id) : null,
  }))
export type ClassFormValues = z.input<typeof classSchema>
