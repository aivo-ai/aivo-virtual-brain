import { test, expect } from '@playwright/test'

test.describe('Parent Onboarding Wizard', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/onboarding')
  })

  test('should complete full onboarding flow', async ({ page }) => {
    // Step 1: Guardian Profile
    await expect(page.locator('h2')).toContainText('Guardian Profile')

    await page.fill('input[placeholder="Enter first name"]', 'John')
    await page.fill('input[placeholder="Enter last name"]', 'Doe')
    await page.fill(
      'input[placeholder="Enter email address"]',
      'john.doe@example.com'
    )
    await page.fill(
      'input[placeholder="Enter phone number"]',
      '+1-555-123-4567'
    )
    await page.selectOption('select[name="preferredLanguage"]', 'en')
    await page.selectOption('select[name="timezone"]', 'America/New_York')

    await page.click('button:has-text("Continue →")')

    // Step 2: Add Learner
    await expect(page.locator('h2')).toContainText('Add Your Learners')

    await page.click('button:has-text("+ Add Learner")')

    await page.fill('input[placeholder="Enter first name"]', 'Emma')
    await page.fill('input[placeholder="Enter last name"]', 'Doe')
    await page.fill('input[type="date"]', '2015-06-15') // 10 years old
    await page.fill(
      'textarea[placeholder*="special needs"]',
      'No special accommodations needed'
    )

    // Select some interests
    await page.click('button:has-text("Math")')
    await page.click('button:has-text("Science")')
    await page.click('button:has-text("Reading")')

    await page.click('button:has-text("Save Learner")')
    await page.click('button:has-text("Continue →")')

    // Step 3: Consent
    await expect(page.locator('h2')).toContainText('Privacy & Consent')

    // Accept required consents
    await page.click('input[name="dataProcessingConsent"]')
    await page.click('input[name="termsAccepted"]')

    // Optional consents
    await page.click('input[name="mediaConsent"]')
    await page.click('input[name="chatConsent"]')

    await page.click('button:has-text("Continue →")')

    // Step 4: Plan Picker
    await expect(page.locator('h2')).toContainText('Choose Your Plan')

    // Select monthly plan instead of trial
    await page.click('[data-testid="plan-monthly"]')

    await expect(page.locator('text=29.99')).toBeVisible()
    await page.click('button:has-text("Continue →")')

    // Step 5: Schedule Baseline
    await expect(page.locator('h2')).toContainText('Learning Schedule')

    // Set weekly goal
    await page.click('button:has-text("5 hours/week")')

    // Select time slots
    await page.click('button:has-text("After School")')
    await page.click('button:has-text("Evening")')

    // Select subjects
    await page.click('button:has-text("Mathematics")')
    await page.click('button:has-text("Science")')
    await page.click('button:has-text("English")')

    // Set difficulty
    await page.click('button:has-text("Intermediate")')

    await page.click('button:has-text("Continue →")')

    // Step 6: Success
    await expect(page.locator('h1')).toContainText('Welcome to AIVO!')
    await expect(page.locator('text=John Doe')).toBeVisible()
    await expect(page.locator('text=Emma Doe')).toBeVisible()
    await expect(page.locator('text=Monthly Plan')).toBeVisible()
    await expect(page.locator('text=5 hours')).toBeVisible()

    await page.click('button:has-text("🎯 Go to Dashboard")')

    // Should navigate to dashboard
    await expect(page).toHaveURL('/dashboard')
  })

  test('should validate required fields', async ({ page }) => {
    // Step 1: Try to continue without filling required fields
    await page.click('button:has-text("Continue →")')

    await expect(page.locator('text=First name is required')).toBeVisible()
    await expect(page.locator('text=Last name is required')).toBeVisible()
    await expect(page.locator('text=Email is required')).toBeVisible()
  })

  test('should calculate grade correctly from date of birth', async ({
    page,
  }) => {
    // Fill guardian profile
    await page.fill('input[placeholder="Enter first name"]', 'John')
    await page.fill('input[placeholder="Enter last name"]', 'Doe')
    await page.fill(
      'input[placeholder="Enter email address"]',
      'john.doe@example.com'
    )
    await page.click('button:has-text("Continue →")')

    // Add learner with specific DOB
    await page.click('button:has-text("+ Add Learner")')
    await page.fill('input[placeholder="Enter first name"]', 'Child')
    await page.fill('input[placeholder="Enter last name"]', 'Doe')

    // Set DOB for a 7-year-old (should be 2nd grade)
    const sevenYearOldDate = new Date()
    sevenYearOldDate.setFullYear(sevenYearOldDate.getFullYear() - 7)
    const dateString = sevenYearOldDate.toISOString().split('T')[0]

    await page.fill('input[type="date"]', dateString)
    await page.click('button:has-text("Save Learner")')

    // Verify grade calculation
    await expect(page.locator('text=Grade 2')).toBeVisible()
    await expect(page.locator('text=Early Elementary')).toBeVisible()
  })

  test('should show sibling discount for multiple learners', async ({
    page,
  }) => {
    // Fill guardian profile
    await page.fill('input[placeholder="Enter first name"]', 'John')
    await page.fill('input[placeholder="Enter last name"]', 'Doe')
    await page.fill(
      'input[placeholder="Enter email address"]',
      'john.doe@example.com'
    )
    await page.click('button:has-text("Continue →")')

    // Add first learner
    await page.click('button:has-text("+ Add Learner")')
    await page.fill('input[placeholder="Enter first name"]', 'Child1')
    await page.fill('input[placeholder="Enter last name"]', 'Doe')
    await page.fill('input[type="date"]', '2015-06-15')
    await page.click('button:has-text("Save Learner")')

    // Add second learner
    await page.click('button:has-text("+ Add Learner")')
    await page.fill('input[placeholder="Enter first name"]', 'Child2')
    await page.fill('input[placeholder="Enter last name"]', 'Doe')
    await page.fill('input[type="date"]', '2017-03-20')
    await page.click('button:has-text("Save Learner")')

    await page.click('button:has-text("Continue →")')

    // Skip consent
    await page.click('input[name="dataProcessingConsent"]')
    await page.click('input[name="termsAccepted"]')
    await page.click('button:has-text("Continue →")')

    // Check for sibling discount in plan picker
    await expect(page.locator('text=Sibling discount')).toBeVisible()
    await expect(page.locator('text=10% off')).toBeVisible()
  })

  test('should enforce minimum learner requirement', async ({ page }) => {
    // Fill guardian profile
    await page.fill('input[placeholder="Enter first name"]', 'John')
    await page.fill('input[placeholder="Enter last name"]', 'Doe')
    await page.fill(
      'input[placeholder="Enter email address"]',
      'john.doe@example.com'
    )
    await page.click('button:has-text("Continue →")')

    // Try to continue without adding any learners
    await page.click('button:has-text("Continue →")')

    // Should show alert or error message
    await expect(
      page.locator('text=Please add at least one learner')
    ).toBeVisible()
  })

  test('should support trial plan selection', async ({ page }) => {
    // Complete minimal flow to reach plan selection
    await page.fill('input[placeholder="Enter first name"]', 'John')
    await page.fill('input[placeholder="Enter last name"]', 'Doe')
    await page.fill(
      'input[placeholder="Enter email address"]',
      'john.doe@example.com'
    )
    await page.click('button:has-text("Continue →")')

    await page.click('button:has-text("+ Add Learner")')
    await page.fill('input[placeholder="Enter first name"]', 'Child')
    await page.fill('input[placeholder="Enter last name"]', 'Doe')
    await page.fill('input[type="date"]', '2015-06-15')
    await page.click('button:has-text("Save Learner")')
    await page.click('button:has-text("Continue →")')

    await page.click('input[name="dataProcessingConsent"]')
    await page.click('input[name="termsAccepted"]')
    await page.click('button:has-text("Continue →")')

    // Trial should be pre-selected
    await expect(page.locator('[data-testid="plan-trial"]')).toHaveClass(
      /selected|active/
    )
    await expect(page.locator('text=30-Day Free Trial')).toBeVisible()
    await expect(page.locator('text=Free')).toBeVisible()
  })
})
