import { test, expect } from '@playwright/test'

test.describe('Learner Profile & Private Brain Persona', () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to learner profile page
    await page.goto('/learner/profile')

    // Wait for the page to load
    await page.waitForSelector('[data-testid="learner-profile"]')
  })

  test('displays learner profile information correctly', async ({ page }) => {
    // Check that profile displays basic information
    await expect(page.locator('[data-testid="learner-name"]')).toBeVisible()
    await expect(page.locator('[data-testid="learner-grade"]')).toBeVisible()
    await expect(page.locator('[data-testid="enrollment-date"]')).toBeVisible()

    // Check grade band preview
    await expect(
      page.locator('[data-testid="grade-band-preview"]')
    ).toBeVisible()
    await expect(
      page.locator('[data-testid="current-grade-indicator"]')
    ).toBeVisible()
  })

  test('displays brain persona configuration', async ({ page }) => {
    // Check that brain persona section is visible
    await expect(
      page.locator('[data-testid="brain-persona-section"]')
    ).toBeVisible()

    // Check persona display
    await expect(page.locator('[data-testid="persona-alias"]')).toBeVisible()
    await expect(page.locator('[data-testid="persona-voice"]')).toBeVisible()
    await expect(page.locator('[data-testid="persona-tone"]')).toBeVisible()

    // Check edit button
    await expect(page.locator('[data-testid="edit-persona-btn"]')).toBeVisible()
  })

  test('allows editing brain persona alias with validation', async ({
    page,
  }) => {
    // Click edit persona button
    await page.click('[data-testid="edit-persona-btn"]')

    // Wait for edit form to appear
    await page.waitForSelector('[data-testid="persona-edit-form"]')

    // Test alias input
    const aliasInput = page.locator('[data-testid="alias-input"]')
    await expect(aliasInput).toBeVisible()

    // Test valid alias
    await aliasInput.fill('StudyBuddy')
    await expect(page.locator('[data-testid="alias-error"]')).not.toBeVisible()

    // Test profanity filter
    await aliasInput.fill('BadWord123')
    await aliasInput.blur()
    await expect(page.locator('[data-testid="alias-error"]')).toContainText(
      'inappropriate language'
    )

    // Test PII detection
    await aliasInput.fill('john.doe@email.com')
    await aliasInput.blur()
    await expect(page.locator('[data-testid="alias-error"]')).toContainText(
      'personal information'
    )

    // Test SSN detection
    await aliasInput.fill('123-45-6789')
    await aliasInput.blur()
    await expect(page.locator('[data-testid="alias-error"]')).toContainText(
      'personal information'
    )

    // Test phone number detection
    await aliasInput.fill('(555) 123-4567')
    await aliasInput.blur()
    await expect(page.locator('[data-testid="alias-error"]')).toContainText(
      'personal information'
    )
  })

  test('allows voice selection with preview', async ({ page }) => {
    // Click edit persona button
    await page.click('[data-testid="edit-persona-btn"]')
    await page.waitForSelector('[data-testid="persona-edit-form"]')

    // Check voice selection options
    const voiceOptions = page.locator('[data-testid="voice-option"]')
    await expect(voiceOptions).toHaveCount(4) // friendly, encouraging, professional, playful

    // Test voice selection
    await page.click('[data-testid="voice-option-friendly"]')
    await expect(
      page.locator('[data-testid="voice-option-friendly"]')
    ).toHaveClass(/selected/)

    // Test voice preview
    await page.click('[data-testid="voice-preview-friendly"]')
    await expect(
      page.locator('[data-testid="voice-preview-friendly"]')
    ).toContainText('Playing...')

    // Wait for preview to complete
    await page.waitForTimeout(2000)
    await expect(
      page.locator('[data-testid="voice-preview-friendly"]')
    ).toContainText('Preview')
  })

  test('allows tone selection with examples', async ({ page }) => {
    // Click edit persona button
    await page.click('[data-testid="edit-persona-btn"]')
    await page.waitForSelector('[data-testid="persona-edit-form"]')

    // Check tone selection options
    const toneOptions = page.locator('[data-testid="tone-option"]')
    await expect(toneOptions).toHaveCount(4) // formal, casual, nurturing, direct

    // Test tone selection
    await page.click('[data-testid="tone-option-casual"]')
    await expect(
      page.locator('[data-testid="tone-option-casual"]')
    ).toHaveClass(/selected/)

    // Check tone example is displayed
    await expect(
      page.locator('[data-testid="tone-example-casual"]')
    ).toBeVisible()
    await expect(
      page.locator('[data-testid="tone-example-casual"]')
    ).toContainText("let's dive into")

    // Test tone preview
    await page.click('[data-testid="tone-preview-casual"]')
    await expect(
      page.locator('[data-testid="tone-preview-casual"]')
    ).toContainText('Playing...')
  })

  test('saves persona changes successfully', async ({ page }) => {
    // Click edit persona button
    await page.click('[data-testid="edit-persona-btn"]')
    await page.waitForSelector('[data-testid="persona-edit-form"]')

    // Fill valid persona data
    await page.fill('[data-testid="alias-input"]', 'MathWizard')
    await page.click('[data-testid="voice-option-encouraging"]')
    await page.click('[data-testid="tone-option-nurturing"]')

    // Save changes
    await page.click('[data-testid="save-persona-btn"]')

    // Wait for success message
    await expect(page.locator('[data-testid="save-success"]')).toBeVisible()
    await expect(page.locator('[data-testid="save-success"]')).toContainText(
      'Persona updated successfully'
    )

    // Verify changes are reflected in display
    await expect(page.locator('[data-testid="persona-alias"]')).toContainText(
      'MathWizard'
    )
    await expect(page.locator('[data-testid="persona-voice"]')).toContainText(
      'encouraging'
    )
    await expect(page.locator('[data-testid="persona-tone"]')).toContainText(
      'nurturing'
    )
  })

  test('displays teacher assignments correctly', async ({ page }) => {
    // Check teacher assignments section
    await expect(
      page.locator('[data-testid="teacher-assignments"]')
    ).toBeVisible()

    // Check for teacher cards
    const teacherCards = page.locator('[data-testid="teacher-card"]')
    await expect(teacherCards.first()).toBeVisible()

    // Check teacher information display
    await expect(
      page.locator('[data-testid="teacher-name"]').first()
    ).toBeVisible()
    await expect(
      page.locator('[data-testid="teacher-subject"]').first()
    ).toBeVisible()
    await expect(
      page.locator('[data-testid="teacher-email"]').first()
    ).toBeVisible()
    await expect(
      page.locator('[data-testid="assignment-date"]').first()
    ).toBeVisible()
  })

  test('allows managing teacher assignments', async ({ page }) => {
    // Click manage teachers button
    await page.click('[data-testid="manage-teachers-btn"]')
    await page.waitForSelector('[data-testid="teacher-management-modal"]')

    // Check available teachers list
    await expect(
      page.locator('[data-testid="available-teachers"]')
    ).toBeVisible()

    // Test adding a teacher
    const addTeacherBtn = page
      .locator('[data-testid="add-teacher-btn"]')
      .first()
    await addTeacherBtn.click()
    await expect(page.locator('[data-testid="add-success"]')).toBeVisible()

    // Test removing a teacher
    const removeTeacherBtn = page
      .locator('[data-testid="remove-teacher-btn"]')
      .first()
    await removeTeacherBtn.click()
    await expect(page.locator('[data-testid="confirm-removal"]')).toBeVisible()
    await page.click('[data-testid="confirm-remove"]')
    await expect(page.locator('[data-testid="remove-success"]')).toBeVisible()
  })

  test('displays accessibility preferences', async ({ page }) => {
    // Navigate to preferences tab
    await page.click('[data-testid="preferences-tab"]')

    // Check accessibility options
    await expect(
      page.locator('[data-testid="accessibility-section"]')
    ).toBeVisible()
    await expect(page.locator('[data-testid="font-size-option"]')).toBeVisible()
    await expect(
      page.locator('[data-testid="high-contrast-toggle"]')
    ).toBeVisible()
    await expect(
      page.locator('[data-testid="screen-reader-toggle"]')
    ).toBeVisible()
    await expect(
      page.locator('[data-testid="reduced-motion-toggle"]')
    ).toBeVisible()
  })

  test('allows updating accessibility preferences', async ({ page }) => {
    // Navigate to preferences tab
    await page.click('[data-testid="preferences-tab"]')

    // Test font size adjustment
    await page.selectOption('[data-testid="font-size-select"]', 'large')
    await expect(page.locator('[data-testid="font-size-select"]')).toHaveValue(
      'large'
    )

    // Test high contrast toggle
    await page.click('[data-testid="high-contrast-toggle"]')
    await expect(
      page.locator('[data-testid="high-contrast-toggle"]')
    ).toBeChecked()

    // Test screen reader support
    await page.click('[data-testid="screen-reader-toggle"]')
    await expect(
      page.locator('[data-testid="screen-reader-toggle"]')
    ).toBeChecked()

    // Save preferences
    await page.click('[data-testid="save-preferences-btn"]')
    await expect(
      page.locator('[data-testid="preferences-saved"]')
    ).toBeVisible()
  })

  test('displays notification settings', async ({ page }) => {
    // Navigate to preferences tab
    await page.click('[data-testid="preferences-tab"]')

    // Check notification settings
    await expect(
      page.locator('[data-testid="notification-section"]')
    ).toBeVisible()
    await expect(
      page.locator('[data-testid="email-notifications-toggle"]')
    ).toBeVisible()
    await expect(
      page.locator('[data-testid="push-notifications-toggle"]')
    ).toBeVisible()
    await expect(
      page.locator('[data-testid="assignment-reminders-toggle"]')
    ).toBeVisible()
    await expect(
      page.locator('[data-testid="progress-updates-toggle"]')
    ).toBeVisible()
  })

  test('handles guardian/teacher view restrictions', async ({ page }) => {
    // Test as guardian role
    await page
      .context()
      .addCookies([
        { name: 'user_role', value: 'guardian', url: 'http://localhost:3000' },
      ])
    await page.reload()

    // Guardian should see limited edit options
    await expect(page.locator('[data-testid="edit-persona-btn"]')).toBeVisible()
    await expect(
      page.locator('[data-testid="manage-teachers-btn"]')
    ).not.toBeVisible()

    // Test as teacher role
    await page
      .context()
      .addCookies([
        { name: 'user_role', value: 'teacher', url: 'http://localhost:3000' },
      ])
    await page.reload()

    // Teacher should see all management options
    await expect(page.locator('[data-testid="edit-persona-btn"]')).toBeVisible()
    await expect(
      page.locator('[data-testid="manage-teachers-btn"]')
    ).toBeVisible()
  })

  test('handles grade band preview navigation', async ({ page }) => {
    // Check grade band preview controls
    await expect(
      page.locator('[data-testid="grade-band-preview"]')
    ).toBeVisible()

    // Test navigation between grade levels
    const prevButton = page.locator('[data-testid="prev-grade-btn"]')
    const nextButton = page.locator('[data-testid="next-grade-btn"]')

    // Navigate to next grade
    if (await nextButton.isVisible()) {
      await nextButton.click()
      await expect(
        page.locator('[data-testid="preview-grade-level"]')
      ).not.toContainText('Current')
    }

    // Navigate to previous grade
    if (await prevButton.isVisible()) {
      await prevButton.click()
      await expect(
        page.locator('[data-testid="preview-grade-level"]')
      ).toBeVisible()
    }

    // Return to current grade
    await page.click('[data-testid="current-grade-btn"]')
    await expect(
      page.locator('[data-testid="current-grade-indicator"]')
    ).toBeVisible()
  })

  test('validates persona alias character limits', async ({ page }) => {
    // Click edit persona button
    await page.click('[data-testid="edit-persona-btn"]')
    await page.waitForSelector('[data-testid="persona-edit-form"]')

    const aliasInput = page.locator('[data-testid="alias-input"]')

    // Test minimum length
    await aliasInput.fill('a')
    await aliasInput.blur()
    await expect(page.locator('[data-testid="alias-error"]')).toContainText(
      'at least 2 characters'
    )

    // Test maximum length
    await aliasInput.fill('a'.repeat(51))
    await aliasInput.blur()
    await expect(page.locator('[data-testid="alias-error"]')).toContainText(
      'maximum 50 characters'
    )

    // Test valid length
    await aliasInput.fill('ValidAlias')
    await aliasInput.blur()
    await expect(page.locator('[data-testid="alias-error"]')).not.toBeVisible()
  })

  test('handles network errors gracefully', async ({ page }) => {
    // Simulate network failure
    await page.route('**/api/learner/**', route => route.abort())

    // Try to edit persona
    await page.click('[data-testid="edit-persona-btn"]')

    // Should show error message
    await expect(page.locator('[data-testid="network-error"]')).toBeVisible()
    await expect(page.locator('[data-testid="network-error"]')).toContainText(
      'Unable to load'
    )

    // Should have retry button
    await expect(page.locator('[data-testid="retry-btn"]')).toBeVisible()
  })

  test('maintains persona privacy (no alias logging)', async ({ page }) => {
    // Enable console monitoring
    const consoleLogs: string[] = []
    page.on('console', msg => {
      if (msg.type() === 'log' || msg.type() === 'error') {
        consoleLogs.push(msg.text())
      }
    })

    // Click edit persona button
    await page.click('[data-testid="edit-persona-btn"]')
    await page.waitForSelector('[data-testid="persona-edit-form"]')

    // Fill alias with sensitive test data
    await page.fill('[data-testid="alias-input"]', 'PrivateAlias123')

    // Trigger save
    await page.click('[data-testid="save-persona-btn"]')

    // Wait for potential logging
    await page.waitForTimeout(1000)

    // Verify alias is not logged
    const hasAliasInLogs = consoleLogs.some(log =>
      log.includes('PrivateAlias123')
    )
    expect(hasAliasInLogs).toBeFalsy()
  })
})
