import { test, expect } from '@playwright/test'

test.describe('Authentication Flow E2E', () => {
  test.beforeEach(async ({ page }) => {
    // Reset any stored authentication state
    await page.context().clearCookies()
    await page.goto('/')
  })

  test.describe('Landing Page', () => {
    test('displays landing page with auth CTAs', async ({ page }) => {
      await expect(page.getByTestId('hero-title')).toBeVisible()
      await expect(page.getByTestId('cta-primary')).toBeVisible()
      await expect(page.getByTestId('cta-secondary')).toBeVisible()
      await expect(page.getByTestId('nav-login')).toBeVisible()
      await expect(page.getByTestId('nav-register')).toBeVisible()
    })

    test('navigates to login from hero CTA', async ({ page }) => {
      await page.getByTestId('cta-primary').click()
      await expect(page).toHaveURL('/login')
    })

    test('navigates to register from hero CTA', async ({ page }) => {
      await page.getByTestId('cta-secondary').click()
      await expect(page).toHaveURL('/register')
    })

    test('navigates to login from nav', async ({ page }) => {
      await page.getByTestId('nav-login').click()
      await expect(page).toHaveURL('/login')
    })

    test('navigates to register from nav', async ({ page }) => {
      await page.getByTestId('nav-register').click()
      await expect(page).toHaveURL('/register')
    })
  })

  test.describe('Registration Flow', () => {
    test('completes full registration process', async ({ page }) => {
      await page.goto('/register')

      // Fill out registration form
      await page.getByTestId('first-name').fill('John')
      await page.getByTestId('last-name').fill('Doe')
      await page.getByTestId('register-email').fill('john.doe@example.com')
      await page.getByTestId('register-password').fill('SecurePassword123!')
      await page.getByTestId('confirm-password').fill('SecurePassword123!')
      await page.getByTestId('terms-checkbox').check()

      // Submit form
      await page.getByTestId('register-submit').click()

      // Should either redirect to dashboard or show verification message
      await expect(page).toHaveURL(/\/(dashboard|login)/)
    })

    test('validates required fields', async ({ page }) => {
      await page.goto('/register')
      await page.getByTestId('register-submit').click()

      // Check for validation errors
      await expect(page.getByText('First name is required')).toBeVisible()
      await expect(page.getByText('Last name is required')).toBeVisible()
      await expect(page.getByText('Email is required')).toBeVisible()
      await expect(
        page.getByText('Password must be at least 8 characters')
      ).toBeVisible()
      await expect(
        page.getByText('You must accept the terms and conditions')
      ).toBeVisible()
    })

    test('validates password confirmation mismatch', async ({ page }) => {
      await page.goto('/register')

      await page.getByTestId('register-password').fill('Password123!')
      await page.getByTestId('confirm-password').fill('DifferentPassword!')
      await page.getByTestId('register-submit').click()

      await expect(page.getByText('Passwords do not match')).toBeVisible()
    })

    test('validates email format', async ({ page }) => {
      await page.goto('/register')

      await page.getByTestId('register-email').fill('invalid-email')
      await page.getByTestId('register-submit').click()

      await expect(
        page.getByText('Please enter a valid email address')
      ).toBeVisible()
    })

    test('shows password strength indicator', async ({ page }) => {
      await page.goto('/register')

      const passwordField = page.getByTestId('register-password')
      await passwordField.click()

      // Type a weak password
      await passwordField.fill('123')
      await expect(page.getByText('Password strength:')).toBeVisible()
      await expect(page.locator('[data-testid="strength-bar"]')).toHaveClass(
        /bg-red/
      )

      // Type a stronger password
      await passwordField.fill('SecurePassword123!')
      await expect(page.locator('[data-testid="strength-bar"]')).toHaveClass(
        /bg-green/
      )
    })

    test('toggles password visibility', async ({ page }) => {
      await page.goto('/register')

      const passwordField = page.getByTestId('register-password')
      const toggleButton = passwordField
        .locator('..')
        .getByRole('button', { name: /show password/i })

      await passwordField.fill('password123')

      // Initially should be password type
      await expect(passwordField).toHaveAttribute('type', 'password')

      // Click toggle to show
      await toggleButton.click()
      await expect(passwordField).toHaveAttribute('type', 'text')

      // Click toggle to hide
      await toggleButton.click()
      await expect(passwordField).toHaveAttribute('type', 'password')
    })

    test('navigates to login page from register link', async ({ page }) => {
      await page.goto('/register')
      await page.getByTestId('login-link').click()
      await expect(page).toHaveURL('/login')
    })

    test('links to terms and privacy open in new tab', async ({ page }) => {
      await page.goto('/register')

      // Check terms link opens in new tab
      const [termsPage] = await Promise.all([
        page.waitForEvent('popup'),
        page.getByTestId('terms-link').click(),
      ])
      await expect(termsPage).toHaveURL('/terms')

      // Check privacy link opens in new tab
      const [privacyPage] = await Promise.all([
        page.waitForEvent('popup'),
        page.getByTestId('privacy-link').click(),
      ])
      await expect(privacyPage).toHaveURL('/privacy')
    })
  })

  test.describe('Login Flow', () => {
    test('completes basic login process', async ({ page }) => {
      await page.goto('/login')

      await page.getByTestId('login-email').fill('test@example.com')
      await page.getByTestId('login-password').fill('password123')
      await page.getByTestId('login-submit').click()

      // Should redirect to dashboard on successful login
      await expect(page).toHaveURL('/dashboard')
    })

    test('validates required fields', async ({ page }) => {
      await page.goto('/login')
      await page.getByTestId('login-submit').click()

      await expect(page.getByText('Email is required')).toBeVisible()
      await expect(page.getByText('Password is required')).toBeVisible()
    })

    test('handles 2FA flow', async ({ page }) => {
      await page.goto('/login')

      // Mock a user that requires 2FA
      await page.getByTestId('login-email').fill('2fa-user@example.com')
      await page.getByTestId('login-password').fill('password123')
      await page.getByTestId('login-submit').click()

      // Should show 2FA input
      await expect(page.getByTestId('2fa-code')).toBeVisible()
      await expect(page.getByTestId('2fa-submit')).toBeVisible()
      await expect(page.getByTestId('back-to-login')).toBeVisible()

      // Fill 2FA code
      const codeInputs = page.getByTestId('2fa-code').locator('input')
      await codeInputs.nth(0).fill('1')
      await codeInputs.nth(1).fill('2')
      await codeInputs.nth(2).fill('3')
      await codeInputs.nth(3).fill('4')
      await codeInputs.nth(4).fill('5')
      await codeInputs.nth(5).fill('6')

      await page.getByTestId('2fa-submit').click()

      // Should redirect to dashboard
      await expect(page).toHaveURL('/dashboard')
    })

    test('navigates to register page from login link', async ({ page }) => {
      await page.goto('/login')
      await page.getByTestId('register-link').click()
      await expect(page).toHaveURL('/register')
    })

    test('navigates to reset password', async ({ page }) => {
      await page.goto('/login')
      await page.getByTestId('forgot-password-link').click()
      await expect(page).toHaveURL('/reset-password')
    })

    test('remembers user selection', async ({ page }) => {
      await page.goto('/login')

      const rememberCheckbox = page.getByTestId('remember-me')
      await expect(rememberCheckbox).not.toBeChecked()

      await rememberCheckbox.check()
      await expect(rememberCheckbox).toBeChecked()
    })

    test('2FA keyboard navigation works', async ({ page }) => {
      await page.goto('/login')

      // Mock 2FA flow
      await page.getByTestId('login-email').fill('2fa-user@example.com')
      await page.getByTestId('login-password').fill('password123')
      await page.getByTestId('login-submit').click()

      await expect(page.getByTestId('2fa-code')).toBeVisible()

      const codeInputs = page.getByTestId('2fa-code').locator('input')

      // Type in first input, should focus next
      await codeInputs.nth(0).fill('1')
      await expect(codeInputs.nth(1)).toBeFocused()

      // Use arrow keys to navigate
      await page.keyboard.press('ArrowLeft')
      await expect(codeInputs.nth(0)).toBeFocused()

      await page.keyboard.press('ArrowRight')
      await expect(codeInputs.nth(1)).toBeFocused()
    })

    test('2FA paste functionality works', async ({ page }) => {
      await page.goto('/login')

      // Mock 2FA flow
      await page.getByTestId('login-email').fill('2fa-user@example.com')
      await page.getByTestId('login-password').fill('password123')
      await page.getByTestId('login-submit').click()

      await expect(page.getByTestId('2fa-code')).toBeVisible()

      // Focus first input and paste
      const firstInput = page.getByTestId('2fa-code').locator('input').nth(0)
      await firstInput.click()

      // Simulate paste operation
      await page.evaluate(() => {
        // Mock clipboard API
        Object.assign(navigator, {
          clipboard: {
            readText: () => Promise.resolve('123456'),
          },
        })
      })

      await page.keyboard.press('Control+v')

      // Check that all inputs are filled
      const codeInputs = page.getByTestId('2fa-code').locator('input')
      await expect(codeInputs.nth(0)).toHaveValue('1')
      await expect(codeInputs.nth(1)).toHaveValue('2')
      await expect(codeInputs.nth(2)).toHaveValue('3')
      await expect(codeInputs.nth(3)).toHaveValue('4')
      await expect(codeInputs.nth(4)).toHaveValue('5')
      await expect(codeInputs.nth(5)).toHaveValue('6')
    })
  })

  test.describe('Password Reset Flow', () => {
    test('requests password reset', async ({ page }) => {
      await page.goto('/reset-password')

      await page.getByTestId('reset-email').fill('test@example.com')
      await page.getByTestId('send-reset-email').click()

      // Should show success message
      await expect(page.getByText(/reset email sent/i)).toBeVisible()
      await expect(page.getByTestId('back-to-login')).toBeVisible()
    })

    test('validates email field', async ({ page }) => {
      await page.goto('/reset-password')

      await page.getByTestId('send-reset-email').click()
      await expect(page.getByText('Email is required')).toBeVisible()

      await page.getByTestId('reset-email').fill('invalid-email')
      await page.getByTestId('send-reset-email').click()
      await expect(
        page.getByText('Please enter a valid email address')
      ).toBeVisible()
    })

    test('resets password with token', async ({ page }) => {
      // Navigate to reset page with token
      await page.goto('/reset-password?token=valid-reset-token')

      // Should show password reset form
      await expect(page.getByTestId('new-password')).toBeVisible()
      await expect(page.getByTestId('confirm-new-password')).toBeVisible()
      await expect(page.getByTestId('reset-password-submit')).toBeVisible()

      await page.getByTestId('new-password').fill('NewPassword123!')
      await page.getByTestId('confirm-new-password').fill('NewPassword123!')
      await page.getByTestId('reset-password-submit').click()

      // Should show success and redirect to login
      await expect(page.getByText(/password updated/i)).toBeVisible()
    })

    test('validates password confirmation in reset', async ({ page }) => {
      await page.goto('/reset-password?token=valid-reset-token')

      await page.getByTestId('new-password').fill('Password123!')
      await page.getByTestId('confirm-new-password').fill('DifferentPassword!')
      await page.getByTestId('reset-password-submit').click()

      await expect(page.getByText('Passwords do not match')).toBeVisible()
    })

    test('navigates back to login', async ({ page }) => {
      await page.goto('/reset-password')
      await page.getByTestId('back-to-login-link').click()
      await expect(page).toHaveURL('/login')
    })
  })

  test.describe('2FA Setup Flow', () => {
    test('completes 2FA setup process', async ({ page }) => {
      // Navigate to 2FA setup (requires authentication)
      await page.goto('/login')
      await page.getByTestId('login-email').fill('test@example.com')
      await page.getByTestId('login-password').fill('password123')
      await page.getByTestId('login-submit').click()

      await page.goto('/2fa-setup')

      // Should show QR code and instructions
      await expect(page.getByTestId('qr-code')).toBeVisible()
      await expect(page.getByTestId('copy-secret')).toBeVisible()
      await expect(page.getByTestId('continue-setup')).toBeVisible()
      await expect(page.getByTestId('skip-setup')).toBeVisible()

      // Continue to verification
      await page.getByTestId('continue-setup').click()

      // Should show verification code input
      await expect(page.getByTestId('verification-code')).toBeVisible()
      await expect(page.getByTestId('verify-code')).toBeVisible()
      await expect(page.getByTestId('back-to-setup')).toBeVisible()

      // Enter verification code
      const codeInputs = page.getByTestId('verification-code').locator('input')
      await codeInputs.nth(0).fill('1')
      await codeInputs.nth(1).fill('2')
      await codeInputs.nth(2).fill('3')
      await codeInputs.nth(3).fill('4')
      await codeInputs.nth(4).fill('5')
      await codeInputs.nth(5).fill('6')

      await page.getByTestId('verify-code').click()

      // Should show backup codes
      await expect(page.getByText('Your Backup Codes')).toBeVisible()
      await expect(page.getByTestId('backup-code-0')).toBeVisible()
      await expect(page.getByTestId('copy-codes')).toBeVisible()
      await expect(page.getByTestId('download-codes')).toBeVisible()
      await expect(page.getByTestId('complete-setup')).toBeVisible()

      // Complete setup
      await page.getByTestId('complete-setup').click()

      // Should show success and redirect
      await expect(page.getByText(/2FA setup complete/i)).toBeVisible()
    })

    test('copies secret key', async ({ page }) => {
      await page.goto('/login')
      await page.getByTestId('login-email').fill('test@example.com')
      await page.getByTestId('login-password').fill('password123')
      await page.getByTestId('login-submit').click()

      await page.goto('/2fa-setup')

      // Mock clipboard API
      await page.evaluate(() => {
        Object.assign(navigator, {
          clipboard: {
            writeText: () => Promise.resolve(),
          },
        })
      })

      await page.getByTestId('copy-secret').click()
      // In a real test, you'd verify the clipboard content
    })

    test('downloads backup codes', async ({ page }) => {
      await page.goto('/login')
      await page.getByTestId('login-email').fill('test@example.com')
      await page.getByTestId('login-password').fill('password123')
      await page.getByTestId('login-submit').click()

      await page.goto('/2fa-setup')
      await page.getByTestId('continue-setup').click()

      // Enter verification code to get to backup codes
      const codeInputs = page.getByTestId('verification-code').locator('input')
      for (let i = 0; i < 6; i++) {
        await codeInputs.nth(i).fill((i + 1).toString())
      }
      await page.getByTestId('verify-code').click()

      // Set up download listener
      const downloadPromise = page.waitForEvent('download')
      await page.getByTestId('download-codes').click()
      const download = await downloadPromise

      expect(download.suggestedFilename()).toBe('aivo-backup-codes.txt')
    })

    test('skips 2FA setup', async ({ page }) => {
      await page.goto('/login')
      await page.getByTestId('login-email').fill('test@example.com')
      await page.getByTestId('login-password').fill('password123')
      await page.getByTestId('login-submit').click()

      await page.goto('/2fa-setup')

      await page.getByTestId('skip-setup').click()
      await expect(page).toHaveURL('/dashboard')
    })

    test('navigates back from verification to setup', async ({ page }) => {
      await page.goto('/login')
      await page.getByTestId('login-email').fill('test@example.com')
      await page.getByTestId('login-password').fill('password123')
      await page.getByTestId('login-submit').click()

      await page.goto('/2fa-setup')
      await page.getByTestId('continue-setup').click()
      await page.getByTestId('back-to-setup').click()

      await expect(page.getByTestId('qr-code')).toBeVisible()
      await expect(page.getByTestId('continue-setup')).toBeVisible()
    })
  })

  test.describe('Accessibility', () => {
    test('login form is accessible', async ({ page }) => {
      await page.goto('/login')

      // Check for proper form labels
      await expect(page.getByLabelText(/email/i)).toBeVisible()
      await expect(page.getByLabelText(/password/i)).toBeVisible()

      // Check for proper roles
      await expect(page.getByRole('button', { name: /sign in/i })).toBeVisible()
      await expect(
        page.getByRole('checkbox', { name: /remember me/i })
      ).toBeVisible()

      // Check skip link
      await expect(page.locator('.skip-link')).toBeHidden()
      await page.keyboard.press('Tab')
      await expect(page.locator('.skip-link')).toBeVisible()
    })

    test('register form is accessible', async ({ page }) => {
      await page.goto('/register')

      // Check for proper form labels
      await expect(page.getByLabelText(/first name/i)).toBeVisible()
      await expect(page.getByLabelText(/last name/i)).toBeVisible()
      await expect(page.getByLabelText(/email/i)).toBeVisible()
      await expect(page.getByLabelText(/^password/i)).toBeVisible()
      await expect(page.getByLabelText(/confirm password/i)).toBeVisible()

      // Check required field indicators
      await expect(page.locator('text=*')).toHaveCount(6) // All required fields marked with *
    })

    test('2FA code input is accessible', async ({ page }) => {
      await page.goto('/login')
      await page.getByTestId('login-email').fill('2fa-user@example.com')
      await page.getByTestId('login-password').fill('password123')
      await page.getByTestId('login-submit').click()

      await expect(page.getByTestId('2fa-code')).toBeVisible()

      // Check that inputs have proper labels
      const codeInputs = page.getByTestId('2fa-code').locator('input')
      for (let i = 0; i < 6; i++) {
        await expect(codeInputs.nth(i)).toHaveAttribute(
          'aria-label',
          `Digit ${i + 1}`
        )
      }
    })

    test('keyboard navigation works throughout forms', async ({ page }) => {
      await page.goto('/register')

      // Tab through all form elements
      await page.keyboard.press('Tab') // First name
      await expect(page.getByTestId('first-name')).toBeFocused()

      await page.keyboard.press('Tab') // Last name
      await expect(page.getByTestId('last-name')).toBeFocused()

      await page.keyboard.press('Tab') // Email
      await expect(page.getByTestId('register-email')).toBeFocused()

      await page.keyboard.press('Tab') // Password
      await expect(page.getByTestId('register-password')).toBeFocused()

      await page.keyboard.press('Tab') // Show password button
      await page.keyboard.press('Tab') // Confirm password
      await expect(page.getByTestId('confirm-password')).toBeFocused()

      await page.keyboard.press('Tab') // Show password button
      await page.keyboard.press('Tab') // Terms checkbox
      await expect(page.getByTestId('terms-checkbox')).toBeFocused()

      await page.keyboard.press('Tab') // Submit button
      await expect(page.getByTestId('register-submit')).toBeFocused()
    })
  })

  test.describe('Error Handling', () => {
    test('displays network error gracefully', async ({ page }) => {
      // Mock network failure
      await page.route('**/api/auth/**', route => route.abort('failed'))

      await page.goto('/login')
      await page.getByTestId('login-email').fill('test@example.com')
      await page.getByTestId('login-password').fill('password123')
      await page.getByTestId('login-submit').click()

      await expect(page.getByText(/network error/i)).toBeVisible()
    })

    test('displays validation errors correctly', async ({ page }) => {
      await page.goto('/register')

      // Fill invalid data
      await page.getByTestId('register-email').fill('invalid-email')
      await page.getByTestId('register-password').fill('weak')
      await page.getByTestId('confirm-password').fill('different')
      await page.getByTestId('register-submit').click()

      // Check error styling
      await expect(page.getByTestId('register-email')).toHaveClass(/border-red/)
      await expect(page.getByTestId('register-password')).toHaveClass(
        /border-red/
      )
      await expect(page.getByTestId('confirm-password')).toHaveClass(
        /border-red/
      )

      // Check error messages have proper role
      await expect(page.getByRole('alert')).toHaveCount(5) // Multiple validation errors
    })
  })

  test.describe('Responsive Design', () => {
    test('forms work on mobile viewport', async ({ page }) => {
      await page.setViewportSize({ width: 375, height: 667 })
      await page.goto('/register')

      // Check that form is still usable
      await expect(page.getByTestId('first-name')).toBeVisible()
      await expect(page.getByTestId('register-submit')).toBeVisible()

      // Check that name fields stack on mobile
      const firstNameBox = await page.getByTestId('first-name').boundingBox()
      const lastNameBox = await page.getByTestId('last-name').boundingBox()

      // On mobile, first name should be above last name
      expect(firstNameBox?.y).toBeLessThan(lastNameBox?.y || 0)
    })

    test('social login buttons work on mobile', async ({ page }) => {
      await page.setViewportSize({ width: 375, height: 667 })
      await page.goto('/login')

      await expect(page.getByTestId('google-login')).toBeVisible()
      await expect(page.getByTestId('apple-login')).toBeVisible()

      // Buttons should be side by side even on mobile
      const googleBox = await page.getByTestId('google-login').boundingBox()
      const appleBox = await page.getByTestId('apple-login').boundingBox()

      expect(Math.abs((googleBox?.y || 0) - (appleBox?.y || 0))).toBeLessThan(
        10
      )
    })
  })
})
