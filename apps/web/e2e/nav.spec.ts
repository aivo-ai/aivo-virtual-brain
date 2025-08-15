import { test, expect } from '@playwright/test'

test.describe('Navigation', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/')
  })

  test.describe('Top Navigation', () => {
    test('displays main navigation elements', async ({ page }) => {
      // Check logo/brand
      await expect(page.getByTestId('nav-logo-link')).toBeVisible()

      // Check auth buttons for unauthenticated users
      await expect(page.getByTestId('nav-login-link')).toBeVisible()
      await expect(page.getByTestId('nav-register-link')).toBeVisible()

      // Check theme toggle
      await expect(page.getByTestId('nav-theme-toggle')).toBeVisible()
    })

    test('theme toggle works correctly', async ({ page }) => {
      const themeToggle = page.getByTestId('nav-theme-toggle')

      // Should start with light theme
      await expect(page.locator('html')).toHaveClass(/light/)

      // Toggle to dark theme
      await themeToggle.click()
      await expect(page.locator('html')).toHaveClass(/dark/)

      // Toggle to system theme
      await themeToggle.click()
      // System theme class depends on user's system preference

      // Toggle back to light theme
      await themeToggle.click()
      await expect(page.locator('html')).toHaveClass(/light/)
    })

    test('mobile navigation works', async ({ page }) => {
      // Set mobile viewport
      await page.setViewportSize({ width: 375, height: 667 })

      // Mobile menu toggle should be visible
      const mobileToggle = page.getByTestId('nav-mobile-menu-toggle')
      await expect(mobileToggle).toBeVisible()

      // Desktop nav links should be hidden
      await expect(page.getByTestId('nav-login-link')).toBeHidden()

      // Click mobile menu toggle
      await mobileToggle.click()

      // Mobile nav links should be visible
      await expect(page.getByTestId('nav-mobile-login-link')).toBeVisible()
      await expect(page.getByTestId('nav-mobile-register-link')).toBeVisible()

      // Click again to close
      await mobileToggle.click()
      await expect(page.getByTestId('nav-mobile-login-link')).toBeHidden()
    })

    test('navigation links work correctly', async ({ page }) => {
      // Test login link
      await page.getByTestId('nav-login-link').click()
      await expect(page).toHaveURL('/login')
      await expect(page.getByText('Login page - Coming soon!')).toBeVisible()

      // Navigate back to home
      await page.getByTestId('back-to-home').click()
      await expect(page).toHaveURL('/')

      // Test register link
      await page.getByTestId('nav-register-link').click()
      await expect(page).toHaveURL('/register')
      await expect(page.getByText('Register page - Coming soon!')).toBeVisible()
    })
  })

  test.describe('Route Protection', () => {
    test('redirects protected routes to login', async ({ page }) => {
      await page.goto('/dashboard')

      // Should redirect to login page
      await expect(page).toHaveURL('/login')
    })

    test('allows access to public routes', async ({ page }) => {
      await page.goto('/health')
      await expect(page.getByText('Health Check')).toBeVisible()

      await page.goto('/_dev/mocks')
      await expect(page.getByText('Mock Server Interface')).toBeVisible()
    })

    test('shows 404 page for invalid routes', async ({ page }) => {
      await page.goto('/non-existent-route')
      await expect(page.getByText('Page Not Found')).toBeVisible()
    })
  })

  test.describe('Accessibility', () => {
    test('provides keyboard navigation', async ({ page }) => {
      // Tab to skip link
      await page.keyboard.press('Tab')
      await expect(page.getByText('Skip to main content')).toBeFocused()

      // Skip to main content
      await page.keyboard.press('Enter')
      await expect(page.getByRole('main')).toBeFocused()
    })

    test('has proper ARIA labels', async ({ page }) => {
      const nav = page.getByRole('navigation', { name: 'Main navigation' })
      await expect(nav).toBeVisible()

      const mobileToggle = page.getByTestId('nav-mobile-menu-toggle')
      await expect(mobileToggle).toHaveAttribute('aria-label', /toggle.*menu/i)
    })

    test('has proper heading hierarchy', async ({ page }) => {
      // Check that page has proper heading structure
      const h1 = page.locator('h1').first()
      await expect(h1).toBeVisible()
    })
  })

  test.describe('Analytics Integration', () => {
    test('tracks page views', async ({ page }) => {
      // Mock analytics
      await page.addInitScript(() => {
        window.analyticsEvents = []
        window.analytics = {
          track: (event, properties) => {
            window.analyticsEvents.push({ event, properties })
          },
        }
      })

      await page.goto('/')

      // Check that analytics events were tracked
      const events = await page.evaluate(() => window.analyticsEvents)
      expect(events.length).toBeGreaterThan(0)
    })
  })

  test.describe('CTA Guard Compliance', () => {
    test('all navigation links have proper hrefs', async ({ page }) => {
      // Check that all navigation links have valid hrefs
      const links = page.getByRole('link')
      const linkCount = await links.count()

      for (let i = 0; i < linkCount; i++) {
        const link = links.nth(i)
        const href = await link.getAttribute('href')
        expect(href).toBeTruthy()
        expect(href).not.toBe('#')
        expect(href).not.toBe('javascript:void(0)')
      }
    })

    test('all buttons have proper handlers or are submit buttons', async ({
      page,
    }) => {
      // Check that all buttons either have handlers or are submit buttons
      const buttons = page.getByRole('button')
      const buttonCount = await buttons.count()

      for (let i = 0; i < buttonCount; i++) {
        const button = buttons.nth(i)
        const type = await button.getAttribute('type')
        const hasTestId = await button.getAttribute('data-testid')

        // Buttons should either be submit type or have test handlers
        const isValid = type === 'submit' || hasTestId?.includes('button')
        expect(isValid).toBe(true)
      }
    })
  })
})
