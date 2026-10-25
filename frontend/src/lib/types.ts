// Types mirroring the backend's Pydantic schemas (backend/app/schemas).

export type Role = 'admin' | 'teacher'
export type StudentStatus = 'active' | 'inactive' | 'graduated' | 'withdrawn'
export type AttendanceStatus = 'present' | 'absent' | 'late' | 'excused'
export type AssessmentKind = 'quiz' | 'test' | 'exam' | 'assignment' | 'project'

export interface Page<T> {
  items: T[]
  total: number
  page: number
  page_size: number
}

export interface ListParams {
  page?: number
  page_size?: number
  sort?: string
  order?: 'asc' | 'desc'
  q?: string
  [filter: string]: string | number | boolean | undefined
}

export interface User {
  id: number
  email: string
  full_name: string
  role: Role
  is_active: boolean
  teacher_id: number | null
  last_login_at: string | null
}

export interface TokenResponse {
  access_token: string
  token_type: string
  expires_in: number
  // The refresh token is never in a response body: it is an httpOnly, Secure, SameSite=Strict cookie.
}

export interface Student {
  id: number
  student_no: string
  first_name: string
  last_name: string
  date_of_birth: string
  email: string | null
  phone: string | null
  guardian_name: string | null
  guardian_phone: string | null
  enrolled_on: string
  status: StudentStatus
  prior_failures: number
  class_id: number | null
  class_name: string | null
  created_at: string
  updated_at: string
}

export interface StudentBrief {
  id: number
  student_no: string
  first_name: string
  last_name: string
}

export interface Teacher {
  id: number
  employee_no: string
  first_name: string
  last_name: string
  email: string
  phone: string | null
  hire_date: string
  specialization: string | null
  is_active: boolean
  has_account: boolean
}

export interface StaffMember {
  id: number
  employee_no: string
  first_name: string
  last_name: string
  email: string
  phone: string | null
  job_title: string
  department: string
  hire_date: string
  is_active: boolean
}

export interface ClassGroup {
  id: number
  name: string
  grade_level: number
  section: string
  room: string | null
  academic_year_id: number
  academic_year: string
  homeroom_teacher_id: number | null
  homeroom_teacher_name: string | null
  student_count: number
}

export interface Subject {
  id: number
  code: string
  name: string
}

export interface Term {
  id: number
  number: number
  name: string
  start_date: string
  end_date: string
}

export interface AcademicYear {
  id: number
  name: string
  start_date: string
  end_date: string
  terms: Term[]
}

export interface Assignment {
  id: number
  class_id: number
  class_name: string
  subject_id: number
  subject_code: string
  subject_name: string
  teacher_id: number
  teacher_name: string
}

export interface AttendanceRow {
  student_id: number
  student_no: string
  first_name: string
  last_name: string
  status: AttendanceStatus | null
  note: string | null
}

export interface AttendanceSheet {
  class_id: number
  class_name: string
  date: string
  records: AttendanceRow[]
}

export interface AttendanceSummary {
  student_id: number
  present: number
  absent: number
  late: number
  excused: number
  total: number
  attendance_rate: number | null
  by_month: { month: string; present: number; absent: number; late: number; excused: number }[]
}

export interface Assessment {
  id: number
  assignment_id: number
  class_id: number
  subject_id: number
  subject_name: string
  teacher_id: number
  term_id: number
  term_name: string
  title: string
  kind: AssessmentKind
  max_score: number
  weight: number
  assessed_on: string
  graded_count: number
}

export interface GradeRow {
  student_id: number
  student_no: string
  first_name: string
  last_name: string
  score: number | null
  comment: string | null
}

export interface GradeSheet {
  assessment: Assessment
  grades: GradeRow[]
}

export interface StudentGrade {
  assessment_id: number
  title: string
  kind: AssessmentKind
  subject_name: string
  term_number: number
  assessed_on: string
  score: number
  max_score: number
  percentage: number
}

export interface DashboardSummary {
  scope: 'school' | 'my_classes'
  counts: { students: number; teachers: number; staff: number; classes: number }
  attendance_trend: { week_start: string; attendance_rate: number; records: number }[]
  grade_distribution: { label: string; students: number }[]
}

export interface RowError {
  row: number
  field: string | null
  message: string
}

export interface ImportResult {
  dry_run: boolean
  total_rows: number
  created: number
  errors: RowError[]
}

// --- early warning ---------------------------------------------------------------------------

export type RiskBand = 'high' | 'medium' | 'low'

export interface CiValue {
  estimate: number
  ci_low: number
  ci_high: number
}

export interface RiskModelInfo {
  version: string
  model_type: string
  trained_at: string
  prediction_moment: string
  thresholds: { high: number; medium: number }
  evaluation: {
    dataset?: string
    test_rows?: number
    average_precision?: CiValue
    roc_auc?: CiValue
    precision?: CiValue
    recall?: CiValue
  }
  training_data: string
  disclaimer: string
  data_notice: string | null
}

export interface RiskInputs {
  g1: number | null
  absences_term1: number
  absences_projected: number
  failures: number
  assessments_term1: number
}

export interface RiskFactor {
  feature: string
  label: string
  value: number
  contribution: number
  direction: 'raises' | 'lowers'
  text: string
}

export interface StudentRiskRow {
  student_id: number
  student_no: string
  first_name: string
  last_name: string
  status: 'scored' | 'insufficient_data'
  probability: number | null
  band: RiskBand | null
  top_factor: string | null
  inputs: RiskInputs | null
}

export interface ClassRisk {
  class_id: number
  class_name: string
  as_of: string
  model: RiskModelInfo
  students: StudentRiskRow[]
}

export interface StudentRisk extends Omit<StudentRiskRow, 'top_factor'> {
  class_id: number | null
  class_name: string | null
  as_of: string | null
  factors: RiskFactor[]
  model: RiskModelInfo
}

export interface AuditLogEntry {
  id: number
  created_at: string
  user_id: number | null
  user_email: string
  action: 'risk.view_class' | 'risk.view_student' | 'risk.export_class'
  target_type: string
  target_id: number
  detail: string | null
  ip_address: string | null
}
