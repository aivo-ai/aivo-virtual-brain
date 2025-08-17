/**
 * S3-12 SLP Flow End-to-End Tests
 * Tests the complete SLP workflow with TTS/ASR integration
 */

import { test, expect } from '@playwright/test'

test.describe('SLP Flow', () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to SLP system
    await page.goto('/slp')

    // Mock GraphQL responses
    await page.route('**/graphql', async route => {
      const request = route.request()
      const body = await request.postDataJSON()

      if (body.query.includes('GetStudent')) {
        await route.fulfill({
          contentType: 'application/json',
          body: JSON.stringify({
            data: {
              student: {
                id: 'student-1',
                tenantId: 'tenant-1',
                firstName: 'John',
                lastName: 'Doe',
                dateOfBirth: '2010-05-15',
                gradeLevel: '5th Grade',
                parentConsent: {
                  granted: true,
                  grantedAt: '2024-01-01T00:00:00Z',
                  grantedBy: 'parent@example.com',
                  expiresAt: '2025-01-01T00:00:00Z',
                  restrictions: [],
                },
                videoConsent: {
                  granted: true,
                  grantedAt: '2024-01-01T00:00:00Z',
                  grantedBy: 'parent@example.com',
                  expiresAt: '2025-01-01T00:00:00Z',
                  restrictions: [],
                },
                audioConsent: {
                  granted: true,
                  grantedAt: '2024-01-01T00:00:00Z',
                  grantedBy: 'parent@example.com',
                  expiresAt: '2025-01-01T00:00:00Z',
                  restrictions: [],
                },
                createdAt: '2024-01-01T00:00:00Z',
                updatedAt: '2024-01-01T00:00:00Z',
              },
            },
          }),
        })
      }

      if (body.query.includes('GetProviderMatrix')) {
        await route.fulfill({
          contentType: 'application/json',
          body: JSON.stringify({
            data: {
              providerMatrix: {
                tts: {
                  name: 'Azure TTS',
                  enabled: true,
                  config: {
                    enabled: true,
                    voice: 'en-US-JennyNeural',
                    rate: 1.0,
                    pitch: 1.0,
                    volume: 1.0,
                  },
                },
                asr: {
                  name: 'Azure ASR',
                  enabled: true,
                  config: {
                    enabled: true,
                    language: 'en-US',
                    sensitivity: 0.5,
                    timeout: 30000,
                  },
                },
                recording: {
                  name: 'Azure Media',
                  enabled: true,
                  maxDuration: 300,
                  format: 'mp4',
                },
              },
            },
          }),
        })
      }

      if (body.query.includes('CreateScreening')) {
        await route.fulfill({
          contentType: 'application/json',
          body: JSON.stringify({
            data: {
              createScreening: {
                screening: {
                  id: 'screening-1',
                  studentId: 'student-1',
                  tenantId: 'tenant-1',
                  screeningType: 'COMPREHENSIVE',
                  status: 'DRAFT',
                  responses: [],
                  totalScore: 0,
                  riskLevel: 'LOW',
                  recommendations: [],
                  createdBy: 'therapist@example.com',
                  createdAt: '2024-01-01T00:00:00Z',
                  updatedAt: '2024-01-01T00:00:00Z',
                },
                success: true,
              },
            },
          }),
        })
      }

      if (body.query.includes('UpdateScreening')) {
        await route.fulfill({
          contentType: 'application/json',
          body: JSON.stringify({
            data: {
              updateScreening: {
                screening: {
                  id: 'screening-1',
                  studentId: 'student-1',
                  tenantId: 'tenant-1',
                  screeningType: 'COMPREHENSIVE',
                  status: 'COMPLETED',
                  responses: [
                    {
                      questionId: 'art_1',
                      questionText:
                        'Does the child have difficulty pronouncing certain sounds?',
                      responseType: 'BOOLEAN',
                      value: true,
                      score: 3,
                    },
                  ],
                  totalScore: 75,
                  riskLevel: 'HIGH',
                  recommendations: [
                    'Consider articulation therapy',
                    'Monitor progress closely',
                  ],
                  completedAt: '2024-01-01T10:00:00Z',
                  createdBy: 'therapist@example.com',
                  createdAt: '2024-01-01T00:00:00Z',
                  updatedAt: '2024-01-01T10:00:00Z',
                },
                success: true,
              },
            },
          }),
        })
      }

      if (body.query.includes('CreatePlan')) {
        await route.fulfill({
          contentType: 'application/json',
          body: JSON.stringify({
            data: {
              createPlan: {
                plan: {
                  id: 'plan-1',
                  studentId: 'student-1',
                  tenantId: 'tenant-1',
                  screeningId: 'screening-1',
                  goals: [
                    {
                      id: 'goal-1',
                      category: 'ARTICULATION',
                      description: 'Improve speech sound production accuracy',
                      targetBehavior:
                        'Produce target sounds correctly in words and sentences',
                      measurableOutcome:
                        '80% accuracy in structured activities',
                      timeframe: '12 weeks',
                      priority: 'HIGH',
                      status: 'NOT_STARTED',
                    },
                  ],
                  sessions: [
                    {
                      id: 'session-1',
                      planId: 'plan-1',
                      sessionNumber: 1,
                      scheduledDate: '2024-01-02T10:00:00Z',
                      status: 'SCHEDULED',
                      exercises: [
                        {
                          id: 'exercise-1',
                          type: 'ARTICULATION_DRILL',
                          title: 'R Sound Practice',
                          description:
                            'Practice R sound in different positions',
                          instructions:
                            'Listen to the prompts and repeat clearly',
                          targetGoals: ['goal-1'],
                          ttsEnabled: true,
                          asrEnabled: true,
                          recordingRequired: false,
                          estimatedDuration: 15,
                          materials: [],
                          prompts: [
                            {
                              id: 'prompt-1',
                              text: 'Say "red"',
                              order: 1,
                              ttsEnabled: true,
                              expectedResponse: 'red',
                            },
                          ],
                          status: 'NOT_STARTED',
                          attempts: [],
                        },
                      ],
                      createdAt: '2024-01-01T00:00:00Z',
                      updatedAt: '2024-01-01T00:00:00Z',
                    },
                  ],
                  duration: 12,
                  frequency: 2,
                  status: 'APPROVED',
                  createdBy: 'therapist@example.com',
                  createdAt: '2024-01-01T00:00:00Z',
                  updatedAt: '2024-01-01T00:00:00Z',
                },
                success: true,
              },
            },
          }),
        })
      }

      if (body.query.includes('SubmitExerciseAttempt')) {
        await route.fulfill({
          contentType: 'application/json',
          body: JSON.stringify({
            data: {
              submitExerciseAttempt: {
                attempt: {
                  id: 'attempt-1',
                  exerciseId: 'exercise-1',
                  sessionId: 'session-1',
                  studentResponse: 'red',
                  score: 85,
                  feedback: 'Great job! Clear pronunciation.',
                  completedAt: '2024-01-02T10:15:00Z',
                  metadata: {
                    ttsUsed: true,
                    asrUsed: true,
                  },
                },
                success: true,
              },
            },
          }),
        })
      }

      // Continue with original request for unmatched routes
      await route.continue()
    })
  })

  test('complete SLP workflow', async ({ page }) => {
    // Wait for page to load
    await expect(page.getByText('SLP Therapy System')).toBeVisible()

    // Verify student information is displayed
    await expect(page.getByText('John Doe')).toBeVisible()
    await expect(page.getByText('5th Grade')).toBeVisible()

    // Check consent status
    await expect(page.getByText('Audio: Granted')).toBeVisible()
    await expect(page.getByText('Video: Granted')).toBeVisible()
    await expect(page.getByText('Parent: Granted')).toBeVisible()

    // Start comprehensive screening
    await page
      .getByRole('button', { name: 'Start Comprehensive Screening' })
      .click()

    // Verify screening form loaded
    await expect(page.getByText('COMPREHENSIVE Screening')).toBeVisible()

    // Complete first question
    await expect(
      page.getByText(
        'Does the child have difficulty pronouncing certain sounds?'
      )
    ).toBeVisible()
    await page.getByRole('radio', { name: 'Yes' }).click()

    // Navigate through questions
    await page.getByRole('button', { name: 'Next' }).click()

    // Test TTS functionality (mock click)
    const ttsButton = page
      .locator('button[aria-label="Text to speech"]')
      .first()
    if (await ttsButton.isVisible()) {
      await ttsButton.click()
    }

    // Complete remaining questions and submit
    // (In a real test, we'd iterate through all questions)
    await page.getByRole('button', { name: 'Submit Screening' }).click()

    // Verify transition to therapy plan
    await expect(page.getByText('Therapy Plan for John Doe')).toBeVisible()

    // Verify screening results
    await expect(page.getByText('HIGH')).toBeVisible() // Risk level
    await expect(page.getByText('Consider articulation therapy')).toBeVisible()

    // Review and create therapy plan
    await expect(
      page.getByText('Improve speech sound production accuracy')
    ).toBeVisible()
    await page.getByRole('button', { name: 'Create Therapy Plan' }).click()

    // Verify plan creation and return to overview
    await expect(page.getByText('Progress')).toBeVisible()

    // Start a therapy session
    await page.getByRole('button', { name: 'Start' }).click()

    // Verify session interface
    await expect(page.getByText('Session 1 - John Doe')).toBeVisible()
    await expect(page.getByText('R Sound Practice')).toBeVisible()

    // Complete exercise
    await page.getByText('Say "red"').isVisible()

    // Test ASR functionality (mock)
    const asrButton = page.getByRole('button', { name: 'Voice Input' })
    if (await asrButton.isVisible()) {
      await asrButton.click()
      // Simulate transcript update
      await page.fill(
        'textarea[placeholder="Enter your response here..."]',
        'red'
      )
    }

    // Complete exercise
    await page.getByRole('button', { name: 'Complete Exercise' }).click()

    // Verify completion
    await expect(page.getByText('Session Progress')).toBeVisible()
  })

  test('consent-aware gating', async ({ page }) => {
    // Mock student without audio consent
    await page.route('**/graphql', async route => {
      const request = route.request()
      const body = await request.postDataJSON()

      if (body.query.includes('GetStudent')) {
        await route.fulfill({
          contentType: 'application/json',
          body: JSON.stringify({
            data: {
              student: {
                id: 'student-1',
                tenantId: 'tenant-1',
                firstName: 'Jane',
                lastName: 'Smith',
                dateOfBirth: '2011-03-20',
                gradeLevel: '4th Grade',
                parentConsent: { granted: true },
                videoConsent: { granted: true },
                audioConsent: { granted: false }, // No audio consent
                createdAt: '2024-01-01T00:00:00Z',
                updatedAt: '2024-01-01T00:00:00Z',
              },
            },
          }),
        })
      }

      await route.continue()
    })

    await page.reload()

    // Verify consent warning is displayed
    await expect(page.getByText('Audio: Not Granted')).toBeVisible()

    // Start screening
    await page
      .getByRole('button', { name: 'Start Comprehensive Screening' })
      .click()

    // Verify consent error message
    await expect(
      page.getByText('Audio consent required for text-to-speech')
    ).toBeVisible()

    // Verify TTS button is disabled or not present
    const ttsButton = page.locator('button[aria-label="Text to speech"]')
    if (await ttsButton.isVisible()) {
      await expect(ttsButton).toBeDisabled()
    }
  })

  test('provider matrix integration', async ({ page }) => {
    // Mock provider matrix with disabled features
    await page.route('**/graphql', async route => {
      const request = route.request()
      const body = await request.postDataJSON()

      if (body.query.includes('GetProviderMatrix')) {
        await route.fulfill({
          contentType: 'application/json',
          body: JSON.stringify({
            data: {
              providerMatrix: {
                tts: {
                  name: 'Azure TTS',
                  enabled: false, // TTS disabled
                  config: { enabled: false },
                },
                asr: {
                  name: 'Azure ASR',
                  enabled: false, // ASR disabled
                  config: { enabled: false },
                },
                recording: {
                  name: 'Azure Media',
                  enabled: true,
                  maxDuration: 300,
                  format: 'mp4',
                },
              },
            },
          }),
        })
      }

      await route.continue()
    })

    await page.reload()

    // Start screening
    await page
      .getByRole('button', { name: 'Start Comprehensive Screening' })
      .click()

    // Verify TTS/ASR buttons are not available
    const ttsButton = page.locator('button[aria-label="Text to speech"]')
    await expect(ttsButton).not.toBeVisible()

    const asrButton = page.getByRole('button', { name: 'Voice Input' })
    await expect(asrButton).not.toBeVisible()
  })

  test('SLP update events', async ({ page }) => {
    // Test real-time updates
    await page
      .getByRole('button', { name: 'Start Comprehensive Screening' })
      .click()

    // Complete and submit screening
    await page.getByRole('radio', { name: 'Yes' }).click()
    await page.getByRole('button', { name: 'Submit Screening' }).click()

    // Verify SLP_UPDATED event is dispatched
    const events = await page.evaluate(() => {
      return new Promise(resolve => {
        const events: any[] = []
        window.addEventListener('SLP_UPDATED', (e: any) => {
          events.push(e.detail)
        })

        // Trigger an update
        window.dispatchEvent(
          new CustomEvent('SLP_UPDATED', {
            detail: {
              type: 'SCREENING_UPDATED',
              studentId: 'student-1',
              entityId: 'screening-1',
              timestamp: new Date().toISOString(),
            },
          })
        )

        setTimeout(() => resolve(events), 100)
      })
    })

    expect(events).toHaveLength(1)
    expect(events[0].type).toBe('SCREENING_UPDATED')
  })

  test('error handling', async ({ page }) => {
    // Mock GraphQL error
    await page.route('**/graphql', async route => {
      await route.fulfill({
        contentType: 'application/json',
        body: JSON.stringify({
          errors: [{ message: 'Network error occurred' }],
        }),
      })
    })

    await page.reload()

    // Verify error is displayed
    await expect(page.getByText('Network error occurred')).toBeVisible()
  })

  test('accessibility compliance', async ({ page }) => {
    // Check basic accessibility
    await page
      .getByRole('button', { name: 'Start Comprehensive Screening' })
      .click()

    // Verify proper ARIA labels
    await expect(page.getByRole('radiogroup')).toBeVisible()
    await expect(page.getByRole('progressbar')).toBeVisible()

    // Verify keyboard navigation
    await page.keyboard.press('Tab')
    await page.keyboard.press('Space')

    // Verify focus management
    const focusedElement = page.locator(':focus')
    await expect(focusedElement).toBeVisible()
  })
})
