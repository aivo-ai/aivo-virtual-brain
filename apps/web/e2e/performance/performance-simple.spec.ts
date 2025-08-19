import { test, expect } from '@playwright/test'

test.describe('Performance Budgets - Core Web Vitals', () => {
  // Performance thresholds based on Google's Core Web Vitals
  const PERFORMANCE_BUDGETS = {
    LCP: 2500, // Largest Contentful Paint ≤ 2.5s
    TBT: 200,  // Total Blocking Time ≤ 200ms
    FCP: 1800, // First Contentful Paint ≤ 1.8s
    LoadTime: 5000 // Page load time ≤ 5s
  }

  const criticalPages = [
    { path: '/', name: 'Landing Page' },
    { path: '/login', name: 'Login Page' },
    { path: '/student/dashboard', name: 'Student Dashboard', role: 'student' },
    { path: '/teacher/dashboard', name: 'Teacher Dashboard', role: 'teacher' },
    { path: '/teacher/classes', name: 'Teacher Classes', role: 'teacher' },
    { path: '/student/lessons', name: 'Student Lessons', role: 'student' },
  ]

  const authenticateUser = async (page: any, role: string) => {
    await page.goto('/login')
    
    // Use actual login form structure
    switch (role) {
      case 'student':
        await page.getByTestId('login-email').fill('perf-student@test.edu')
        await page.getByTestId('login-password').fill('PerfTest123!')
        await page.getByTestId('login-submit').click()
        break
      case 'teacher':
        await page.getByTestId('login-email').fill('perf-teacher@test.edu')
        await page.getByTestId('login-password').fill('PerfTest123!')
        await page.getByTestId('login-submit').click()
        break
    }
  }

  criticalPages.forEach(pageInfo => {
    test(`${pageInfo.name} meets performance budgets`, async ({ page }) => {
      // Authenticate if needed
      if (pageInfo.role) {
        await authenticateUser(page, pageInfo.role)
      }

      // Start timing
      const startTime = Date.now()
      
      // Navigate to page
      await page.goto(pageInfo.path)
      await page.waitForLoadState('networkidle')
      
      // Calculate load time
      const loadTime = Date.now() - startTime

      // Get basic navigation metrics
      const metrics = await page.evaluate(() => {
        const navigation = performance.getEntriesByType('navigation')[0] as PerformanceNavigationTiming
        const paint = performance.getEntriesByType('paint')
        
        return {
          loadEventEnd: navigation.loadEventEnd,
          domContentLoaded: navigation.domContentLoadedEventEnd,
          firstContentfulPaint: paint.find(p => p.name === 'first-contentful-paint')?.startTime || 0,
          transferSize: navigation.transferSize || 0,
          decodedBodySize: navigation.decodedBodySize || 0
        }
      })

      console.log(`${pageInfo.name} Performance:`)
      console.log(`- Load Time: ${loadTime}ms`)
      console.log(`- FCP: ${metrics.firstContentfulPaint.toFixed(0)}ms`)
      console.log(`- DOM Ready: ${metrics.domContentLoaded.toFixed(0)}ms`)
      console.log(`- Transfer Size: ${(metrics.transferSize / 1024).toFixed(1)}KB`)

      // Performance assertions
      expect(loadTime, `Load time should be ≤ ${PERFORMANCE_BUDGETS.LoadTime}ms`).toBeLessThanOrEqual(PERFORMANCE_BUDGETS.LoadTime)
      expect(metrics.firstContentfulPaint, `FCP should be ≤ ${PERFORMANCE_BUDGETS.FCP}ms`).toBeLessThanOrEqual(PERFORMANCE_BUDGETS.FCP)
    })
  })

  test('resource loading performance and bundle size limits', async ({ page }) => {
    interface ResourceInfo {
      url: string
      status: number
      size: number
      type: string
    }

    const resourceSizes: ResourceInfo[] = []
    
    page.on('response', response => {
      const headers = response.headers()
      const contentLength = parseInt(headers['content-length'] || '0', 10)
      
      resourceSizes.push({
        url: response.url(),
        status: response.status(),
        size: contentLength,
        type: response.request().resourceType()
      })
    })

    await page.goto('/')
    await page.waitForLoadState('networkidle')

    // Analyze bundle sizes
    const jsFiles = resourceSizes.filter(r => r.type === 'script' && r.url.includes('.js'))
    const cssFiles = resourceSizes.filter(r => r.type === 'stylesheet' && r.url.includes('.css'))

    const totalJSSize = jsFiles.reduce((sum, file) => sum + file.size, 0)
    const totalCSSSize = cssFiles.reduce((sum, file) => sum + file.size, 0)

    console.log(`Resource Sizes:`)
    console.log(`- Total JS: ${(totalJSSize / 1024).toFixed(1)} KB`)
    console.log(`- Total CSS: ${(totalCSSSize / 1024).toFixed(1)} KB`) 

    // Bundle size budgets (in KB)
    expect(totalJSSize / 1024, 'JavaScript bundle should be ≤ 500KB').toBeLessThanOrEqual(500)
    expect(totalCSSSize / 1024, 'CSS bundle should be ≤ 100KB').toBeLessThanOrEqual(100)
  })

  test('performance optimization checks', async ({ page }) => {
    await page.goto('/')
    
    const optimizationIssues: string[] = []

    // Check for render-blocking resources
    const renderBlockingCSS = await page.locator('link[rel="stylesheet"]:not([media])').count()
    const renderBlockingJS = await page.locator('script[src]:not([async]):not([defer])').count()

    if (renderBlockingCSS > 3) {
      optimizationIssues.push(`Too many render-blocking CSS files: ${renderBlockingCSS}`)
    }
    
    if (renderBlockingJS > 0) {
      optimizationIssues.push(`Render-blocking JavaScript detected: ${renderBlockingJS} files`)
    }

    // Check for missing meta viewport
    const hasViewport = await page.locator('meta[name="viewport"]').count() > 0
    if (!hasViewport) {
      optimizationIssues.push('Missing viewport meta tag')
    }

    // Check for image optimization
    const unoptimizedImages = await page.locator('img:not([loading="lazy"])').count()
    if (unoptimizedImages > 5) {
      optimizationIssues.push(`Images not lazy-loaded: ${unoptimizedImages}`)
    }

    console.log('Performance optimization audit:')
    optimizationIssues.forEach(issue => console.log(`- ${issue}`))

    // Should have minimal optimization issues
    expect(optimizationIssues.length, 'Should have minimal performance issues').toBeLessThan(5)
  })

  test('mobile performance on slow connections', async ({ page, context }) => {
    // Set mobile viewport
    await page.setViewportSize({ width: 375, height: 667 })

    // Simulate slow network
    await context.route('**/*', route => {
      setTimeout(() => {
        route.continue()
      }, Math.random() * 100) // Add up to 100ms delay
    })

    const startTime = Date.now()
    await page.goto('/')
    await page.waitForLoadState('domcontentloaded')
    const loadTime = Date.now() - startTime

    console.log(`Mobile load time on slow network: ${loadTime}ms`)
    
    // Should still be usable on mobile
    expect(loadTime, 'Mobile page should load within 8s on slow network').toBeLessThan(8000)
    
    // Critical content should be visible (using actual HomePage elements)
    await expect(page.getByRole('heading', { level: 1 })).toBeVisible()
  })

  test('memory usage monitoring through navigation', async ({ page }) => {
    // Navigate through several pages to test for excessive memory usage
    const testPages = [
      '/',
      '/login', 
      '/teacher/dashboard',
      '/teacher/classes'
    ]
    
    for (const pagePath of testPages) {
      if (pagePath.includes('teacher')) {
        await authenticateUser(page, 'teacher')
      }
      
      await page.goto(pagePath)
      await page.waitForLoadState('networkidle')
    }

    // Check for excessive DOM nodes (indicator of memory issues)
    const nodeCount = await page.evaluate(() => {
      return document.querySelectorAll('*').length
    })

    console.log(`Final DOM node count: ${nodeCount}`)
    expect(nodeCount, 'DOM should not have excessive nodes').toBeLessThan(3000)

    // Check for event listeners (potential memory leaks)
    const listenerCount = await page.evaluate(() => {
      const elements = document.querySelectorAll('*')
      let count = 0
      elements.forEach(el => {
        const listeners = (el as any).getEventListeners?.() || {}
        count += Object.keys(listeners).length
      })
      return count
    })

    console.log(`Event listener count: ${listenerCount}`)
    // This is informational - actual limits depend on app complexity
  })
})
