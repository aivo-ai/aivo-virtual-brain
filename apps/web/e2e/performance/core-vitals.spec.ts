import { test, expect } from '@playwright/test'

// Type definitions for performance monitoring
interface CustomPerformanceEntry {
  type: string;
  startTime: number;
  value?: number;
  processingStart?: number;
}

interface ResourceInfo {
  url: string;
  status: number;
  size: number;
  type: string;
}

interface LayoutShiftEntry extends PerformanceEntry {
  value: number;
  hadRecentInput: boolean;
}

interface FirstInputEntry extends PerformanceEntry {
  processingStart: number;
}

declare global {
  interface Window {
    performanceEntries: CustomPerformanceEntry[];
  }
}

test.describe('Performance Budgets - Core Web Vitals', () => {
  // Performance thresholds based on Google's Core Web Vitals
  const PERFORMANCE_BUDGETS = {
    LCP: 2500, // Largest Contentful Paint ≤ 2.5s
    FID: 100,  // First Input Delay ≤ 100ms  
    TBT: 200,  // Total Blocking Time ≤ 200ms
    CLS: 0.1,  // Cumulative Layout Shift ≤ 0.1
    FCP: 1800, // First Contentful Paint ≤ 1.8s
    TTI: 3800  // Time to Interactive ≤ 3.8s
  }

  const criticalPages = [
    { path: '/', name: 'Landing Page' },
    { path: '/login', name: 'Login Page' },
    { path: '/student/dashboard', name: 'Student Dashboard', role: 'student' },
    { path: '/teacher/dashboard', name: 'Teacher Dashboard', role: 'teacher' },
    { path: '/parent/dashboard', name: 'Parent Dashboard', role: 'parent' },
    { path: '/teacher/classes', name: 'Teacher Classes', role: 'teacher' },
    { path: '/student/lessons', name: 'Student Lessons', role: 'student' },
  ]

  const authenticateUser = async (page: any, role: string) => {
    await page.goto('/login')
    
    switch (role) {
      case 'student':
        await page.getByTestId('student-login-tab').click()
        await page.getByTestId('student-id').fill('perf-test-student')
        await page.getByTestId('student-access-code').fill('PERF2024')
        await page.getByTestId('student-login-submit').click()
        break
      case 'teacher':
        await page.getByTestId('teacher-login-tab').click()
        await page.getByTestId('email').fill('perf@test.edu')
        await page.getByTestId('password').fill('PerfTest123!')
        await page.getByTestId('login-submit').click()
        break
      case 'parent':
        await page.getByTestId('parent-login-tab').click()
        await page.getByTestId('parent-email').fill('perf@parent.com')
        await page.getByTestId('parent-password').fill('PerfParent123!')
        await page.getByTestId('parent-login-submit').click()
        break
    }
  }

  criticalPages.forEach(pageInfo => {
    test(`${pageInfo.name} meets Core Web Vitals performance budgets`, async ({ page }) => {
      // Collect performance entries
      await page.addInitScript(() => {
        window.performanceEntries = []
        
        // Monitor layout shifts
        new PerformanceObserver((list) => {
          for (const entry of list.getEntries()) {
            const layoutShiftEntry = entry as LayoutShiftEntry
            if (entry.entryType === 'layout-shift' && !layoutShiftEntry.hadRecentInput) {
              window.performanceEntries.push({
                type: 'layout-shift',
                startTime: entry.startTime,
                value: layoutShiftEntry.value
              })
            }
          }
        }).observe({ entryTypes: ['layout-shift'] })

        // Monitor largest contentful paint
        new PerformanceObserver((list) => {
          const entries = list.getEntries()
          const lastEntry = entries[entries.length - 1]
          window.performanceEntries.push({
            type: 'largest-contentful-paint',
            startTime: lastEntry.startTime
          })
        }).observe({ entryTypes: ['largest-contentful-paint'] })

        // Monitor first input delay
        new PerformanceObserver((list) => {
          for (const entry of list.getEntries()) {
            const firstInputEntry = entry as FirstInputEntry
            window.performanceEntries.push({
              type: 'first-input',
              processingStart: firstInputEntry.processingStart,
              startTime: entry.startTime
            })
          }
        }).observe({ entryTypes: ['first-input'] })
      })

      // Authenticate if needed
      if (pageInfo.role) {
        await authenticateUser(page, pageInfo.role)
      }

      // Start timing
      const startTime = Date.now()
      
      // Navigate to page with performance monitoring
      await page.goto(pageInfo.path, { waitUntil: 'networkidle' })
      
      // Wait for page to be fully interactive
      await page.waitForLoadState('domcontentloaded')
      await page.waitForLoadState('load')

      // Collect navigation timing metrics
      const navigationMetrics = await page.evaluate(() => {
        const navigation = performance.getEntriesByType('navigation')[0] as PerformanceNavigationTiming
        const paint = performance.getEntriesByType('paint')
        
        return {
          // Use startTime instead of navigationStart for PerformanceNavigationTiming
          navigationStart: navigation.startTime,
          loadEventEnd: navigation.loadEventEnd,
          domContentLoaded: navigation.domContentLoadedEventEnd,
          firstPaint: paint.find(p => p.name === 'first-paint')?.startTime || 0,
          firstContentfulPaint: paint.find(p => p.name === 'first-contentful-paint')?.startTime || 0,
          transferSize: navigation.transferSize,
          decodedBodySize: navigation.decodedBodySize
        }
      })

      // Calculate metrics
      const loadTime = Date.now() - startTime
      const firstContentfulPaint = navigationMetrics.firstContentfulPaint
      
      // Get LCP from performance entries
      const performanceEntries = await page.evaluate(() => window.performanceEntries)
      const lcpEntries = performanceEntries.filter((e: CustomPerformanceEntry) => e.type === 'largest-contentful-paint')
      const largestContentfulPaint = lcpEntries.length > 0 ? lcpEntries[lcpEntries.length - 1].startTime : 0

      // Calculate CLS
      const layoutShiftEntries = performanceEntries.filter((e: CustomPerformanceEntry) => e.type === 'layout-shift')
      const cumulativeLayoutShift = layoutShiftEntries.reduce((sum: number, entry: CustomPerformanceEntry) => sum + (entry.value || 0), 0)

      // Get FID
      const fidEntries = performanceEntries.filter((e: CustomPerformanceEntry) => e.type === 'first-input')
      const firstInputDelay = fidEntries.length > 0 && fidEntries[0].processingStart ? 
        fidEntries[0].processingStart - fidEntries[0].startTime : 0

      // Calculate TBT (simplified - actual calculation is more complex)
      const totalBlockingTime = await page.evaluate(() => {
        // Simplified TBT calculation
        const longTasks = performance.getEntriesByType('longtask')
        return longTasks.reduce((total, task) => {
          const blockingTime = Math.max(0, task.duration - 50)
          return total + blockingTime
        }, 0)
      })

      // Performance assertions
      console.log(`${pageInfo.name} Performance Metrics:`)
      console.log(`- FCP: ${firstContentfulPaint.toFixed(0)}ms`)
      console.log(`- LCP: ${largestContentfulPaint.toFixed(0)}ms`) 
      console.log(`- FID: ${firstInputDelay.toFixed(0)}ms`)
      console.log(`- TBT: ${totalBlockingTime.toFixed(0)}ms`)
      console.log(`- CLS: ${cumulativeLayoutShift.toFixed(3)}`)
      console.log(`- Load Time: ${loadTime}ms`)

      // Assert performance budgets
      expect(firstContentfulPaint, `FCP should be ≤ ${PERFORMANCE_BUDGETS.FCP}ms`).toBeLessThanOrEqual(PERFORMANCE_BUDGETS.FCP)
      expect(largestContentfulPaint, `LCP should be ≤ ${PERFORMANCE_BUDGETS.LCP}ms`).toBeLessThanOrEqual(PERFORMANCE_BUDGETS.LCP)
      expect(firstInputDelay, `FID should be ≤ ${PERFORMANCE_BUDGETS.FID}ms`).toBeLessThanOrEqual(PERFORMANCE_BUDGETS.FID)
      expect(totalBlockingTime, `TBT should be ≤ ${PERFORMANCE_BUDGETS.TBT}ms`).toBeLessThanOrEqual(PERFORMANCE_BUDGETS.TBT)
      expect(cumulativeLayoutShift, `CLS should be ≤ ${PERFORMANCE_BUDGETS.CLS}`).toBeLessThanOrEqual(PERFORMANCE_BUDGETS.CLS)
    })
  })

  test('resource loading performance and bundle size limits', async ({ page }) => {
    await page.goto('/')
    
    // Monitor network requests
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

    await page.waitForLoadState('networkidle')

    // Analyze bundle sizes
    const jsFiles = resourceSizes.filter((r: ResourceInfo) => r.type === 'script' && r.url.includes('.js'))
    const cssFiles = resourceSizes.filter((r: ResourceInfo) => r.type === 'stylesheet' && r.url.includes('.css'))
    const imageFiles = resourceSizes.filter((r: ResourceInfo) => r.type === 'image')

    const totalJSSize = jsFiles.reduce((sum, file) => sum + file.size, 0)
    const totalCSSSize = cssFiles.reduce((sum, file) => sum + file.size, 0)
    const totalImageSize = imageFiles.reduce((sum, file) => sum + file.size, 0)

    console.log(`Resource Sizes:`)
    console.log(`- Total JS: ${(totalJSSize / 1024).toFixed(1)} KB`)
    console.log(`- Total CSS: ${(totalCSSSize / 1024).toFixed(1)} KB`) 
    console.log(`- Total Images: ${(totalImageSize / 1024).toFixed(1)} KB`)

    // Bundle size budgets (in KB)
    expect(totalJSSize / 1024, 'JavaScript bundle should be ≤ 500KB').toBeLessThanOrEqual(500)
    expect(totalCSSSize / 1024, 'CSS bundle should be ≤ 100KB').toBeLessThanOrEqual(100)
    
    // Individual file size limits
    const largeJSFiles = jsFiles.filter(f => f.size > 200 * 1024) // > 200KB
    expect(largeJSFiles.length, 'No individual JS file should exceed 200KB').toBe(0)
  })

  test('performance under simulated slow network conditions', async ({ page, context }) => {
    // Simulate slow 3G network
    await context.route('**/*', route => {
      // Add delay to simulate slow network
      setTimeout(() => {
        route.continue()
      }, Math.random() * 200) // 0-200ms delay
    })

    const startTime = Date.now()
    await page.goto('/')
    await page.waitForLoadState('networkidle')
    const loadTime = Date.now() - startTime

    console.log(`Load time on slow network: ${loadTime}ms`)
    
    // Should still be usable under slow conditions
    expect(loadTime, 'Page should load within 10s on slow network').toBeLessThan(10000)
    
    // Critical content should be visible
    await expect(page.getByTestId('hero-title')).toBeVisible()
    await expect(page.getByTestId('cta-primary')).toBeVisible()
  })

  test('memory usage and leak detection', async ({ page }) => {
    // Navigate through several pages to test for memory leaks
    const pages = ['/', '/login', '/teacher/dashboard', '/teacher/classes']
    
    for (const pagePath of pages) {
      if (pagePath.includes('teacher')) {
        await page.goto('/login')
        await page.getByTestId('teacher-login-tab').click()
        await page.getByTestId('email').fill('memory@test.edu')
        await page.getByTestId('password').fill('MemoryTest123!')
        await page.getByTestId('login-submit').click()
      }
      
      await page.goto(pagePath)
      await page.waitForLoadState('networkidle')
      
      // Force garbage collection if available
      try {
        await page.evaluate(() => {
          if (window.gc) {
            window.gc()
          }
        })
      } catch {
        // GC not available in this context
      }
    }

    // Check for excessive DOM nodes (potential memory leaks)
    const nodeCount = await page.evaluate(() => {
      return document.querySelectorAll('*').length
    })

    console.log(`DOM node count: ${nodeCount}`)
    expect(nodeCount, 'DOM should not have excessive nodes').toBeLessThan(2000)
  })

  test('lighthouse performance audit simulation', async ({ page }) => {
    await page.goto('/')
    
    // Simulate Lighthouse performance audit checks
    const performanceIssues = []

    // Check for render-blocking resources
    const renderBlockingCSS = await page.locator('link[rel="stylesheet"]:not([media])').count()
    const renderBlockingJS = await page.locator('script[src]:not([async]):not([defer])').count()

    if (renderBlockingCSS > 3) {
      performanceIssues.push(`Too many render-blocking CSS files: ${renderBlockingCSS}`)
    }
    
    if (renderBlockingJS > 0) {
      performanceIssues.push(`Render-blocking JavaScript detected: ${renderBlockingJS} files`)
    }

    // Check for missing meta viewport
    const hasViewport = await page.locator('meta[name="viewport"]').count() > 0
    if (!hasViewport) {
      performanceIssues.push('Missing viewport meta tag')
    }

    // Check for image optimization
    const unoptimizedImages = await page.locator('img:not([loading="lazy"]):not([decoding="async"])').count()
    if (unoptimizedImages > 2) {
      performanceIssues.push(`Images not optimized for loading: ${unoptimizedImages}`)
    }

    // Check for missing alt text
    const imagesWithoutAlt = await page.locator('img:not([alt])').count()
    if (imagesWithoutAlt > 0) {
      performanceIssues.push(`Images missing alt text: ${imagesWithoutAlt}`)
    }

    console.log('Performance audit results:')
    performanceIssues.forEach(issue => console.log(`- ${issue}`))

    // Should have minimal performance issues
    expect(performanceIssues.length, 'Should have minimal performance issues').toBeLessThan(3)
  })
})
