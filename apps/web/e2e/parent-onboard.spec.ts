import { test, expect } from '@playwright/test'

test.describe('Golden E2E Flow: Parent Onboarding Journey', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/')
  })

  test('complete parent onboarding flow', async ({ page }) => {
    // Step 1: Landing page interaction (using actual elements)
    await expect(page.getByRole('heading', { name: /smarter ieps/i })).toBeVisible()
    await page.getByTestId('hero-cta-register').click()

    // Step 2: Registration
    await expect(page).toHaveURL('/register')
    await page.getByTestId('register-email').fill('parent@example.com')
    await page.getByTestId('register-password').fill('SecurePass123!')
    await page.getByTestId('register-confirm-password').fill('SecurePass123!')
    await page.getByTestId('register-terms').check()
    await page.getByTestId('register-submit').click()

    // Step 3: Email verification (mock)
    await expect(page.getByText(/check your email/i)).toBeVisible()
    // Simulate clicking verification link
    await page.goto('/onboarding?verified=true')

    // Step 4: Role selection
    await expect(page.getByText(/tell us about yourself/i)).toBeVisible()
    await page.getByTestId('role-parent').click()
    await page.getByTestId('continue-button').click()

    // Step 5: Profile setup
    await expect(page).toHaveURL('/onboarding/profile')
    await page.getByTestId('parent-name').fill('Jane Smith')
    await page.getByTestId('parent-phone').fill('(555) 123-4567')
    
    // Add child information
    await page.getByTestId('add-child-button').click()
    await page.getByTestId('child-name-0').fill('Alex Smith')
    await page.getByTestId('child-grade-0').selectOption('3rd Grade')
    await page.getByTestId('child-needs-0').fill('ADHD, reading support')
    
    await page.getByTestId('save-profile').click()

    // Step 6: Consent and privacy
    await expect(page.getByText(/privacy settings/i)).toBeVisible()
    await page.getByTestId('data-consent').check()
    await page.getByTestId('communication-consent').check()
    await page.getByTestId('save-consent').click()

    // Step 7: Onboarding complete
    await expect(page).toHaveURL('/onboarding/complete')
    await expect(page.getByText(/welcome to aivo/i)).toBeVisible()
    await page.getByTestId('go-to-dashboard').click()

    // Step 8: Verify dashboard access
    await expect(page).toHaveURL('/dashboard')
    await expect(page.getByTestId('parent-dashboard')).toBeVisible()
    await expect(page.getByText('Alex Smith')).toBeVisible()
  })

  test('parent can navigate child progress', async ({ page }) => {
    // Assume logged in as parent
    await page.goto('/dashboard')
    await page.getByTestId('child-progress-card').first().click()

    await expect(page).toHaveURL(/\/learners\/[^/]+\/progress/)
    await expect(page.getByTestId('progress-overview')).toBeVisible()
    await expect(page.getByTestId('learning-goals')).toBeVisible()
    await expect(page.getByTestId('recent-activities')).toBeVisible()
  })

  test('parent can view IEP information', async ({ page }) => {
    // Navigate to child detail
    await page.goto('/dashboard')
    await page.getByTestId('child-card').first().click()

    // View IEP section
    await page.getByTestId('iep-tab').click()
    await expect(page.getByTestId('iep-overview')).toBeVisible()
    await expect(page.getByTestId('iep-goals')).toBeVisible()
    await expect(page.getByTestId('iep-accommodations')).toBeVisible()
  })
})
