/**
 * Route Manifest - All valid routes in the application
 * This is used by the CTA guard to ensure all links point to valid routes
 */
export const ROUTES = {
  HOME: '/',
  HEALTH: '/health',
  DEV_MOCKS: '/_dev/mocks',
} as const

export type Route = (typeof ROUTES)[keyof typeof ROUTES]

// Union type of all valid routes
export type RouteManifest = Route

// Helper to check if a path is a valid route
export function isValidRoute(path: string): path is RouteManifest {
  return Object.values(ROUTES).includes(path as Route)
}

// Get all routes as array for testing
export function getAllRoutes(): RouteManifest[] {
  return Object.values(ROUTES)
}
