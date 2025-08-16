import { test, expect, type Page } from '@playwright/test'

test.describe('S3-09 Learning Session Player with AI Copilot', () => {
  let page: Page

  test.beforeEach(async ({ browser }) => {
    page = await browser.newPage()

    // Mock the API endpoints
    await page.route('**/api/lessons/**', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          id: 'test-lesson-1',
          title: 'Introduction to Algebra',
          description: 'Basic algebraic concepts and operations',
          estimatedDuration: 1800, // 30 minutes
          difficultyLevel: 'beginner',
          gameBreakConfig: {
            enabled: true,
            intervalMinutes: 5,
            durationMinutes: 2,
            motivationalMessages: [
              'Great job! Time for a quick break!',
              "You're doing amazing! Stretch those muscles!",
            ],
          },
          sections: [
            {
              id: 'section-1',
              title: 'What is Algebra?',
              order: 1,
              content: [
                {
                  id: 'content-1',
                  type: 'text',
                  title: 'Introduction',
                  content: {
                    text: 'Algebra is a branch of mathematics dealing with symbols and the rules for manipulating those symbols.',
                  },
                },
                {
                  id: 'content-2',
                  type: 'video',
                  title: 'Algebra Basics Video',
                  content: {
                    url: '/test-video.mp4',
                    duration: 120,
                  },
                },
              ],
            },
          ],
          metadata: {
            version: '1.0',
            tags: ['algebra', 'mathematics', 'beginner'],
            backgroundAudioUrl: '/test-background.mp3',
          },
        }),
      })
    })

    await page.route('**/api/learning-sessions', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          id: 'session-123',
          lessonId: 'test-lesson-1',
          learnerId: 'test-learner',
          status: 'active',
          startedAt: new Date().toISOString(),
          progress: {
            completedSections: [],
            currentSectionId: 'section-1',
            currentContentId: 'content-1',
            timeSpent: 0,
            interactionCount: 0,
          },
          gameBreaks: [],
        }),
      })
    })

    await page.route('**/api/chat-sessions', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          id: 'chat-session-123',
          learnerId: 'test-learner',
          lessonId: 'test-lesson-1',
          messages: [],
          createdAt: new Date().toISOString(),
        }),
      })
    })

    await page.route('**/api/inference/stream', async route => {
      if (route.request().method() === 'POST') {
        // Mock SSE streaming response
        const response =
          'data: {"type":"start","messageId":"msg-123"}\n\n' +
          'data: {"type":"content","content":"Hello! I\'m your AI learning assistant. "}\n\n' +
          'data: {"type":"content","content":"How can I help you understand algebra better?"}\n\n' +
          'data: {"type":"end","messageId":"msg-123"}\n\n'

        await route.fulfill({
          status: 200,
          headers: {
            'Content-Type': 'text/event-stream',
            'Cache-Control': 'no-cache',
            Connection: 'keep-alive',
          },
          body: response,
        })
      }
    })

    await page.route('**/api/events', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ success: true }),
      })
    })
  })

  test('should load learning session player with lesson content', async () => {
    await page.goto('/learn/test-lesson-1?learnerId=test-learner')

    // Wait for the lesson to load
    await expect(page.locator('[data-testid="lesson-title"]')).toContainText(
      'Introduction to Algebra'
    )

    // Check that lesson content is displayed
    await expect(page.locator('[data-testid="lesson-content"]')).toBeVisible()
    await expect(page.locator('text=What is Algebra?')).toBeVisible()
    await expect(
      page.locator('text=Algebra is a branch of mathematics')
    ).toBeVisible()

    // Check that toolbar is present
    await expect(page.locator('[data-testid="learning-toolbar"]')).toBeVisible()
    await expect(
      page.locator('[data-testid="play-pause-button"]')
    ).toBeVisible()
  })

  test('should open and interact with AI copilot chat', async () => {
    await page.goto('/learn/test-lesson-1?learnerId=test-learner')

    // Wait for lesson to load
    await expect(page.locator('[data-testid="lesson-title"]')).toContainText(
      'Introduction to Algebra'
    )

    // Open chat panel
    await page.click('[data-testid="toggle-chat-button"]')
    await expect(page.locator('[data-testid="chat-panel"]')).toBeVisible()

    // Send a message to the AI copilot
    const chatInput = page.locator('[data-testid="chat-input"]')
    await chatInput.fill('Can you explain what variables are in algebra?')
    await page.click('[data-testid="send-message-button"]')

    // Check that message appears in chat
    await expect(
      page.locator('text=Can you explain what variables are')
    ).toBeVisible()

    // Check that AI responds with streaming content
    await expect(
      page.locator("text=Hello! I'm your AI learning assistant")
    ).toBeVisible()
    await expect(
      page.locator('text=How can I help you understand algebra better?')
    ).toBeVisible()

    // Check streaming indicator appears during response
    await expect(page.locator('[data-testid="typing-indicator"]')).toBeVisible()
  })

  test('should handle game break timer and display', async () => {
    await page.goto('/learn/test-lesson-1?learnerId=test-learner')

    // Start the learning session
    await page.click('[data-testid="play-pause-button"]')

    // Check that game break timer is displayed in toolbar
    const gameBreakTimer = page.locator('[data-testid="game-break-timer"]')
    await expect(gameBreakTimer).toBeVisible()
    await expect(gameBreakTimer).toContainText('Next break in')

    // Mock fast-forward to game break time
    await page.evaluate(() => {
      // Simulate game break trigger
      window.dispatchEvent(
        new CustomEvent('gameBreakTriggered', {
          detail: {
            type: 'focus',
            message: 'Great job! Time for a quick break!',
            duration: 120,
          },
        })
      )
    })

    // Check game break overlay appears
    await expect(
      page.locator('[data-testid="game-break-overlay"]')
    ).toBeVisible()
    await expect(
      page.locator('text=Great job! Time for a quick break!')
    ).toBeVisible()

    // Check countdown timer
    await expect(
      page.locator('[data-testid="game-break-countdown"]')
    ).toBeVisible()
    await expect(
      page.locator('[data-testid="game-break-countdown"]')
    ).toContainText('2:00')
  })

  test('should handle audio controls and volume adjustment', async () => {
    await page.goto('/learn/test-lesson-1?learnerId=test-learner')

    // Check if audio controls are present (when background audio is available)
    const audioControls = page.locator('[data-testid="audio-controls"]')

    if (await audioControls.isVisible()) {
      // Test volume slider
      const volumeSlider = page.locator('[data-testid="volume-slider"]')
      await expect(volumeSlider).toBeVisible()

      // Adjust volume
      await volumeSlider.fill('0.5')
      await expect(page.locator('text=50%')).toBeVisible()

      // Test mute button
      await page.click('[data-testid="volume-mute-button"]')
      await expect(page.locator('text=0%')).toBeVisible()
    }
  })

  test('should track lesson progress and interactions', async () => {
    await page.goto('/learn/test-lesson-1?learnerId=test-learner')

    // Start the session
    await page.click('[data-testid="play-pause-button"]')

    // Interact with content
    await page.click('[data-testid="lesson-content"] text=Algebra is a branch')

    // Check that progress is tracked
    const progressBar = page.locator('[data-testid="progress-bar"]')
    if (await progressBar.isVisible()) {
      // Progress should start updating
      await expect(progressBar).toHaveAttribute('data-progress')
    }

    // Check section navigation
    if (await page.locator('[data-testid="section-nav"]').isVisible()) {
      await expect(
        page.locator('[data-testid="current-section"]')
      ).toContainText('section-1')
    }
  })

  test('should handle offline mode and event queuing', async () => {
    await page.goto('/learn/test-lesson-1?learnerId=test-learner')

    // Start session
    await page.click('[data-testid="play-pause-button"]')

    // Simulate offline mode
    await page.context().setOffline(true)

    // Try to send chat message while offline
    await page.click('[data-testid="toggle-chat-button"]')
    const chatInput = page.locator('[data-testid="chat-input"]')
    await chatInput.fill('This message should be queued')
    await page.click('[data-testid="send-message-button"]')

    // Check offline indicator
    await expect(
      page.locator('[data-testid="offline-indicator"]')
    ).toBeVisible()
    await expect(
      page.locator(
        'text=Offline - messages will be sent when connection is restored'
      )
    ).toBeVisible()

    // Go back online
    await page.context().setOffline(false)

    // Check that offline indicator disappears and messages are sent
    await expect(
      page.locator('[data-testid="offline-indicator"]')
    ).not.toBeVisible()
  })

  test('should handle session pause and resume', async () => {
    await page.goto('/learn/test-lesson-1?learnerId=test-learner')

    // Start session
    const playPauseButton = page.locator('[data-testid="play-pause-button"]')
    await playPauseButton.click()

    // Check that session is playing
    await expect(playPauseButton).toHaveAttribute('data-playing', 'true')

    // Pause session
    await playPauseButton.click()
    await expect(playPauseButton).toHaveAttribute('data-playing', 'false')

    // Check that timers are paused
    const gameBreakTimer = page.locator('[data-testid="game-break-timer"]')
    if (await gameBreakTimer.isVisible()) {
      await expect(gameBreakTimer).toContainText('Paused')
    }
  })

  test('should handle video and media content with volume control', async () => {
    await page.goto('/learn/test-lesson-1?learnerId=test-learner')

    // Navigate to section with video content
    const videoContent = page.locator('video')
    if (await videoContent.isVisible()) {
      // Check video controls are present
      await expect(videoContent).toHaveAttribute('controls')

      // Test video interaction tracking
      await videoContent.click() // Play video

      // Volume should be controlled by the global volume setting
      const volume = await videoContent.evaluate(
        video => (video as HTMLVideoElement).volume
      )
      expect(volume).toBe(1.0) // Default volume
    }
  })

  test('should handle lesson completion and next steps', async () => {
    await page.goto('/learn/test-lesson-1?learnerId=test-learner')

    // Start session
    await page.click('[data-testid="play-pause-button"]')

    // Simulate lesson completion
    await page.evaluate(() => {
      window.dispatchEvent(
        new CustomEvent('lessonCompleted', {
          detail: {
            lessonId: 'test-lesson-1',
            timeSpent: 1800,
            completionPercentage: 100,
          },
        })
      )
    })

    // Check completion UI
    if (await page.locator('[data-testid="lesson-complete"]').isVisible()) {
      await expect(page.locator('text=Lesson Complete!')).toBeVisible()
      await expect(
        page.locator('[data-testid="next-lesson-button"]')
      ).toBeVisible()
    }
  })

  test('should handle error states gracefully', async () => {
    // Mock API error for lesson loading
    await page.route('**/api/lessons/**', async route => {
      await route.fulfill({
        status: 404,
        contentType: 'application/json',
        body: JSON.stringify({ error: 'Lesson not found' }),
      })
    })

    await page.goto('/learn/invalid-lesson-id?learnerId=test-learner')

    // Check error message
    await expect(page.locator('[data-testid="error-message"]')).toBeVisible()
    await expect(page.locator('text=Lesson not found')).toBeVisible()

    // Check retry button
    await expect(page.locator('[data-testid="retry-button"]')).toBeVisible()
  })

  test('should handle telemetry and event tracking', async () => {
    let eventsSent: any[] = []

    await page.route('**/api/events', async route => {
      const body = await route.request().postDataJSON()
      eventsSent.push(...body.events)

      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ success: true }),
      })
    })

    await page.goto('/learn/test-lesson-1?learnerId=test-learner')

    // Start session
    await page.click('[data-testid="play-pause-button"]')

    // Interact with content
    await page.click('[data-testid="lesson-content"]')

    // Open chat
    await page.click('[data-testid="toggle-chat-button"]')

    // Wait for events to be sent
    await page.waitForTimeout(2000)

    // Check that telemetry events were sent
    expect(eventsSent.length).toBeGreaterThan(0)

    // Check for specific event types
    const eventTypes = eventsSent.map(event => event.type)
    expect(eventTypes).toContain('session_started')
    expect(eventTypes).toContain('content_viewed')
    expect(eventTypes).toContain('chat_opened')
  })
})
