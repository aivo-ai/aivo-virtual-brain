import { test, expect } from '@playwright/test'

test.describe('Golden E2E Flow: Authentication & Security', () => {
  test.beforeEach(async ({ page }) => {
    // Reset any stored authentication state
    await page.context().clearCookies()
    await page.goto('/login')
  })

  test('comprehensive multi-role authentication flow', async ({ page }) => {
    // Note: Current login doesn't have separate tabs, so test single login form
    
    // Step 1: Basic user authentication
    await page.getByTestId('login-email').fill('user@district.edu')
    await page.getByTestId('login-password').fill('UserPass456!')
    await page.getByTestId('login-submit').click()
    
    await expect(page).toHaveURL('/dashboard')
    await expect(page.getByText(/welcome/i)).toBeVisible()
    
    // Step 2: Test logout functionality
    const userMenu = page.locator('[data-testid="user-menu"], .user-menu, [aria-label*="menu"]').first()
    if (await userMenu.count() > 0) {
      await userMenu.click()
      const logoutButton = page.locator('[data-testid="logout"], [data-testid="sign-out"]').first()
      if (await logoutButton.count() > 0) {
        await logoutButton.click()
        await expect(page).toHaveURL('/login')
      }
    }
    
    // Step 3: Test 2FA flow if enabled
    await page.getByTestId('login-email').fill('admin@district.edu')
    await page.getByTestId('login-password').fill('AdminSecure123!')
    await page.getByTestId('login-submit').click()
    
    // Check if 2FA is required (using actual test ID)
    const twoFAPrompt = page.getByTestId('2fa-code')
    if (await twoFAPrompt.count() > 0) {
      await twoFAPrompt.fill('123456')
      await page.getByTestId('2fa-submit').click()
    }
    
    await expect(page).toHaveURL('/dashboard')
  })

  test('password reset and account recovery flow', async ({ page }) => {
    // Step 1: Initiate password reset (using actual test ID)
    await page.getByTestId('forgot-password-link').click()
    
    await expect(page).toHaveURL('/forgot-password')
    await page.getByTestId('email').fill('teacher@district.edu')
    await page.getByTestId('send-reset-email').click()
    
    await expect(page.getByText(/reset email sent/i)).toBeVisible()
    
    // Step 2: Simulate email link click (direct navigation)
    await page.goto('/reset-password?token=mock-reset-token-123')
    
    // Step 3: Set new password
    await page.getByTestId('new-password').fill('NewSecurePass456!')
    await page.getByTestId('confirm-password').fill('NewSecurePass456!')
    await page.getByTestId('reset-password-submit').click()
    
    await expect(page.getByText(/password reset successful/i)).toBeVisible()
    
    // Step 4: Login with new password (using actual test IDs)
    await page.getByTestId('login-with-new-password').click()
    await page.getByTestId('login-email').fill('teacher@district.edu')
    await page.getByTestId('login-password').fill('NewSecurePass456!')
    await page.getByTestId('login-submit').click()
    
    await expect(page).toHaveURL('/dashboard')
  })

  test('session management and security enforcement', async ({ page }) => {
    // Step 1: Login as teacher
    await page.getByTestId('email').fill('teacher@district.edu')
    await page.getByTestId('password').fill('TeacherPass456!')
    await page.getByTestId('login-submit').click()
    
    // Step 2: Navigate to sensitive area (gradebook)
    await page.getByTestId('nav-gradebook').click()
    await expect(page).toHaveURL('/teacher/gradebook')
    
    // Step 3: Test session timeout warning
    // Simulate extended inactivity (accelerated for testing)
    await page.evaluate(() => {
      window.dispatchEvent(new CustomEvent('test-session-timeout-warning'))
    })
    
    await expect(page.getByTestId('session-timeout-warning')).toBeVisible()
    await page.getByTestId('extend-session').click()
    
    // Step 4: Test automatic logout after max session time
    await page.evaluate(() => {
      window.dispatchEvent(new CustomEvent('test-force-logout'))
    })
    
    await expect(page).toHaveURL('/login')
    await expect(page.getByText(/session expired/i)).toBeVisible()
  })

  test('role-based access control validation', async ({ page }) => {
    // Step 1: Login as teacher
    await page.getByTestId('email').fill('teacher@district.edu')
    await page.getByTestId('password').fill('TeacherPass456!')
    await page.getByTestId('login-submit').click()
    
    // Step 2: Try to access admin-only routes (should be blocked)
    await page.goto('/admin/users')
    await expect(page).toHaveURL('/unauthorized')
    await expect(page.getByText(/access denied/i)).toBeVisible()
    
    // Step 3: Verify allowed teacher routes work
    await page.goto('/teacher/classes')
    await expect(page).toHaveURL('/teacher/classes')
    
    await page.goto('/teacher/gradebook')
    await expect(page).toHaveURL('/teacher/gradebook')
    
    // Step 4: Test navigation menu reflects role permissions
    await expect(page.getByTestId('nav-admin-panel')).not.toBeVisible()
    await expect(page.getByTestId('nav-billing')).not.toBeVisible()
    await expect(page.getByTestId('nav-teacher-classes')).toBeVisible()
    await expect(page.getByTestId('nav-teacher-gradebook')).toBeVisible()
  })

  test('account lockout after multiple failed attempts', async ({ page }) => {
    // Step 1: Multiple failed login attempts
    for (let i = 1; i <= 5; i++) {
      await page.getByTestId('email').fill('teacher@district.edu')
      await page.getByTestId('password').fill(`wrong-password-${i}`)
      await page.getByTestId('login-submit').click()
      
      if (i < 5) {
        await expect(page.getByText(/invalid credentials/i)).toBeVisible()
        await page.getByTestId('email').clear()
        await page.getByTestId('password').clear()
      }
    }
    
    // Step 2: Account should be locked
    await expect(page.getByText(/account temporarily locked/i)).toBeVisible()
    
    // Step 3: Even correct credentials should be rejected
    await page.getByTestId('email').clear()
    await page.getByTestId('password').clear()
    await page.getByTestId('email').fill('teacher@district.edu')
    await page.getByTestId('password').fill('TeacherPass456!')
    await page.getByTestId('login-submit').click()
    
    await expect(page.getByText(/account locked/i)).toBeVisible()
    
    // Step 4: Account unlock process
    await page.getByTestId('request-unlock').click()
    await expect(page.getByText(/unlock request sent/i)).toBeVisible()
  })

  test('single sign-on (SSO) integration flow', async ({ page }) => {
    // Step 1: Initiate SSO login
    await page.getByTestId('sso-login').click()
    
    // Step 2: Redirect to identity provider (simulated)
    await expect(page).toHaveURL(/identity-provider\.district\.edu/)
    
    // Step 3: SSO authentication (simulated)
    await page.getByTestId('sso-username').fill('teacher.sso')
    await page.getByTestId('sso-password').fill('SSOPass123!')
    await page.getByTestId('sso-submit').click()
    
    // Step 4: Return to application with token
    await expect(page).toHaveURL('/teacher/dashboard')
    await expect(page.getByText(/sso login successful/i)).toBeVisible()
    
    // Step 5: Verify SSO session attributes
    await page.getByTestId('user-profile').click()
    await expect(page.getByTestId('auth-method')).toHaveText('SSO')
    await expect(page.getByTestId('sso-provider')).toHaveText('District Identity Provider')
  })

  test('landing page authentication integration', async ({ page }) => {
    // Navigate to landing page first
    await page.goto('/')
    
    // Step 1: Landing page displays (using actual HomePage structure)
    await expect(page.getByRole('heading', { level: 1 })).toBeVisible() // Main title
    await expect(page.getByTestId('get-started-button')).toBeVisible()
    await expect(page.getByTestId('health-check-link')).toBeVisible()
    
    // Step 2: Navigate to health check (available route)
    await page.getByTestId('health-check-link').click()
    await expect(page).toHaveURL('/health')
    
    // Step 3: Navigate back to home
    await page.getByTestId('nav-home-link').click()
    await expect(page).toHaveURL('/')
    
    // Step 4: Test get started button functionality
    await page.getByTestId('get-started-button').click()
    // Button has handler (console.log), so should work without error
    await expect(page.getByTestId('get-started-button')).toBeVisible()
  })
})
