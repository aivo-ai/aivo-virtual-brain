/**
 * Route Manifest - All valid routes in the application
 * This is used by the CTA guard to ensure all links point to valid routes
 */
export const ROUTES = {
  // Public routes
  HOME: '/',
  LOGIN: '/login',
  REGISTER: '/register',
  RESET_PASSWORD: '/reset-password',
  TWO_FA_SETUP: '/2fa-setup',

  // Onboarding
  ONBOARDING: '/onboarding',
  ONBOARDING_ROLE: '/onboarding/role',
  ONBOARDING_PROFILE: '/onboarding/profile',
  ONBOARDING_COMPLETE: '/onboarding/complete',

  // Dashboard
  DASHBOARD: '/dashboard',

  // Learners
  LEARNERS: '/learners',
  LEARNER_DETAIL: '/learners/:id',
  LEARNER_PROGRESS: '/learners/:id/progress',
  LEARNER_ASSESSMENTS: '/learners/:id/assessments',
  LEARNER_GOALS: '/learners/:id/goals',

  // District admin
  DISTRICT: '/district',
  DISTRICT_OVERVIEW: '/district/overview',
  DISTRICT_SCHOOLS: '/district/schools',
  DISTRICT_TEACHERS: '/district/teachers',
  DISTRICT_REPORTS: '/district/reports',
  DISTRICT_SETTINGS: '/district/settings',

  // Teacher
  TEACHER: '/teacher',
  TEACHER_CLASSES: '/teacher/classes',
  TEACHER_STUDENTS: '/teacher/students',
  TEACHER_ASSIGNMENTS: '/teacher/assignments',
  TEACHER_REPORTS: '/teacher/reports',

  // Search
  SEARCH: '/search',

  // Coursework
  COURSEWORK: '/coursework',
  COURSEWORK_UPLOAD: '/coursework/upload',
  COURSEWORK_REVIEW: '/coursework/review',
  COURSEWORK_CONFIRM: '/coursework/confirm',
  COURSEWORK_DETAIL: '/coursework/:id',

  // IEP Management
  IEP_EDITOR: '/iep/:learnerId/editor',
  IEP_ASSISTANT: '/iep/:learnerId/assistant',
  IEP_REVIEW: '/iep/:learnerId/review',
  IEP_APPROVALS: '/iep/:learnerId/approvals',

  // Legacy/dev routes
  HEALTH: '/health',
  DEV_MOCKS: '/_dev/mocks',
} as const

export type Route = (typeof ROUTES)[keyof typeof ROUTES]

// Role-based route groups
export const PUBLIC_ROUTES = [
  ROUTES.HOME,
  ROUTES.LOGIN,
  ROUTES.REGISTER,
  ROUTES.HEALTH,
  ROUTES.DEV_MOCKS,
] as const

export const ONBOARDING_ROUTES = [
  ROUTES.ONBOARDING,
  ROUTES.ONBOARDING_ROLE,
  ROUTES.ONBOARDING_PROFILE,
  ROUTES.ONBOARDING_COMPLETE,
] as const

export const PARENT_ROUTES = [
  ROUTES.DASHBOARD,
  ROUTES.LEARNERS,
  ROUTES.LEARNER_DETAIL,
  ROUTES.LEARNER_PROGRESS,
  ROUTES.LEARNER_ASSESSMENTS,
  ROUTES.LEARNER_GOALS,
  ROUTES.SEARCH,
  ROUTES.COURSEWORK,
  ROUTES.COURSEWORK_UPLOAD,
  ROUTES.COURSEWORK_REVIEW,
  ROUTES.COURSEWORK_CONFIRM,
  ROUTES.COURSEWORK_DETAIL,
] as const

export const TEACHER_ROUTES = [
  ROUTES.DASHBOARD,
  ROUTES.TEACHER,
  ROUTES.TEACHER_CLASSES,
  ROUTES.TEACHER_STUDENTS,
  ROUTES.TEACHER_ASSIGNMENTS,
  ROUTES.TEACHER_REPORTS,
  ROUTES.SEARCH,
  ROUTES.COURSEWORK,
  ROUTES.COURSEWORK_UPLOAD,
  ROUTES.COURSEWORK_REVIEW,
  ROUTES.COURSEWORK_CONFIRM,
  ROUTES.COURSEWORK_DETAIL,
  ROUTES.IEP_EDITOR,
  ROUTES.IEP_ASSISTANT,
  ROUTES.IEP_REVIEW,
  ROUTES.IEP_APPROVALS,
] as const

export const DISTRICT_ADMIN_ROUTES = [
  ROUTES.DASHBOARD,
  ROUTES.DISTRICT,
  ROUTES.DISTRICT_OVERVIEW,
  ROUTES.DISTRICT_SCHOOLS,
  ROUTES.DISTRICT_TEACHERS,
  ROUTES.DISTRICT_REPORTS,
  ROUTES.DISTRICT_SETTINGS,
  ROUTES.SEARCH,
] as const

// User roles
export type UserRole = 'parent' | 'teacher' | 'district_admin'

// Dashboard context
export type DashContext = 'parent' | 'teacher' | 'district'

// Route manifest type
export type RouteManifest = Route

// Helper functions
export function isValidRoute(path: string): path is RouteManifest {
  return Object.values(ROUTES).includes(path as Route)
}

export function getAllRoutes(): RouteManifest[] {
  return Object.values(ROUTES)
}

export function isPublicRoute(path: string): boolean {
  return PUBLIC_ROUTES.some(route => path === route || path.startsWith(route))
}

export function getRoutesForRole(role: UserRole): readonly Route[] {
  switch (role) {
    case 'parent':
      return PARENT_ROUTES
    case 'teacher':
      return TEACHER_ROUTES
    case 'district_admin':
      return DISTRICT_ADMIN_ROUTES
    default:
      return []
  }
}

export function canAccessRoute(path: string, userRole?: UserRole): boolean {
  if (isPublicRoute(path)) {
    return true
  }

  if (!userRole) {
    return false
  }

  const allowedRoutes = getRoutesForRole(userRole)
  return allowedRoutes.some(route => {
    // Handle dynamic routes with params
    const routePattern = route.replace(/:[\w]+/g, '[^/]+')
    const regex = new RegExp(`^${routePattern}$`)
    return regex.test(path)
  })
}

// Route building helpers
export function buildLearnerRoute(learnerId: string, section?: string): string {
  const base = ROUTES.LEARNER_DETAIL.replace(':id', learnerId)
  if (section) {
    return `${base}/${section}`
  }
  return base
}

export function buildDistrictRoute(section?: string): string {
  if (!section) return ROUTES.DISTRICT
  return `${ROUTES.DISTRICT}/${section}`
}

export function buildTeacherRoute(section?: string): string {
  if (!section) return ROUTES.TEACHER
  return `${ROUTES.TEACHER}/${section}`
}

// IEP route building helpers
export function buildIEPRoute(
  learnerId: string,
  section: 'editor' | 'assistant' | 'review' | 'approvals'
): string {
  switch (section) {
    case 'editor':
      return ROUTES.IEP_EDITOR.replace(':learnerId', learnerId)
    case 'assistant':
      return ROUTES.IEP_ASSISTANT.replace(':learnerId', learnerId)
    case 'review':
      return ROUTES.IEP_REVIEW.replace(':learnerId', learnerId)
    case 'approvals':
      return ROUTES.IEP_APPROVALS.replace(':learnerId', learnerId)
    default:
      return ROUTES.IEP_EDITOR.replace(':learnerId', learnerId)
  }
}
