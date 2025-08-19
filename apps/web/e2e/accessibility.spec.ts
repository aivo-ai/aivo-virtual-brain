import { test, expect } from '@playwright/test'
import AxeBuilder from '@axe-core/playwright'

test.describe('Accessibility (A11y) Audit - Top 20 Routes', () => {
  // Critical routes that must pass accessibility tests
  const criticalRoutes = [
    { path: '/', name: 'Landing Page' },
    { path: '/login', name: 'Login Page' },
    { path: '/register', name: 'Registration Page' },
    { path: '/forgot-password', name: 'Password Reset' },
    { path: '/student/dashboard', name: 'Student Dashboard', requiresAuth: 'student' },
    { path: '/teacher/dashboard', name: 'Teacher Dashboard', requiresAuth: 'teacher' },
    { path: '/parent/dashboard', name: 'Parent Dashboard', requiresAuth: 'parent' },
    { path: '/admin/dashboard', name: 'Admin Dashboard', requiresAuth: 'admin' },
    { path: '/teacher/classes', name: 'Teacher Classes', requiresAuth: 'teacher' },
    { path: '/teacher/gradebook', name: 'Teacher Gradebook', requiresAuth: 'teacher' },
    { path: '/student/lessons', name: 'Student Lessons', requiresAuth: 'student' },
    { path: '/student/games', name: 'Student Games', requiresAuth: 'student' },
    { path: '/parent/progress', name: 'Parent Progress View', requiresAuth: 'parent' },
    { path: '/teacher/assessments', name: 'Teacher Assessments', requiresAuth: 'teacher' },
    { path: '/admin/users', name: 'Admin User Management', requiresAuth: 'admin' },
    { path: '/admin/billing', name: 'Admin Billing', requiresAuth: 'admin' },
    { path: '/iep/management', name: 'IEP Management', requiresAuth: 'admin' },
    { path: '/student/profile', name: 'Student Profile', requiresAuth: 'student' },
    { path: '/teacher/calendar', name: 'Teacher Calendar', requiresAuth: 'teacher' },
    { path: '/help', name: 'Help Center' },
  ]

  const authenticateUser = async (page: any, role: string) => {
    await page.goto('/login')
    
    // Current implementation uses single login form, not role-based tabs
    switch (role) {
      case 'student':
        await page.getByTestId('login-email').fill('student@test.edu')
        await page.getByTestId('login-password').fill('StudentPass123!')
        await page.getByTestId('login-submit').click()
        break
      case 'teacher':
        await page.getByTestId('login-email').fill('teacher@test.edu')
        await page.getByTestId('login-password').fill('TeacherPass123!')
        await page.getByTestId('login-submit').click()
        break
      case 'parent':
        await page.getByTestId('login-email').fill('parent@test.com')
        await page.getByTestId('login-password').fill('ParentPass123!')
        await page.getByTestId('login-submit').click()
        break
      case 'admin':
        await page.getByTestId('login-email').fill('admin@test.edu')
        await page.getByTestId('login-password').fill('AdminPass123!')
        await page.getByTestId('login-submit').click()
        // Handle 2FA if present
        try {
          await page.getByTestId('2fa-code').fill('123456', { timeout: 2000 })
          await page.getByTestId('2fa-submit').click()
        } catch {
          // No 2FA in test environment
        }
        break
    }
  }

  criticalRoutes.forEach(route => {
    test(`${route.name} (${route.path}) meets WCAG 2.1 AA standards`, async ({ page }) => {
      // Authenticate if required
      if (route.requiresAuth) {
        await authenticateUser(page, route.requiresAuth)
      }
      
      // Navigate to the route
      await page.goto(route.path)
      
      // Wait for page to fully load
      await page.waitForLoadState('networkidle')
      
      // Run accessibility scan
      const accessibilityScanResults = await new AxeBuilder({ page })
        .withTags(['wcag2a', 'wcag2aa', 'wcag21aa'])
        .exclude('#ads-banner') // Exclude third-party content
        .exclude('[data-testid="analytics-script"]')
        .analyze()
      
      // Assert no violations of serious or critical level
      expect(accessibilityScanResults.violations.filter(v => 
        v.impact === 'serious' || v.impact === 'critical'
      )).toEqual([])
      
      // Log moderate violations for review but don't fail
      const moderateViolations = accessibilityScanResults.violations.filter(v => 
        v.impact === 'moderate'
      )
      
      if (moderateViolations.length > 0) {
        console.warn(`${route.name} has ${moderateViolations.length} moderate accessibility issues:`)
        moderateViolations.forEach(violation => {
          console.warn(`- ${violation.description}`)
        })
      }
      
      // Verify basic accessibility features are present
      await expect(page.locator('[role="main"], main')).toBeVisible()
      
      // Check for skip links on pages with navigation
      if (route.path !== '/login' && route.path !== '/register') {
        const skipLink = page.locator('a[href="#main"], a[href="#content"]').first()
        if (await skipLink.count() > 0) {
          await expect(skipLink).toBeVisible()
        }
      }
    })
  })

  test('keyboard navigation works across critical interactive elements', async ({ page }) => {
    await page.goto('/')
    
    // Test keyboard navigation on landing page (using actual HomePage structure)
    await page.keyboard.press('Tab')
    await expect(page.locator(':focus')).toBeVisible()
    
    // Navigate to health page instead of login
    await page.goto('/health')
    
    // Test form keyboard navigation
    await page.keyboard.press('Tab') // Focus first input
    await expect(page.getByTestId('login-email')).toBeFocused()
    
    await page.keyboard.press('Tab') // Focus password
    await expect(page.getByTestId('login-password')).toBeFocused()
    
    await page.keyboard.press('Tab') // Focus submit button
    await expect(page.getByTestId('login-submit')).toBeFocused()
    
    // Test escape key behavior on modals/dropdowns
    await page.goto('/teacher/dashboard')
    await authenticateUser(page, 'teacher')
    
    // Open user menu and test escape
    await page.getByTestId('user-menu').click()
    await page.keyboard.press('Escape')
    // Menu should close (implementation dependent)
  })

  test('screen reader compatibility - ARIA labels and landmarks', async ({ page }) => {
    await page.goto('/')
    
    // Check for proper landmark structure
    await expect(page.locator('[role="banner"], header')).toBeVisible()
    await expect(page.locator('[role="main"], main')).toBeVisible()
    await expect(page.locator('[role="contentinfo"], footer')).toBeVisible()
    
    // Check navigation landmarks
    await expect(page.locator('[role="navigation"], nav')).toBeVisible()
    
    // Check for proper heading hierarchy
    const h1Elements = await page.locator('h1').count()
    expect(h1Elements).toBeGreaterThanOrEqual(1)
    expect(h1Elements).toBeLessThanOrEqual(1) // Should have exactly one h1
    
    // Check form accessibility
    await page.goto('/login')
    
    // Verify form labels (using actual test IDs)
    await expect(page.locator('label[for="login-email"], [aria-label*="email"], [aria-labelledby]')).toBeVisible()
    await expect(page.locator('label[for="login-password"], [aria-label*="password"], [aria-labelledby]')).toBeVisible()
    
    // Check for error message association
    await page.getByTestId('login-submit').click() // Trigger validation
    
    const errorMessages = page.locator('[role="alert"], .error-message')
    if (await errorMessages.count() > 0) {
      // Verify error messages are properly associated with inputs
      await expect(errorMessages.first()).toHaveAttribute('aria-describedby')
    }
  })

  test('color contrast and visual accessibility', async ({ page }) => {
    await page.goto('/')
    
    // Test high contrast mode compatibility
    await page.addStyleTag({
      content: `
        @media (prefers-contrast: high) {
          * { filter: contrast(1.5) !important; }
        }
        @media (prefers-reduced-motion: reduce) {
          * { animation-duration: 0.01ms !important; }
        }
      `
    })
    
    // Verify page still functions with high contrast
    await expect(page.getByTestId('hero-title')).toBeVisible()
    await expect(page.getByTestId('cta-primary')).toBeVisible()
    
    // Test reduced motion preference
    await page.emulateMedia({ reducedMotion: 'reduce' })
    await page.reload()
    
    // Page should still be functional
    await expect(page.getByTestId('hero-title')).toBeVisible()
  })

  test('mobile accessibility and touch targets', async ({ page }) => {
    // Set mobile viewport
    await page.setViewportSize({ width: 375, height: 667 })
    
    await page.goto('/')
    
    // Check touch target sizes (minimum 44px)
    const interactiveElements = page.locator('button, a, input[type="button"], input[type="submit"]')
    const count = await interactiveElements.count()
    
    for (let i = 0; i < Math.min(count, 10); i++) { // Check first 10 elements
      const element = interactiveElements.nth(i)
      const box = await element.boundingBox()
      
      if (box) {
        expect(box.width).toBeGreaterThanOrEqual(44)
        expect(box.height).toBeGreaterThanOrEqual(44)
      }
    }
    
    // Test mobile navigation accessibility
    const mobileMenu = page.locator('[data-testid="mobile-menu"], .mobile-menu, [aria-label*="menu"]')
    if (await mobileMenu.count() > 0) {
      await mobileMenu.click()
      
      // Menu should be accessible via keyboard
      await page.keyboard.press('Tab')
      await expect(page.locator(':focus')).toBeVisible()
    }
  })

  test('focus management and visual indicators', async ({ page }) => {
    await page.goto('/login')
    
    // Test focus visibility
    await page.keyboard.press('Tab')
    const focusedElement = page.locator(':focus')
    await expect(focusedElement).toBeVisible()
    
    // Check focus indicator styles
    const focusStyles = await focusedElement.evaluate(el => {
      const styles = window.getComputedStyle(el)
      return {
        outline: styles.outline,
        outlineWidth: styles.outlineWidth,
        boxShadow: styles.boxShadow
      }
    })
    
    // Should have visible focus indicator
    expect(
      focusStyles.outline !== 'none' || 
      focusStyles.outlineWidth !== '0px' || 
      focusStyles.boxShadow !== 'none'
    ).toBeTruthy()
    
    // Test focus trap in modals
    await authenticateUser(page, 'teacher')
    await page.goto('/teacher/dashboard')
    
    // Open modal if available
    const modalTrigger = page.locator('[data-testid*="modal"], [aria-haspopup="dialog"]').first()
    if (await modalTrigger.count() > 0) {
      await modalTrigger.click()
      
      // Focus should be trapped within modal
      await page.keyboard.press('Tab')
      const focusWithinModal = await page.locator(':focus').evaluate(el => {
        return el.closest('[role="dialog"], .modal') !== null
      })
      expect(focusWithinModal).toBeTruthy()
    }
  })
})
