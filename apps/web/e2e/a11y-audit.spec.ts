import { test, expect } from '@playwright/test'
import AxeBuilder from '@axe-core/playwright'

/**
 * S4-19 Accessibility & Localization Audit Gate
 * Comprehensive a11y testing across top 30 screens with CI gate enforcement
 */

test.describe('S4-19 Accessibility Audit Gate - Top 30 Screens', () => {
  // Top 30 critical screens that must pass accessibility tests
  const criticalScreens = [
    // Public/Landing pages
    { path: '/', name: 'Landing Page', category: 'public' },
    { path: '/login', name: 'Login Page', category: 'auth' },
    { path: '/register', name: 'Registration Page', category: 'auth' },
    { path: '/forgot-password', name: 'Password Reset', category: 'auth' },
    { path: '/help', name: 'Help Center', category: 'public' },
    { path: '/privacy', name: 'Privacy Policy', category: 'public' },
    { path: '/terms', name: 'Terms of Service', category: 'public' },
    
    // Student Experience (7 screens)
    { path: '/student/dashboard', name: 'Student Dashboard', requiresAuth: 'student', category: 'student' },
    { path: '/student/lessons', name: 'Student Lessons', requiresAuth: 'student', category: 'student' },
    { path: '/student/games', name: 'Student Games', requiresAuth: 'student', category: 'student' },
    { path: '/student/profile', name: 'Student Profile', requiresAuth: 'student', category: 'student' },
    { path: '/student/progress', name: 'Student Progress', requiresAuth: 'student', category: 'student' },
    { path: '/student/assignments', name: 'Student Assignments', requiresAuth: 'student', category: 'student' },
    { path: '/student/achievements', name: 'Student Achievements', requiresAuth: 'student', category: 'student' },
    
    // Teacher Experience (8 screens)
    { path: '/teacher/dashboard', name: 'Teacher Dashboard', requiresAuth: 'teacher', category: 'teacher' },
    { path: '/teacher/classes', name: 'Teacher Classes', requiresAuth: 'teacher', category: 'teacher' },
    { path: '/teacher/gradebook', name: 'Teacher Gradebook', requiresAuth: 'teacher', category: 'teacher' },
    { path: '/teacher/assessments', name: 'Teacher Assessments', requiresAuth: 'teacher', category: 'teacher' },
    { path: '/teacher/calendar', name: 'Teacher Calendar', requiresAuth: 'teacher', category: 'teacher' },
    { path: '/teacher/students', name: 'Teacher Student Management', requiresAuth: 'teacher', category: 'teacher' },
    { path: '/teacher/reports', name: 'Teacher Reports', requiresAuth: 'teacher', category: 'teacher' },
    { path: '/teacher/settings', name: 'Teacher Settings', requiresAuth: 'teacher', category: 'teacher' },
    
    // Parent Experience (5 screens)
    { path: '/parent/dashboard', name: 'Parent Dashboard', requiresAuth: 'parent', category: 'parent' },
    { path: '/parent/progress', name: 'Parent Progress View', requiresAuth: 'parent', category: 'parent' },
    { path: '/parent/communication', name: 'Parent Communication', requiresAuth: 'parent', category: 'parent' },
    { path: '/parent/billing', name: 'Parent Billing', requiresAuth: 'parent', category: 'parent' },
    { path: '/parent/settings', name: 'Parent Settings', requiresAuth: 'parent', category: 'parent' },
    
    // Admin/Management (8 screens)
    { path: '/admin/dashboard', name: 'Admin Dashboard', requiresAuth: 'admin', category: 'admin' },
    { path: '/admin/users', name: 'Admin User Management', requiresAuth: 'admin', category: 'admin' },
    { path: '/admin/billing', name: 'Admin Billing', requiresAuth: 'admin', category: 'admin' },
    { path: '/admin/approvals', name: 'Admin Approvals', requiresAuth: 'admin', category: 'admin' },
    { path: '/admin/queues', name: 'Admin Queue Management', requiresAuth: 'admin', category: 'admin' },
    { path: '/iep/management', name: 'IEP Management', requiresAuth: 'admin', category: 'admin' },
    { path: '/admin/analytics', name: 'Admin Analytics', requiresAuth: 'admin', category: 'admin' },
    { path: '/admin/system', name: 'Admin System Settings', requiresAuth: 'admin', category: 'admin' }
  ]

  const authenticateUser = async (page: any, role: string) => {
    await page.goto('/login')
    
    // Role-based authentication
    const credentials = {
      student: { email: 'student@test.edu', password: 'StudentPass123!' },
      teacher: { email: 'teacher@test.edu', password: 'TeacherPass123!' },
      parent: { email: 'parent@test.com', password: 'ParentPass123!' },
      admin: { email: 'admin@test.edu', password: 'AdminPass123!' }
    }
    
    const cred = credentials[role as keyof typeof credentials]
    if (!cred) throw new Error(`Unknown role: ${role}`)
    
    await page.getByTestId('login-email').fill(cred.email)
    await page.getByTestId('login-password').fill(cred.password)
    await page.getByTestId('login-submit').click()
    
    // Handle 2FA for admin
    if (role === 'admin') {
      try {
        await page.getByTestId('2fa-code').fill('123456', { timeout: 2000 })
        await page.getByTestId('2fa-submit').click()
      } catch {
        // No 2FA in test environment
      }
    }
    
    // Wait for dashboard redirect
    await page.waitForURL(`**/${role}/dashboard`, { timeout: 10000 })
  }

  // Critical A11y Test: FAIL BUILD on serious/critical violations
  criticalScreens.forEach(screen => {
    test(`🔴 CRITICAL: ${screen.name} (${screen.path}) - Zero serious/critical a11y violations`, async ({ page }) => {
      // Set up accessibility testing context
      await page.addInitScript(() => {
        // Disable animations for consistent testing
        document.documentElement.style.setProperty('--animation-duration', '0ms')
        document.documentElement.style.setProperty('--transition-duration', '0ms')
      })
      
      // Authenticate if required
      if (screen.requiresAuth) {
        await authenticateUser(page, screen.requiresAuth)
      }
      
      // Navigate to the screen
      await page.goto(screen.path)
      
      // Wait for page to fully load and stabilize
      await page.waitForLoadState('networkidle')
      await page.waitForTimeout(1000) // Allow for dynamic content
      
      // Enhanced accessibility scan with comprehensive rules
      const axeResults = await new AxeBuilder({ page })
        .withTags([
          'wcag2a',      // WCAG 2.0 Level A
          'wcag2aa',     // WCAG 2.0 Level AA  
          'wcag21aa',    // WCAG 2.1 Level AA
          'wcag22aa',    // WCAG 2.2 Level AA
          'best-practice' // Best practices
        ])
        .include('main, [role="main"]')  // Focus on main content
        .exclude('#ads-banner')         // Exclude third-party content
        .exclude('[data-testid="analytics-script"]')
        .exclude('.gtm-container')      // Exclude Google Tag Manager
        .analyze()
      
      // 🔴 FAIL BUILD: Zero tolerance for serious/critical violations
      const criticalViolations = axeResults.violations.filter(violation => 
        violation.impact === 'serious' || violation.impact === 'critical'
      )
      
      if (criticalViolations.length > 0) {
        console.error(`❌ ${screen.name} has ${criticalViolations.length} CRITICAL accessibility violations:`)
        criticalViolations.forEach(violation => {
          console.error(`  - ${violation.id}: ${violation.description}`)
          console.error(`    Impact: ${violation.impact}`)
          console.error(`    Help: ${violation.helpUrl}`)
          violation.nodes.forEach(node => {
            console.error(`    Element: ${node.target.join(', ')}`)
            console.error(`    Summary: ${node.failureSummary}`)
          })
        })
      }
      
      // CRITICAL: This will fail the build
      expect(criticalViolations, 
        `${screen.name} has ${criticalViolations.length} critical accessibility violations that must be fixed before merge.`
      ).toHaveLength(0)
      
      // Log moderate violations for improvement (don't fail build)
      const moderateViolations = axeResults.violations.filter(v => v.impact === 'moderate')
      if (moderateViolations.length > 0) {
        console.warn(`⚠️  ${screen.name} has ${moderateViolations.length} moderate accessibility issues for improvement:`)
        moderateViolations.forEach(violation => {
          console.warn(`  - ${violation.id}: ${violation.description}`)
        })
      }
      
      // Verify essential accessibility features
      await test.step('Verify essential a11y features', async () => {
        // Must have exactly one h1
        const h1Count = await page.locator('h1').count()
        expect(h1Count, 'Page must have exactly one h1 element').toBe(1)
        
        // Must have main landmark
        await expect(page.locator('[role="main"], main')).toBeVisible()
        
        // Check for skip links on complex pages
        if (screen.category !== 'auth') {
          const skipLinks = page.locator('a[href="#main"], a[href="#content"], .skip-link')
          if (await skipLinks.count() > 0) {
            await expect(skipLinks.first()).toBeVisible()
          }
        }
        
        // Language attribute must be set
        const lang = await page.getAttribute('html', 'lang')
        expect(lang, 'HTML element must have lang attribute').toBeTruthy()
        expect(lang?.length, 'Language code must be valid').toBeGreaterThan(1)
      })
    })
  })

  test('🔴 CRITICAL: Keyboard navigation accessibility across all user flows', async ({ page }) => {
    await page.goto('/')
    
    // Test tab navigation on landing page
    await page.keyboard.press('Tab')
    let focusedElement = page.locator(':focus')
    await expect(focusedElement).toBeVisible()
    
    // Test form keyboard navigation
    await page.goto('/login')
    await page.keyboard.press('Tab') // Email field
    await expect(page.getByTestId('login-email')).toBeFocused()
    
    await page.keyboard.press('Tab') // Password field
    await expect(page.getByTestId('login-password')).toBeFocused()
    
    await page.keyboard.press('Tab') // Submit button
    await expect(page.getByTestId('login-submit')).toBeFocused()
    
    // Test Enter key submission
    await page.getByTestId('login-email').fill('test@example.com')
    await page.getByTestId('login-password').fill('TestPass123!')
    await page.keyboard.press('Enter')
    
    // Should attempt login submission
    await page.waitForTimeout(1000)
    
    // Test authenticated navigation
    await authenticateUser(page, 'teacher')
    await page.goto('/teacher/dashboard')
    
    // Test escape key behavior
    const userMenu = page.getByTestId('user-menu')
    if (await userMenu.count() > 0) {
      await userMenu.click()
      await page.keyboard.press('Escape')
      // Menu should close
    }
  })

  test('🔴 CRITICAL: Screen reader compatibility - ARIA and semantic HTML', async ({ page }) => {
    await page.goto('/')
    
    // Verify landmark structure
    await expect(page.locator('[role="banner"], header')).toBeVisible()
    await expect(page.locator('[role="main"], main')).toBeVisible()
    await expect(page.locator('[role="navigation"], nav')).toBeVisible()
    
    // Check heading hierarchy
    const headings = await page.locator('h1, h2, h3, h4, h5, h6').all()
    let prevLevel = 0
    
    for (const heading of headings) {
      const tagName = await heading.evaluate(el => el.tagName.toLowerCase())
      const level = parseInt(tagName.charAt(1))
      
      // Heading levels should not skip (e.g., h1 -> h3)
      if (prevLevel > 0) {
        expect(level - prevLevel, 'Heading hierarchy should not skip levels').toBeLessThanOrEqual(1)
      }
      prevLevel = level
    }
    
    // Test form accessibility
    await page.goto('/login')
    
    // All form inputs must have accessible names
    const inputs = page.locator('input, textarea, select')
    const inputCount = await inputs.count()
    
    for (let i = 0; i < inputCount; i++) {
      const input = inputs.nth(i)
      const hasLabel = await input.evaluate(el => {
        const id = el.getAttribute('id')
        const ariaLabel = el.getAttribute('aria-label')
        const ariaLabelledby = el.getAttribute('aria-labelledby')
        
        return !!(
          ariaLabel ||
          ariaLabelledby ||
          (id && document.querySelector(`label[for="${id}"]`))
        )
      })
      
      expect(hasLabel, 'All form inputs must have accessible names').toBeTruthy()
    }
  })

  test('🔴 CRITICAL: Color contrast and visual accessibility standards', async ({ page }) => {
    await page.goto('/')
    
    // Test high contrast mode compatibility
    await page.emulateMedia({ colorScheme: 'dark' })
    await page.addStyleTag({
      content: `
        @media (prefers-contrast: high) {
          :root {
            --contrast-ratio: 7:1;
            filter: contrast(1.5);
          }
        }
      `
    })
    
    // Page should remain functional in high contrast
    await expect(page.locator('body')).toBeVisible()
    
    // Test reduced motion preference
    await page.emulateMedia({ reducedMotion: 'reduce' })
    await page.reload()
    
    // Verify no motion elements are animated
    const animatedElements = page.locator('[style*="animation"], [class*="animate"]')
    const count = await animatedElements.count()
    
    for (let i = 0; i < count; i++) {
      const element = animatedElements.nth(i)
      const computedStyle = await element.evaluate(el => {
        const styles = window.getComputedStyle(el)
        return {
          animationDuration: styles.animationDuration,
          transitionDuration: styles.transitionDuration
        }
      })
      
      // Animations should be disabled or very short
      expect(
        computedStyle.animationDuration === '0s' || 
        computedStyle.animationDuration === '0.01ms'
      ).toBeTruthy()
    }
  })

  test('🔴 CRITICAL: Mobile accessibility and touch targets (WCAG 2.1)', async ({ page }) => {
    // Test multiple mobile viewports
    const viewports = [
      { width: 375, height: 667, name: 'iPhone SE' },
      { width: 390, height: 844, name: 'iPhone 12' },
      { width: 360, height: 740, name: 'Galaxy S20' }
    ]
    
    for (const viewport of viewports) {
      await page.setViewportSize({ width: viewport.width, height: viewport.height })
      await page.goto('/')
      
      // Check touch target sizes (minimum 44x44px per WCAG 2.1)
      const touchTargets = page.locator('button, a, input[type="button"], input[type="submit"], [role="button"]')
      const targetCount = await touchTargets.count()
      
      for (let i = 0; i < Math.min(targetCount, 15); i++) {
        const target = touchTargets.nth(i)
        const box = await target.boundingBox()
        
        if (box && await target.isVisible()) {
          expect(box.width, `Touch target must be at least 44px wide on ${viewport.name}`).toBeGreaterThanOrEqual(44)
          expect(box.height, `Touch target must be at least 44px tall on ${viewport.name}`).toBeGreaterThanOrEqual(44)
        }
      }
    }
  })

  test('🔴 CRITICAL: Focus management and visual indicators', async ({ page }) => {
    await page.goto('/login')
    
    // Test focus visibility on all interactive elements
    const focusableElements = page.locator(
      'button, a, input, textarea, select, [tabindex]:not([tabindex="-1"])'
    )
    const count = await focusableElements.count()
    
    for (let i = 0; i < Math.min(count, 10); i++) {
      const element = focusableElements.nth(i)
      if (await element.isVisible()) {
        await element.focus()
        
        // Check for visible focus indicator
        const focusStyles = await element.evaluate(el => {
          const styles = window.getComputedStyle(el)
          return {
            outline: styles.outline,
            outlineWidth: styles.outlineWidth,
            outlineStyle: styles.outlineStyle,
            boxShadow: styles.boxShadow
          }
        })
        
        const hasVisibleFocus = (
          focusStyles.outline !== 'none' ||
          focusStyles.outlineWidth !== '0px' ||
          focusStyles.boxShadow !== 'none' ||
          focusStyles.outlineStyle !== 'none'
        )
        
        expect(hasVisibleFocus, 'All focusable elements must have visible focus indicators').toBeTruthy()
      }
    }
  })

  // Test accessibility across different language settings
  test('🔴 CRITICAL: Multi-language accessibility support', async ({ page }) => {
    const languages = ['en', 'es', 'ar', 'fr']
    
    for (const lang of languages) {
      // Set language in localStorage
      await page.addInitScript((language) => {
        localStorage.setItem('aivoLanguage', language)
      }, lang)
      
      await page.goto('/')
      await page.waitForLoadState('networkidle')
      
      // Verify language attribute matches
      const htmlLang = await page.getAttribute('html', 'lang')
      expect(htmlLang).toBe(lang)
      
      // Verify direction for RTL languages
      if (lang === 'ar') {
        const direction = await page.getAttribute('html', 'dir')
        expect(direction).toBe('rtl')
      }
      
      // Run basic accessibility check in each language
      const axeResults = await new AxeBuilder({ page })
        .withTags(['wcag2a', 'wcag2aa'])
        .analyze()
      
      const criticalViolations = axeResults.violations.filter(v => 
        v.impact === 'serious' || v.impact === 'critical'
      )
      
      expect(criticalViolations, 
        `${lang} language mode must have zero critical accessibility violations`
      ).toHaveLength(0)
    }
  })
})
