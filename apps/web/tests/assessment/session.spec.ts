import { test, expect } from '@playwright/test'

test.describe('S3-08 Baseline Assessment - Session Flow', () => {
  test.beforeEach(async ({ page }) => {
    // Mock the assessment API
    await page.route('**/assessment-svc/**', async route => {
      const url = route.request().url()
      const method = route.request().method()

      if (url.includes('/sessions/session-123') && method === 'GET') {
        // Mock get session
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
            totalItems: 5,
            responses: [],
            estimatedLevel: 'L1',
            gradeBand: 'K-2',
            adaptiveSettings: {
              audioFirst: true,
              largeTargets: true,
              simplifiedInterface: true,
              timeLimit: 60,
            },
          }),
        })
      } else if (
        url.includes('/sessions/session-123/next') &&
        method === 'GET'
      ) {
        // Mock get next item
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            item: {
              id: 'item-1',
              type: 'multiple-choice',
              question: 'What color is the sky?',
              audioUrl: 'https://example.com/audio.mp3',
              imageUrl: 'https://example.com/sky.jpg',
              options: [
                { id: 'a', text: 'Blue' },
                { id: 'b', text: 'Red' },
                { id: 'c', text: 'Green' },
                { id: 'd', text: 'Yellow' },
              ],
              difficultyLevel: 'L1',
              estimatedDuration: 30,
            },
            isComplete: false,
            sessionUpdate: {},
          }),
        })
      } else if (
        url.includes('/sessions/session-123/respond') &&
        method === 'POST'
      ) {
        // Mock submit response
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            item: {
              id: 'item-2',
              type: 'multiple-choice',
              question: 'How many legs does a cat have?',
              options: [
                { id: 'a', text: '2' },
                { id: 'b', text: '4' },
                { id: 'c', text: '6' },
                { id: 'd', text: '8' },
              ],
              difficultyLevel: 'L1',
              estimatedDuration: 30,
            },
            isComplete: false,
            sessionUpdate: { currentItemIndex: 2 },
          }),
        })
      } else if (
        url.includes('/sessions/session-123/pause') &&
        method === 'POST'
      ) {
        // Mock pause session
        await route.fulfill({ status: 200, body: '{}' })
      } else if (
        url.includes('/sessions/session-123/resume') &&
        method === 'POST'
      ) {
        // Mock resume session
        await route.fulfill({ status: 200, body: '{}' })
      }
    })
  })

  test('should display K-2 assessment interface with large buttons', async ({
    page,
  }) => {
    await page.goto('/assessment/session?sessionId=session-123')

    // Wait for content to load
    await expect(page.getByText('What color is the sky?')).toBeVisible()

    // Check for K-2 specific progress indicator
    await expect(page.getByText('🌟 Question 1')).toBeVisible()

    // Check for audio button (K-2 specific)
    await expect(page.getByRole('button', { name: /listen/i })).toBeVisible()

    // Check for large answer buttons
    const answerButtons = page
      .getByRole('button')
      .filter({ hasText: /Blue|Red|Green|Yellow/ })
    await expect(answerButtons).toHaveCount(4)

    // Buttons should have large text and spacing for K-2
    const firstButton = answerButtons.first()
    await expect(firstButton).toHaveClass(/text-2xl|text-xl/)
  })

  test('should handle multiple choice question interaction', async ({
    page,
  }) => {
    await page.goto('/assessment/session?sessionId=session-123')

    // Wait for question to load
    await expect(page.getByText('What color is the sky?')).toBeVisible()

    // Click on "Blue" answer
    const blueButton = page.getByRole('button', { name: /Blue/ })
    await blueButton.click()

    // Should advance to next question
    await expect(page.getByText('How many legs does a cat have?')).toBeVisible()
  })

  test('should display question image when available', async ({ page }) => {
    await page.goto('/assessment/session?sessionId=session-123')

    // Check for question image
    const image = page.locator('img[alt="Question illustration"]')
    await expect(image).toBeVisible()
    await expect(image).toHaveAttribute('src', 'https://example.com/sky.jpg')
  })

  test('should show progress indicator', async ({ page }) => {
    await page.goto('/assessment/session?sessionId=session-123')

    // Check for progress information
    await expect(page.getByText('Question 1')).toBeVisible()
    await expect(page.getByText('1 of 5')).toBeVisible()

    // Check for progress bar
    const progressBar = page.locator('.bg-blue-600').first()
    await expect(progressBar).toBeVisible()
  })

  test('should handle pause and resume functionality', async ({ page }) => {
    await page.goto('/assessment/session?sessionId=session-123')

    // Click pause button
    const pauseButton = page.getByRole('button', {
      name: /take a break|pause/i,
    })
    await pauseButton.click()

    // Should show pause overlay
    await expect(
      page.getByText(/taking a break|assessment paused/i)
    ).toBeVisible()

    // Click resume button in overlay
    const resumeButton = page.getByRole('button', { name: /continue|resume/i })
    await resumeButton.click()

    // Overlay should disappear
    await expect(
      page.getByText(/taking a break|assessment paused/i)
    ).not.toBeVisible()
  })

  test('should handle audio playback for K-2', async ({ page }) => {
    await page.goto('/assessment/session?sessionId=session-123')

    // Mock audio API
    await page.addInitScript(() => {
      window.HTMLAudioElement.prototype.play = async () => {}
      window.HTMLAudioElement.prototype.pause = () => {}
    })

    // Click audio button
    const audioButton = page.getByRole('button', { name: /listen/i })
    await audioButton.click()

    // Button should show playing state (implementation may vary)
    // This test mainly ensures the button is clickable and doesn't crash
  })

  test('should show timer for 6-12 grade band', async ({ page }) => {
    // Mock session with 6-12 grade band
    await page.route('**/assessment-svc/sessions/session-123', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          id: 'session-123',
          learnerId: 'learner-456',
          type: 'baseline',
          status: 'in-progress',
          gradeBand: '6-12',
          adaptiveSettings: {
            audioFirst: false,
            largeTargets: false,
            simplifiedInterface: false,
            timeLimit: 60,
          },
          currentItemIndex: 1,
          totalItems: 5,
          responses: [],
        }),
      })
    })

    await page.goto('/assessment/session?sessionId=session-123')

    // Should show timer for 6-12
    await expect(page.locator('svg')).toBeVisible() // Timer icon
    await expect(page.getByText(/\d+:\d+/)).toBeVisible() // Timer display
  })

  test('should handle text input questions', async ({ page }) => {
    // Mock text input question
    await page.route(
      '**/assessment-svc/sessions/session-123/next',
      async route => {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            item: {
              id: 'item-text',
              type: 'text-input',
              question: 'Describe your favorite animal in one sentence.',
              difficultyLevel: 'L1',
              estimatedDuration: 60,
            },
            isComplete: false,
            sessionUpdate: {},
          }),
        })
      }
    )

    await page.goto('/assessment/session?sessionId=session-123')

    // Should show text area
    const textArea = page.locator('textarea')
    await expect(textArea).toBeVisible()

    // Type answer
    await textArea.fill('My favorite animal is a dog because they are loyal.')

    // Submit answer
    const submitButton = page.getByRole('button', { name: /submit/i })
    await submitButton.click()
  })

  test('should handle session completion', async ({ page }) => {
    // Mock completed session
    await page.route(
      '**/assessment-svc/sessions/session-123/respond',
      async route => {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            item: null,
            isComplete: true,
            sessionUpdate: { status: 'completed' },
          }),
        })
      }
    )

    await page.route(
      '**/assessment-svc/sessions/session-123/complete',
      async route => {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            id: 'session-123',
            status: 'completed',
            completedAt: new Date().toISOString(),
          }),
        })
      }
    )

    await page.goto('/assessment/session?sessionId=session-123')

    // Answer the question to complete
    const blueButton = page.getByRole('button', { name: /Blue/ })
    await blueButton.click()

    // Should navigate to report page
    await expect(page).toHaveURL(/\/assessment\/report\?sessionId=session-123/)
  })

  test('should be responsive on mobile devices', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 667 })
    await page.goto('/assessment/session?sessionId=session-123')

    // Question should be visible
    await expect(page.getByText('What color is the sky?')).toBeVisible()

    // Answer buttons should be appropriately sized for touch
    const answerButtons = page
      .getByRole('button')
      .filter({ hasText: /Blue|Red|Green|Yellow/ })
    const firstButton = answerButtons.first()

    const buttonBox = await firstButton.boundingBox()
    expect(buttonBox?.height).toBeGreaterThan(48) // Minimum touch target
  })

  test('should handle API errors gracefully', async ({ page }) => {
    await page.route('**/assessment-svc/**', async route => {
      await route.fulfill({
        status: 500,
        contentType: 'application/json',
        body: JSON.stringify({ error: 'Server error' }),
      })
    })

    await page.goto('/assessment/session?sessionId=session-123')

    // Should show error message
    await expect(page.getByText(/failed to load|error/i)).toBeVisible()
  })
})
