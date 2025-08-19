import { test, expect } from '@playwright/test'

test.describe('Golden E2E Flow: Authentication & Security', () => {
  test.beforeEach(async ({ page }) => {
    // Reset any stored authentication state
    await page.context().clearCookies()
    await page.goto('/login')
  })

  test('comprehensive multi-role authentication flow', async ({ page }) => {
    // Step 1: Student authentication
    await page.getByTestId('student-login-tab').click()
    
    await page.getByTestId('student-id').fill('emma-johnson-001')
    await page.getByTestId('student-access-code').fill('EJ2024')
    await page.getByTestId('student-login-submit').click()
    
    await expect(page).toHaveURL('/student/dashboard')
    await expect(page.getByText(/welcome back, emma/i)).toBeVisible()
    
    // Student logout
    await page.getByTestId('student-menu').click()
    await page.getByTestId('logout').click()
    
    // Step 2: Teacher authentication
    await page.getByTestId('teacher-login-tab').click()
    await page.getByTestId('email').fill('sarah.johnson@district.edu')
    await page.getByTestId('password').fill('TeacherPass456!')
    await page.getByTestId('login-submit').click()
    
    await expect(page).toHaveURL('/teacher/dashboard')
    await expect(page.getByText(/welcome, ms. johnson/i)).toBeVisible()
    
    // Teacher logout
    await page.getByTestId('user-menu').click()
    await page.getByTestId('logout').click()
    
    // Step 3: Parent authentication
    await page.getByTestId('parent-login-tab').click()
    await page.getByTestId('parent-email').fill('parent.johnson@email.com')
    await page.getByTestId('parent-password').fill('ParentPass789!')
    await page.getByTestId('parent-login-submit').click()
    
    await expect(page).toHaveURL('/parent/dashboard')
    await expect(page.getByText(/welcome, parent/i)).toBeVisible()
    
    // Parent logout
    await page.getByTestId('parent-menu').click()
    await page.getByTestId('logout').click()
    
    // Step 4: Admin authentication with 2FA
    await page.getByTestId('admin-login-tab').click()
    await page.getByTestId('admin-email').fill('admin@district.edu')
    await page.getByTestId('admin-password').fill('AdminSecure123!')
    await page.getByTestId('admin-login-submit').click()
    
    // 2FA requirement
    await expect(page.getByTestId('2fa-prompt')).toBeVisible()
    await page.getByTestId('2fa-code').fill('123456')
    await page.getByTestId('verify-2fa').click()
    
    await expect(page).toHaveURL('/admin/dashboard')
    await expect(page.getByText(/admin dashboard/i)).toBeVisible()
  })

  test('password reset and account recovery flow', async ({ page }) => {
    // Step 1: Initiate password reset
    await page.getByTestId('forgot-password').click()
    
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
    
    // Step 4: Login with new password
    await page.getByTestId('login-with-new-password').click()
    await page.getByTestId('email').fill('teacher@district.edu')
    await page.getByTestId('password').fill('NewSecurePass456!')
    await page.getByTestId('login-submit').click()
    
    await expect(page).toHaveURL('/teacher/dashboard')
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
    
    // Step 1: Landing page displays with auth CTAs
    await expect(page.getByTestId('hero-title')).toBeVisible()
    await expect(page.getByTestId('cta-primary')).toBeVisible()
    await expect(page.getByTestId('cta-secondary')).toBeVisible()
    await expect(page.getByTestId('nav-login')).toBeVisible()
    await expect(page.getByTestId('nav-register')).toBeVisible()
    
    // Step 2: Navigate to login from hero CTA
    await page.getByTestId('cta-primary').click()
    await expect(page).toHaveURL('/login')
    
    // Step 3: Complete login flow
    await page.getByTestId('email').fill('teacher@district.edu')
    await page.getByTestId('password').fill('TeacherPass456!')
    await page.getByTestId('login-submit').click()
    
    // Step 4: Verify successful authentication redirect
    await expect(page).toHaveURL('/teacher/dashboard')
    await expect(page.getByText(/welcome/i)).toBeVisible()
  })
})
