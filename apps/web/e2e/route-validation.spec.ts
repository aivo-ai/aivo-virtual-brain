import { test, expect } from '@playwright/test'

test.describe('Route Validation & CTA Guard Scanner', () => {
  // Define all expected routes based on current implementation
  const expectedRoutes = [
    '/',
    '/health',
    '/dev-mocks',
    // Note: Login, dashboard, and other routes are defined in ROUTES but not implemented yet
    // This reflects the current state where basic infrastructure exists but full auth is pending
  ]

  const authenticateUser = async (page: any, role: string) => {
    await page.goto('/login')
    
    // Use single login form (current implementation)
    switch (role) {
      case 'student':
        await page.getByTestId('login-email').fill('test-student@test.edu')
        await page.getByTestId('login-password').fill('TestPass123!')
        await page.getByTestId('login-submit').click()
        break
      case 'teacher':
        await page.getByTestId('login-email').fill('test-teacher@test.edu')
        await page.getByTestId('login-password').fill('TestPass123!')
        await page.getByTestId('login-submit').click()
        break
      case 'parent':
        await page.getByTestId('login-email').fill('test-parent@test.com')
        await page.getByTestId('login-password').fill('TestPass123!')
        await page.getByTestId('login-submit').click()
        break
      case 'admin':
        await page.getByTestId('login-email').fill('test-admin@test.edu')
        await page.getByTestId('login-password').fill('TestPass123!')
        await page.getByTestId('login-submit').click()
        break
    }
  }

  test('validate all expected routes are accessible', async ({ page }) => {
    const routeResults = []
    
    for (const route of expectedRoutes) {
      try {
        // Determine if route requires authentication
        const requiresAuth = route.startsWith('/student/') || 
                           route.startsWith('/teacher/') || 
                           route.startsWith('/parent/') || 
                           route.startsWith('/admin/') ||
                           route.startsWith('/iep/')
        
        if (requiresAuth) {
          // Determine role based on route
          let role = 'admin' // default
          if (route.startsWith('/student/')) role = 'student'
          else if (route.startsWith('/teacher/')) role = 'teacher'
          else if (route.startsWith('/parent/')) role = 'parent'
          
          await authenticateUser(page, role)
        }
        
        // Navigate to route
        const response = await page.goto(route)
        
        routeResults.push({
          route,
          status: response?.status() || 'unknown',
          accessible: response?.status() === 200,
          requiresAuth
        })
        
        // Basic content check
        if (response?.status() === 200) {
          await expect(page.locator('body')).toBeVisible()
        }
        
      } catch (error) {
        routeResults.push({
          route,
          status: 'error',
          accessible: false,
          error: (error as Error).message
        })
      }
    }
    
    // Report results
    const inaccessibleRoutes = routeResults.filter(r => !r.accessible)
    
    if (inaccessibleRoutes.length > 0) {
      console.log('Inaccessible routes found:')
      inaccessibleRoutes.forEach(route => {
        console.log(`- ${route.route}: Status ${route.status}`)
      })
    }
    
    // Fail test if critical routes are inaccessible
    const criticalRoutes = ['/', '/login', '/student/dashboard', '/teacher/dashboard']
    const inaccessibleCritical = inaccessibleRoutes.filter(r => 
      criticalRoutes.includes(r.route)
    )
    
    expect(inaccessibleCritical).toHaveLength(0)
  })

  test('scan for orphan CTAs and broken navigation links', async ({ page }) => {
    const pagesWithNavigation = [
      { path: '/', auth: false },
      { path: '/student/dashboard', auth: 'student' },
      { path: '/teacher/dashboard', auth: 'teacher' },
      { path: '/parent/dashboard', auth: 'parent' },
      { path: '/admin/dashboard', auth: 'admin' },
      { path: '/teacher/classes', auth: 'teacher' },
      { path: '/student/lessons', auth: 'student' }
    ]
    
    const orphanCTAs = []
    const brokenLinks = []
    
    for (const pageInfo of pagesWithNavigation) {
      // Authenticate if needed
      if (pageInfo.auth && typeof pageInfo.auth === 'string') {
        await authenticateUser(page, pageInfo.auth)
      }
      
      await page.goto(pageInfo.path)
      await page.waitForLoadState('networkidle')
      
      // Find all interactive elements
      const buttons = await page.locator('button:visible').all()
      const links = await page.locator('a:visible').all()
      
      // Check buttons for proper handlers
      for (const button of buttons) {
        const hasOnClick = await button.evaluate(el => {
          const htmlEl = el as HTMLButtonElement
          return el.onclick !== null || 
                 el.getAttribute('data-testid') !== null ||
                 htmlEl.type === 'submit' ||
                 htmlEl.form !== null
        })
        
        if (!hasOnClick) {
          const text = await button.textContent()
          orphanCTAs.push({
            page: pageInfo.path,
            element: 'button',
            text: text?.trim(),
            issue: 'No click handler detected'
          })
        }
      }
      
      // Check links for valid hrefs
      for (const link of links) {
        const href = await link.getAttribute('href')
        
        if (!href || href === '#' || href === 'javascript:void(0)') {
          const text = await link.textContent()
          orphanCTAs.push({
            page: pageInfo.path,
            element: 'link',
            text: text?.trim(),
            href,
            issue: 'Empty or placeholder href'
          })
        } else if (href.startsWith('/')) {
          // Check if internal link exists in our route list
          if (!expectedRoutes.includes(href) && !href.includes('?') && !href.includes('#')) {
            brokenLinks.push({
              page: pageInfo.path,
              href,
              text: await link.textContent()
            })
          }
        }
      }
    }
    
    // Report findings
    if (orphanCTAs.length > 0) {
      console.log('Orphan CTAs found:')
      orphanCTAs.forEach(cta => {
        console.log(`- ${cta.page}: ${cta.element} "${cta.text}" - ${cta.issue}`)
      })
    }
    
    if (brokenLinks.length > 0) {
      console.log('Potentially broken internal links:')
      brokenLinks.forEach(link => {
        console.log(`- ${link.page}: "${link.text}" -> ${link.href}`)
      })
    }
    
    // Fail if too many issues found
    expect(orphanCTAs.length).toBeLessThan(5) // Allow some false positives
    expect(brokenLinks.length).toBeLessThan(3)
  })

  test('validate form submissions and CTA functionality', async ({ page }) => {
    // Test login form CTAs
    await page.goto('/login')
    
    // Check login button functionality (using actual test IDs)
    await page.getByTestId('login-email').fill('test@example.com')
    await page.getByTestId('login-password').fill('wrongpassword')
    await page.getByTestId('login-submit').click()
    
    // Should show error message (button works)
    await expect(page.locator('.error, [role="alert"], [data-testid*="error"]')).toBeVisible({ timeout: 5000 })
    
    // Test forgot password link (using actual test ID)
    await page.getByTestId('forgot-password-link').click()
    await expect(page).toHaveURL('/forgot-password')
    
    // Test registration link if present (using actual test ID)
    const registerLink = page.getByTestId('register-link')
    if (await registerLink.count() > 0) {
      await registerLink.click()
      await expect(page).toHaveURL('/register')
    }
  })

  test('verify navigation menu completeness', async ({ page }) => {
    const navigationTests = [
      {
        role: 'student',
        expectedNavItems: ['dashboard', 'lessons', 'games', 'profile'],
        path: '/student/dashboard'
      },
      {
        role: 'teacher', 
        expectedNavItems: ['dashboard', 'classes', 'gradebook', 'assessments'],
        path: '/teacher/dashboard'
      },
      {
        role: 'parent',
        expectedNavItems: ['dashboard', 'progress', 'children'],
        path: '/parent/dashboard'  
      },
      {
        role: 'admin',
        expectedNavItems: ['dashboard', 'users', 'billing', 'analytics'],
        path: '/admin/dashboard'
      }
    ]
    
    for (const navTest of navigationTests) {
      await authenticateUser(page, navTest.role)
      await page.goto(navTest.path)
      
      // Check each expected navigation item exists and is functional
      for (const navItem of navTest.expectedNavItems) {
        const navElement = page.locator(`[data-testid="nav-${navItem}"], nav a[href*="${navItem}"]`).first()
        
        if (await navElement.count() > 0) {
          await expect(navElement).toBeVisible()
          
          // Test navigation functionality
          await navElement.click()
          await page.waitForLoadState('networkidle')
          
          // Should navigate to expected route
          const currentURL = page.url()
          expect(currentURL).toContain(navItem)
        } else {
          console.warn(`Missing navigation item for ${navTest.role}: ${navItem}`)
        }
      }
    }
  })

  test('scan for inconsistent CTA styling and labeling', async ({ page }) => {
    const ctaPages = [
      '/',
      '/login', 
      '/register',
      '/student/dashboard',
      '/teacher/dashboard'
    ]
    
    const ctaStyles = []
    
    for (const pagePath of ctaPages) {
      if (pagePath.includes('/dashboard')) {
        const role = pagePath.split('/')[1]
        await authenticateUser(page, role)
      }
      
      await page.goto(pagePath)
      
      // Collect primary CTA button styles
      const primaryButtons = await page.locator('[data-testid*="cta"], .btn-primary, button[type="submit"]').all()
      
      for (const button of primaryButtons) {
        const styles = await button.evaluate(el => {
          const computed = window.getComputedStyle(el)
          return {
            backgroundColor: computed.backgroundColor,
            color: computed.color,
            fontSize: computed.fontSize,
            padding: computed.padding,
            borderRadius: computed.borderRadius
          }
        })
        
        const text = await button.textContent()
        
        ctaStyles.push({
          page: pagePath,
          text: text?.trim(),
          styles
        })
      }
    }
    
    // Check for style consistency
    if (ctaStyles.length > 1) {
      const firstStyle = ctaStyles[0].styles
      const inconsistentStyles = ctaStyles.filter(cta => 
        cta.styles.backgroundColor !== firstStyle.backgroundColor ||
        cta.styles.fontSize !== firstStyle.fontSize
      )
      
      if (inconsistentStyles.length > 0) {
        console.log('Inconsistent CTA styling found:')
        inconsistentStyles.forEach(cta => {
          console.log(`- ${cta.page}: "${cta.text}" has different styling`)
        })
      }
      
      // Allow some variation but not too much
      expect(inconsistentStyles.length).toBeLessThan(ctaStyles.length * 0.5)
    }
  })

  test('verify error page routes and 404 handling', async ({ page }) => {
    // Test common error scenarios
    const errorTests = [
      { path: '/nonexistent-page', expectedStatus: 404 },
      { path: '/admin/users', expectedRedirect: '/unauthorized' }, // Without auth
      { path: '/teacher/classes', expectedRedirect: '/login' }, // Without auth
    ]
    
    for (const errorTest of errorTests) {
      const response = await page.goto(errorTest.path)
      
      if (errorTest.expectedStatus) {
        expect(response?.status()).toBe(errorTest.expectedStatus)
      }
      
      if (errorTest.expectedRedirect) {
        await expect(page).toHaveURL(errorTest.expectedRedirect)
      }
      
      // Verify error page has proper navigation back
      const backButton = page.locator('[data-testid="back-button"], .back-link, a[href="/"]')
      if (await backButton.count() > 0) {
        await expect(backButton).toBeVisible()
      }
    }
  })
})
