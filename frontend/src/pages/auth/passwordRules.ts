// Mirrors the server's password policy (backend/app/core/passwords.py); the server re-checks.
export const PASSWORD_MIN = 12
export const PASSWORD_MAX = 128

export const PASSWORD_RULES: { id: string; label: string; test: (value: string) => boolean }[] = [
  { id: 'length', label: `${PASSWORD_MIN}–${PASSWORD_MAX} characters`, test: (v) => v.length >= PASSWORD_MIN && v.length <= PASSWORD_MAX },
  { id: 'upper', label: 'An upper-case letter', test: (v) => /[A-Z]/.test(v) },
  { id: 'lower', label: 'A lower-case letter', test: (v) => /[a-z]/.test(v) },
  { id: 'digit', label: 'A digit', test: (v) => /\d/.test(v) },
]

export function passwordProblems(value: string): string[] {
  return PASSWORD_RULES.filter((rule) => !rule.test(value)).map((rule) => rule.label.toLowerCase())
}
