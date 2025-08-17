/**
 * S3-12 Simple SLP Flow Tests
 * Tests the SLP workflow with basic functionality
 */

import { test, expect } from '@playwright/test'

test.describe('Simple SLP Flow', () => {
  test.beforeEach(async ({ page }) => {
    // Mock student data for testing
    await page.addInitScript(() => {
      // Mock the API calls
      const mockStudent = {
        id: 'student-1',
        tenantId: 'tenant-1',
        firstName: 'John',
        lastName: 'Doe',
        dateOfBirth: '2010-05-15',
        gradeLevel: '5th Grade',
        parentConsent: { granted: true },
        videoConsent: { granted: true },
        audioConsent: { granted: true },
      }

      const mockProviderMatrix = {
        tts: { name: 'Mock TTS', enabled: true },
        asr: { name: 'Mock ASR', enabled: true },
        recording: { name: 'Mock Recording', enabled: true },
      }

      // Mock the SLP client
      window.mockSLPClient = {
        getStudent: () => Promise.resolve(mockStudent),
        getProviderMatrix: () => Promise.resolve(mockProviderMatrix),
      }
    })

    // Navigate to SLP page
    await page.goto('/slp/student-1')
  })

  test('displays student information', async ({ page }) => {
    // Wait for the page to load
    await expect(page.getByText('SLP Therapy System')).toBeVisible()

    // Check if student info is displayed
    await expect(page.getByText('John Doe')).toBeVisible()
    await expect(page.getByText('5th Grade')).toBeVisible()

    // Check consent status
    await expect(page.getByText('Audio: Granted')).toBeVisible()
    await expect(page.getByText('Video: Granted')).toBeVisible()
    await expect(page.getByText('Parent: Granted')).toBeVisible()
  })

  test('can start screening process', async ({ page }) => {
    // Wait for page to load
    await expect(page.getByText('SLP Therapy System')).toBeVisible()

    // Start screening
    await page
      .getByRole('button', { name: 'Start Comprehensive Screening' })
      .click()

    // Verify screening form is displayed
    await expect(page.getByText('Screening Assessment')).toBeVisible()
    await expect(page.getByText('Sample Question 1')).toBeVisible()
  })

  test('can complete screening and create plan', async ({ page }) => {
    // Start and complete screening
    await page
      .getByRole('button', { name: 'Start Comprehensive Screening' })
      .click()
    await page.getByRole('button', { name: 'Complete Screening' }).click()

    // Verify screening completion
    await expect(page.getByText('75')).toBeVisible() // Score
    await expect(page.getByText('HIGH')).toBeVisible() // Risk level

    // Create therapy plan
    await page.getByRole('button', { name: 'Create Therapy Plan' }).click()
    await page.getByRole('button', { name: 'Create Plan' }).click()

    // Verify plan creation
    await expect(page.getByText('1')).toBeVisible() // Goals count
    await expect(page.getByText('12 weeks')).toBeVisible() // Duration
  })

  test('can start and complete session', async ({ page }) => {
    // Complete screening and plan first
    await page
      .getByRole('button', { name: 'Start Comprehensive Screening' })
      .click()
    await page.getByRole('button', { name: 'Complete Screening' }).click()
    await page.getByRole('button', { name: 'Create Therapy Plan' }).click()
    await page.getByRole('button', { name: 'Create Plan' }).click()

    // Start session
    await page.getByRole('button', { name: 'Start' }).click()

    // Verify session interface
    await expect(page.getByText('Session 1 - John Doe')).toBeVisible()
    await expect(
      page.getByText('Exercise 1: Articulation Practice')
    ).toBeVisible()

    // Complete session
    await page.getByRole('button', { name: 'Complete Session' }).click()

    // Verify session completion
    await expect(page.getByText('1 completed')).toBeVisible()
  })

  test('handles navigation correctly', async ({ page }) => {
    // Test back navigation from screening
    await page
      .getByRole('button', { name: 'Start Comprehensive Screening' })
      .click()
    await page.getByRole('button', { name: 'Back' }).click()

    // Should be back at overview
    await expect(page.getByText('Student Information')).toBeVisible()

    // Test exit functionality
    await page.getByRole('button', { name: 'Exit SLP System' }).click()

    // In a real app, this would navigate away
    // For now, just verify the button is clickable
  })

  test('displays appropriate UI states', async ({ page }) => {
    // Initial state - no screening
    await expect(page.getByText('No screening completed yet.')).toBeVisible()

    // After screening
    await page
      .getByRole('button', { name: 'Start Comprehensive Screening' })
      .click()
    await page.getByRole('button', { name: 'Complete Screening' }).click()

    // Should show plan creation option
    await expect(page.getByText('No therapy plan created yet.')).toBeVisible()

    // After plan creation
    await page.getByRole('button', { name: 'Create Therapy Plan' }).click()
    await page.getByRole('button', { name: 'Create Plan' }).click()

    // Should show sessions
    await expect(page.getByText('Sessions (0 completed)')).toBeVisible()
  })

  test('validates required information', async ({ page }) => {
    // Test that screening is required before plan creation
    // In this simplified version, the UI should guide the user appropriately

    // Initially, no plan creation should be possible without screening
    const createPlanButton = page.getByRole('button', {
      name: 'Create Therapy Plan',
    })
    await expect(createPlanButton).not.toBeVisible()

    // After screening, plan creation should be available
    await page
      .getByRole('button', { name: 'Start Comprehensive Screening' })
      .click()
    await page.getByRole('button', { name: 'Complete Screening' }).click()

    await expect(
      page.getByRole('button', { name: 'Create Therapy Plan' })
    ).toBeVisible()
  })
})
