import { test, expect } from '@playwright/test'

test.describe('S3-08 Baseline Assessment - Start Page', () => {
  test.beforeEach(async ({ page }) => {
    // Mock the assessment API
    await page.route('**/assessment-svc/**', async route => {
      const url = route.request().url()

      if (url.includes('/sessions') && route.request().method() === 'POST') {
        // Mock start assessment
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            id: 'session-123',
            learnerId: 'learner-456',
            type: 'baseline',
            status: 'in-progress',
            startedAt: new Date().toISOString(),
            currentItemIndex: 1,
            totalItems: 10,
            responses: [],
            estimatedLevel: 'L1',
            gradeBand: 'K-2',
            adaptiveSettings: {
              audioFirst: true,
              largeTargets: true,
              simplifiedInterface: true,
            },
          }),
        })
      }
    })
  })

  test('should display K-2 appropriate interface with large buttons', async ({
    page,
  }) => {
    await page.goto('/assessment/start?learnerId=learner-456&gradeBand=K-2')

    // Check for K-2 specific title
    await expect(page.getByText("🌟 Let's Play and Learn! 🌟")).toBeVisible()

    // Check for grade-appropriate description
    await expect(
      page.getByText("We're going to play some fun games")
    ).toBeVisible()

    // Check for adaptive settings section
    await expect(page.getByText('🎮 How would you like to play?')).toBeVisible()

    // Check for audio-first option
    await expect(page.getByText('🔊 Listen to questions first')).toBeVisible()

    // Check for large targets option
    await expect(page.getByText('🎯 Big buttons (easier to tap)')).toBeVisible()

    // Check for simplified interface option
    await expect(page.getByText('🌈 Simple, colorful design')).toBeVisible()

    // Check for large start button
    const startButton = page.getByRole('button', {
      name: /let's start playing/i,
    })
    await expect(startButton).toBeVisible()
    await expect(startButton).toHaveClass(/text-2xl|text-xl/)
  })

  test('should display 3-5 appropriate interface', async ({ page }) => {
    await page.goto('/assessment/start?learnerId=learner-456&gradeBand=3-5')

    // Check for 3-5 specific title
    await expect(
      page.getByText('🎯 Ready for Your Assessment? 🎯')
    ).toBeVisible()

    // Check for appropriate description
    await expect(
      page.getByText('This assessment helps us understand what you know')
    ).toBeVisible()

    // Check for simplified interface option (but not large targets)
    await expect(page.getByText('🎨 Simplified interface')).toBeVisible()
    await expect(page.getByText('🎯 Big buttons')).not.toBeVisible()

    // Start button should be appropriately sized
    const startButton = page.getByRole('button', { name: /begin assessment/i })
    await expect(startButton).toBeVisible()
  })

  test('should display 6-12 appropriate interface with time limit options', async ({
    page,
  }) => {
    await page.goto('/assessment/start?learnerId=learner-456&gradeBand=6-12')

    // Check for 6-12 specific title
    await expect(page.getByText('📝 Baseline Assessment')).toBeVisible()

    // Check for professional description
    await expect(
      page.getByText('This baseline assessment will help us understand')
    ).toBeVisible()

    // Check for time limit option
    await expect(page.getByText('⏱️ Time limit per question:')).toBeVisible()

    // Check for time limit dropdown
    const timeSelect = page.locator('select')
    await expect(timeSelect).toBeVisible()
    await expect(timeSelect).toHaveValue('60')

    // Should not show simplified interface or large targets options
    await expect(page.getByText('🌈 Simple, colorful design')).not.toBeVisible()
    await expect(page.getByText('🎯 Big buttons')).not.toBeVisible()
  })

  test('should handle adaptive settings changes', async ({ page }) => {
    await page.goto('/assessment/start?learnerId=learner-456&gradeBand=K-2')

    // Toggle audio-first setting
    const audioCheckbox = page.getByRole('checkbox').first()
    await expect(audioCheckbox).toBeChecked() // Should be checked by default for K-2

    await audioCheckbox.uncheck()
    await expect(audioCheckbox).not.toBeChecked()

    // Toggle large targets
    const largeTargetsCheckbox = page.getByRole('checkbox').nth(1)
    await largeTargetsCheckbox.uncheck()
    await expect(largeTargetsCheckbox).not.toBeChecked()
  })

  test('should start assessment and navigate to session page', async ({
    page,
  }) => {
    await page.goto('/assessment/start?learnerId=learner-456&gradeBand=K-2')

    // Click start button
    const startButton = page.getByRole('button', {
      name: /let's start playing/i,
    })
    await startButton.click()

    // Should navigate to session page
    await expect(page).toHaveURL(/\/assessment\/session\?sessionId=session-123/)
  })

  test('should auto-start assessment when autoStart=true', async ({ page }) => {
    await page.goto(
      '/assessment/start?learnerId=learner-456&gradeBand=K-2&autoStart=true'
    )

    // Should automatically redirect to session page
    await expect(page).toHaveURL(/\/assessment\/session/, { timeout: 5000 })
  })

  test('should show error for missing learner ID', async ({ page }) => {
    await page.goto('/assessment/start')

    // Should show error message
    await expect(page.getByText('Assessment Setup Required')).toBeVisible()
    await expect(page.getByText('A learner ID is required')).toBeVisible()

    // Should show link to go to learners page
    const goToLearnersButton = page.getByRole('button', {
      name: /go to learners/i,
    })
    await expect(goToLearnersButton).toBeVisible()
  })

  test('should handle API error gracefully', async ({ page }) => {
    // Mock API error
    await page.route('**/assessment-svc/**', async route => {
      await route.fulfill({
        status: 500,
        contentType: 'application/json',
        body: JSON.stringify({ error: 'Internal server error' }),
      })
    })

    await page.goto('/assessment/start?learnerId=learner-456&gradeBand=K-2')

    // Click start button
    const startButton = page.getByRole('button', {
      name: /let's start playing/i,
    })
    await startButton.click()

    // Should show error message
    await expect(page.getByText('Failed to start assessment')).toBeVisible()
  })

  test('should maintain responsive design on mobile viewports', async ({
    page,
  }) => {
    await page.setViewportSize({ width: 375, height: 667 }) // iPhone SE size
    await page.goto('/assessment/start?learnerId=learner-456&gradeBand=K-2')

    // Should still be visible and usable
    await expect(page.getByText("🌟 Let's Play and Learn! 🌟")).toBeVisible()

    const startButton = page.getByRole('button', {
      name: /let's start playing/i,
    })
    await expect(startButton).toBeVisible()

    // Button should be large enough for touch targets
    const buttonBox = await startButton.boundingBox()
    expect(buttonBox?.height).toBeGreaterThan(48) // Minimum touch target size
  })
})
