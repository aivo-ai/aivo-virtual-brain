import { test, expect } from '@playwright/test'

test.describe('Route Validation - Current Implementation', () => {
  const baseURL = process.env.PLAYWRIGHT_TEST_BASE_URL || 'http://localhost:3000'
  
  // Define routes that actually exist in the current implementation
  const existingRoutes = [
    { path: '/', title: 'Welcome to Aivo', element: 'get-started-button' },
    { path: '/health', title: 'Health Check', element: 'h1' },
    { path: '/dev-mocks', title: 'Development Mocks', element: 'h1' }
  ]

  test('validate existing routes are accessible', async ({ page }) => {
    for (const route of existingRoutes) {
      await test.step(`Testing route: ${route.path}`, async () => {
        const response = await page.goto(`${baseURL}${route.path}`)
        
        // Verify response is successful
        expect(response?.status()).toBe(200)
        
        // Wait for page to stabilize
        await page.waitForLoadState('networkidle')
        
        // Verify expected content exists
        if (route.element === 'get-started-button') {
          await expect(page.locator('[data-testid="get-started-button"]')).toBeVisible()
        } else if (route.element === 'h1') {
          await expect(page.locator('h1')).toContainText(route.title)
        }
      })
    }
  })

  test('validate unknown routes return 404', async ({ page }) => {
    const unknownRoutes = ['/login', '/dashboard', '/unknown-route', '/student/dashboard']
    
    for (const route of unknownRoutes) {
      await test.step(`Testing unknown route: ${route}`, async () => {
        const response = await page.goto(`${baseURL}${route}`)
        
        // Should be handled by NotFoundPage
        expect(response?.status()).toBe(200) // React Router handles 404s client-side
        
        // Should show 404 content
        await expect(page.locator('h1')).toContainText('404')
      })
    }
  })

  test('validate navigation links work', async ({ page }) => {
    await page.goto(baseURL)
    await page.waitForLoadState('networkidle')
    
    // Test navigation from home page
    await page.locator('[data-testid="health-check-link"]').click()
    await page.waitForLoadState('networkidle')
    await expect(page.locator('h1')).toContainText('Health Check')
    
    // Test back to home
    await page.locator('[data-testid="nav-home-link"]').click()
    await page.waitForLoadState('networkidle')
    await expect(page.locator('[data-testid="get-started-button"]')).toBeVisible()
  })
})
