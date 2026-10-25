// Shared reference-data queries (cached for the session; they rarely change).
import { useQuery } from '@tanstack/react-query'
import { api } from './api'
import type { AcademicYear, ClassGroup, Page, Subject, Teacher } from './types'

const LONG = 5 * 60 * 1000

export function useAllClasses() {
  return useQuery({
    queryKey: ['classes', 'all'],
    queryFn: () => api.get<Page<ClassGroup>>('/classes', { page_size: 100, sort: 'name' }),
    staleTime: LONG,
    select: (page) => page.items,
  })
}

export function useAllTeachers() {
  return useQuery({
    queryKey: ['teachers', 'all'],
    queryFn: () => api.get<Page<Teacher>>('/teachers', { page_size: 100, sort: 'last_name' }),
    staleTime: LONG,
    select: (page) => page.items,
  })
}

export function useSubjects() {
  return useQuery({ queryKey: ['subjects'], queryFn: () => api.get<Subject[]>('/subjects'), staleTime: LONG })
}

export function useAcademicYears() {
  return useQuery({
    queryKey: ['academic-years'],
    queryFn: () => api.get<AcademicYear[]>('/academic-years'),
    staleTime: LONG,
  })
}
