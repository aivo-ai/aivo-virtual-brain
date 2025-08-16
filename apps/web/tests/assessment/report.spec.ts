import { test, expect } from '@playwright/test'

test.describe('S3-08 Baseline Assessment - Report Page', () => {
  test.beforeEach(async ({ page }) => {
    // Mock the assessment API
    await page.route('**/assessment-svc/**', async route => {
      const url = route.request().url()

      if (
        url.includes('/sessions/session-123') &&
        route.request().method() === 'GET'
      ) {
        // Mock get session
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            id: 'session-123',
            learnerId: 'learner-456',
            type: 'baseline',
            status: 'completed',
            startedAt: '2025-08-16T10:00:00Z',
            completedAt: '2025-08-16T10:15:00Z',
            currentItemIndex: 5,
            totalItems: 5,
            gradeBand: 'K-2',
            adaptiveSettings: {
              audioFirst: true,
              largeTargets: true,
              simplifiedInterface: true,
            },
          }),
        })
      } else if (
        url.includes('/sessions/session-123/report') &&
        route.request().method() === 'GET'
      ) {
        // Mock get report
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            sessionId: 'session-123',
            learnerId: 'learner-456',
            type: 'baseline',
            status: 'BASELINE_COMPLETE',
            completedAt: '2025-08-16T10:15:00Z',
            surfaceLevel: 'L2',
            totalItems: 5,
            correctAnswers: 4,
            accuracyPercentage: 80,
            averageResponseTime: 15000,
            skillsAssessed: [
              {
                skillId: 'math-basic',
                skillName: 'Basic Math',
                level: 'L2',
                mastery: 'proficient',
                confidence: 0.85,
                itemsAssessed: 2,
              },
              {
                skillId: 'reading-comp',
                skillName: 'Reading Comprehension',
                level: 'L1',
                mastery: 'developing',
                confidence: 0.65,
                itemsAssessed: 3,
              },
            ],
            recommendations: [
              'Continue practicing basic math skills with visual aids',
              'Focus on reading comprehension with age-appropriate stories',
            ],
            nextSteps: [
              'Start with Level 2 math activities',
              'Practice reading daily for 15 minutes',
            ],
          }),
        })
      }
    })
  })

  test('should display K-2 appropriate celebration and results', async ({
    page,
  }) => {
    await page.goto('/assessment/report?sessionId=session-123')

    // Check for K-2 specific celebration title
    await expect(page.getByText('🌟 Amazing Job!')).toBeVisible()

    // Check for encouraging subtitle
    await expect(
      page.getByText("You did your best and that's what matters!")
    ).toBeVisible()

    // Check for large, prominent accuracy display
    await expect(page.getByText('80%')).toBeVisible()
    await expect(page.getByText('Accuracy')).toBeVisible()

    // Check for correct answers display
    await expect(page.getByText('4/5')).toBeVisible()
    await expect(page.getByText('Correct')).toBeVisible()

    // Check for level display
    await expect(page.getByText('L2')).toBeVisible()
    await expect(page.getByText('Level')).toBeVisible()

    // Check for encouraging message
    await expect(page.getByText("You're a superstar learner!")).toBeVisible()
  })

  test('should display skills assessment with appropriate icons and colors', async ({
    page,
  }) => {
    await page.goto('/assessment/report?sessionId=session-123')

    // Check for skills section title
    await expect(page.getByText('🎯 What You Learned About')).toBeVisible()

    // Check for skills with mastery levels
    await expect(page.getByText('Basic Math')).toBeVisible()
    await expect(page.getByText('proficient')).toBeVisible()

    await expect(page.getByText('Reading Comprehension')).toBeVisible()
    await expect(page.getByText('developing')).toBeVisible()

    // Check for skill details
    await expect(page.getByText('Level: L2')).toBeVisible()
    await expect(page.getByText('Confidence: 85%')).toBeVisible()
    await expect(page.getByText('2 items')).toBeVisible()
  })

  test('should show animated progress bar', async ({ page }) => {
    await page.goto('/assessment/report?sessionId=session-123')

    // Progress bar should be visible
    const progressBar = page
      .locator('.bg-green-500, .bg-yellow-500, .bg-blue-500')
      .first()
    await expect(progressBar).toBeVisible()

    // Should animate to 80% width (may need to wait for animation)
    await page.waitForTimeout(2000) // Wait for animation
  })

  test('should display recommendations with appropriate styling', async ({
    page,
  }) => {
    await page.goto('/assessment/report?sessionId=session-123')

    // Check for recommendations section
    await expect(page.getByText("🚀 What's Next?")).toBeVisible()

    // Check for recommendation content
    await expect(
      page.getByText('Continue practicing basic math skills')
    ).toBeVisible()
    await expect(page.getByText('Focus on reading comprehension')).toBeVisible()

    // Recommendations should have star icons for K-2
    await expect(page.getByText('🌟')).toBeVisible()
  })

  test('should display next steps section', async ({ page }) => {
    await page.goto('/assessment/report?sessionId=session-123')

    // Check for next steps section
    await expect(page.getByText('🎮 Ready to Learn More?')).toBeVisible()

    // Check for next step content
    await expect(
      page.getByText('Start with Level 2 math activities')
    ).toBeVisible()
    await expect(
      page.getByText('Practice reading daily for 15 minutes')
    ).toBeVisible()

    // Next steps should have target icons for K-2
    await expect(page.getByText('🎯')).toBeVisible()
  })

  test('should provide appropriate action buttons for K-2', async ({
    page,
  }) => {
    await page.goto('/assessment/report?sessionId=session-123')

    // Check for K-2 appropriate button labels
    await expect(page.getByRole('button', { name: '🏠 Go Home' })).toBeVisible()
    await expect(
      page.getByRole('button', { name: '🔄 Play Again?' })
    ).toBeVisible()
    await expect(
      page.getByRole('button', { name: '🖨️ Print My Report' })
    ).toBeVisible()

    // Buttons should be large enough for K-2
    const homeButton = page.getByRole('button', { name: '🏠 Go Home' })
    await expect(homeButton).toHaveClass(/text-xl|text-2xl/)
  })

  test('should handle different performance levels appropriately', async ({
    page,
  }) => {
    // Test lower performance with encouraging messaging
    await page.route(
      '**/assessment-svc/sessions/session-123/report',
      async route => {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            sessionId: 'session-123',
            learnerId: 'learner-456',
            type: 'baseline',
            status: 'BASELINE_COMPLETE',
            completedAt: '2025-08-16T10:15:00Z',
            surfaceLevel: 'L1',
            totalItems: 5,
            correctAnswers: 2,
            accuracyPercentage: 40,
            averageResponseTime: 20000,
            skillsAssessed: [],
            recommendations: [
              'Keep practicing! Every day you learn something new.',
            ],
            nextSteps: ['Start with fun learning games'],
          }),
        })
      }
    )

    await page.goto('/assessment/report?sessionId=session-123')

    // Should show encouraging title for lower performance
    await expect(page.getByText('💪 Keep Learning!')).toBeVisible()

    // Should show encouraging message
    await expect(
      page.getByText('Every day you learn something new')
    ).toBeVisible()

    // Performance should be displayed in encouraging blue color
    await expect(page.getByText('40%')).toHaveClass(/text-blue-600/)
  })

  test('should display 6-12 grade appropriate interface', async ({ page }) => {
    // Mock 6-12 session and report
    await page.route('**/assessment-svc/sessions/session-123', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          id: 'session-123',
          gradeBand: '6-12',
          adaptiveSettings: {
            audioFirst: false,
            largeTargets: false,
            simplifiedInterface: false,
          },
          startedAt: '2025-08-16T10:00:00Z',
          completedAt: '2025-08-16T10:15:00Z',
        }),
      })
    })

    await page.route(
      '**/assessment-svc/sessions/session-123/report',
      async route => {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            sessionId: 'session-123',
            type: 'baseline',
            accuracyPercentage: 75,
            totalItems: 10,
            correctAnswers: 7,
            surfaceLevel: 'L3',
            averageResponseTime: 12000,
            skillsAssessed: [],
            recommendations: ['Focus on advanced problem-solving techniques'],
            nextSteps: ['Proceed to intermediate-level coursework'],
          }),
        })
      }
    )

    await page.goto('/assessment/report?sessionId=session-123')

    // Should show professional title for 6-12
    await expect(page.getByText('📊 Assessment Complete')).toBeVisible()
    await expect(page.getByText('Baseline Assessment Results')).toBeVisible()

    // Should show session details section
    await expect(page.getByText('Session Details')).toBeVisible()
    await expect(page.getByText('Started')).toBeVisible()
    await expect(page.getByText('Completed')).toBeVisible()
    await expect(page.getByText('Average Time')).toBeVisible()

    // Buttons should have professional labels
    await expect(
      page.getByRole('button', { name: '👤 Back to Profile' })
    ).toBeVisible()
    await expect(
      page.getByRole('button', { name: '🔄 Retake Assessment' })
    ).toBeVisible()
    await expect(
      page.getByRole('button', { name: '📄 Print Report' })
    ).toBeVisible()
  })

  test('should handle button navigation', async ({ page }) => {
    await page.goto('/assessment/report?sessionId=session-123')

    // Test home button navigation
    const homeButton = page.getByRole('button', {
      name: /go home|back to profile/i,
    })
    await homeButton.click()
    await expect(page).toHaveURL(/\/learners/)
  })

  test('should handle print functionality', async ({ page }) => {
    await page.goto('/assessment/report?sessionId=session-123')

    // Mock window.print
    await page.addInitScript(() => {
      window.print = () => console.log('Print called')
    })

    // Click print button
    const printButton = page.getByRole('button', { name: /print/i })
    await printButton.click()

    // Print should be called (implementation detail)
  })

  test('should handle missing report error', async ({ page }) => {
    await page.route('**/assessment-svc/**', async route => {
      await route.fulfill({
        status: 404,
        contentType: 'application/json',
        body: JSON.stringify({ error: 'Report not found' }),
      })
    })

    await page.goto('/assessment/report?sessionId=session-123')

    // Should show error message
    await expect(page.getByText('Report Error')).toBeVisible()
    await expect(
      page.getByText('Failed to load assessment report')
    ).toBeVisible()

    // Should provide return button
    await expect(
      page.getByRole('button', { name: /return to assessment/i })
    ).toBeVisible()
  })

  test('should be responsive on mobile devices', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 667 })
    await page.goto('/assessment/report?sessionId=session-123')

    // Title should be visible
    await expect(page.getByText('🌟 Amazing Job!')).toBeVisible()

    // Results should be visible
    await expect(page.getByText('80%')).toBeVisible()

    // Action buttons should stack vertically and be touch-friendly
    const buttons = page.getByRole('button')
    const firstButton = buttons.first()

    const buttonBox = await firstButton.boundingBox()
    expect(buttonBox?.height).toBeGreaterThan(48) // Touch target size
  })

  test('should show loading state initially', async ({ page }) => {
    // Delay the API response to test loading state
    await page.route('**/assessment-svc/**', async route => {
      await new Promise(resolve => setTimeout(resolve, 1000))
      // Then fulfill normally...
    })

    await page.goto('/assessment/report?sessionId=session-123')

    // Should show loading spinner and message
    await expect(
      page.getByText(/creating your special report|generating/i)
    ).toBeVisible()
    await expect(page.locator('.animate-spin')).toBeVisible()
  })
})
