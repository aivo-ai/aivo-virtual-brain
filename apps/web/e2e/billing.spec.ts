import { test, expect } from '@playwright/test'

test.describe('Golden E2E Flow: Billing & Payment Process', () => {
  test.beforeEach(async ({ page }) => {
    // Login as district admin
    await page.goto('/login')
    await page.getByTestId('admin-login-tab').click()
    await page.getByTestId('email').fill('billing.admin@district.edu')
    await page.getByTestId('password').fill('BillAdmin2024!')
    await page.getByTestId('login-submit').click()
  })

  test('district reviews usage and approves billing for new seats', async ({ page }) => {
    // Step 1: Navigate to billing dashboard
    await expect(page).toHaveURL('/admin/dashboard')
    await page.getByTestId('nav-billing').click()
    
    // Step 2: Review current usage
    await expect(page.getByTestId('current-usage-summary')).toBeVisible()
    await expect(page.getByTestId('total-active-users')).toBeVisible()
    await expect(page.getByTestId('license-utilization')).toBeVisible()
    
    // Check usage metrics
    await page.getByTestId('usage-details').click()
    await expect(page.getByTestId('student-seat-usage')).toBeVisible()
    await expect(page.getByTestId('teacher-seat-usage')).toBeVisible()
    await expect(page.getByTestId('admin-seat-usage')).toBeVisible()
    
    // Step 3: Request additional seats
    await page.getByTestId('request-additional-seats').click()
    
    // Seat requirements form
    await page.getByTestId('additional-student-seats').fill('50')
    await page.getByTestId('additional-teacher-seats').fill('5')
    await page.getByTestId('seat-request-reason').fill('Expanding to two new elementary schools in Q2')
    await page.getByTestId('expected-start-date').fill('2024-03-01')
    
    // Step 4: Review pricing
    await page.getByTestId('calculate-pricing').click()
    await expect(page.getByTestId('pricing-breakdown')).toBeVisible()
    await expect(page.getByTestId('monthly-cost-increase')).toBeVisible()
    await expect(page.getByTestId('annual-cost-projection')).toBeVisible()
    
    // Step 5: Budget approval workflow
    await page.getByTestId('submit-for-budget-approval').click()
    await page.getByTestId('budget-justification').fill('Critical for supporting new schools and maintaining student-to-license ratios per district policy')
    await page.getByTestId('superintendent-approval').check()
    await page.getByTestId('board-notification').check()
    
    await page.getByTestId('submit-budget-request').click()
    await expect(page.getByText(/budget request submitted/i)).toBeVisible()
  })

  test('finance team processes payment and updates billing', async ({ page }) => {
    // Switch to finance admin
    await page.goto('/login')
    await page.getByTestId('email').clear()
    await page.getByTestId('email').fill('finance.admin@district.edu')
    await page.getByTestId('password').clear()
    await page.getByTestId('password').fill('FinanceSecure123!')
    await page.getByTestId('login-submit').click()
    
    // Step 1: Navigate to pending billing approvals
    await page.getByTestId('nav-finance').click()
    await page.getByTestId('pending-approvals').click()
    
    // Step 2: Review seat request
    await page.getByTestId('seat-request-50-student-5-teacher').click()
    await expect(page.getByTestId('request-details')).toBeVisible()
    await expect(page.getByTestId('cost-analysis')).toBeVisible()
    
    // Step 3: Verify budget availability
    await page.getByTestId('check-budget-availability').click()
    await expect(page.getByTestId('budget-status-sufficient')).toBeVisible()
    await expect(page.getByTestId('remaining-budget')).toBeVisible()
    
    // Step 4: Process payment
    await page.getByTestId('approve-and-process-payment').click()
    
    // Payment method selection
    await page.getByTestId('payment-method').selectOption('District Credit Card')
    await page.getByTestId('payment-authorization').fill('AUTH-2024-ED-0156')
    await page.getByTestId('purchase-order-number').fill('PO-2024-TECH-089')
    
    // Step 5: Confirm payment details
    await expect(page.getByTestId('payment-summary')).toBeVisible()
    await page.getByTestId('confirm-payment').click()
    
    // Two-factor authentication
    await page.getByTestId('2fa-code').fill('123456')
    await page.getByTestId('verify-2fa').click()
    
    // Step 6: Payment processing
    await expect(page.getByText(/processing payment/i)).toBeVisible()
    await expect(page.getByText(/payment successful/i)).toBeVisible()
    
    // Step 7: Update billing records
    await page.getByTestId('update-billing-records').click()
    await expect(page.getByText(/billing records updated/i)).toBeVisible()
  })

  test('automatic license provisioning after payment confirmation', async ({ page }) => {
    // Step 1: Navigate to license management
    await page.getByTestId('nav-license-management').click()
    
    // Step 2: Verify automatic provisioning
    await expect(page.getByTestId('recent-license-updates')).toBeVisible()
    await expect(page.getByText(/50 student licenses added/i)).toBeVisible()
    await expect(page.getByText(/5 teacher licenses added/i)).toBeVisible()
    
    // Step 3: Configure license allocation
    await page.getByTestId('allocate-new-licenses').click()
    
    // School assignment
    await page.getByTestId('school-1').selectOption('Lincoln Elementary')
    await page.getByTestId('school-1-student-seats').fill('25')
    await page.getByTestId('school-1-teacher-seats').fill('3')
    
    await page.getByTestId('school-2').selectOption('Washington Elementary')
    await page.getByTestId('school-2-student-seats').fill('25')
    await page.getByTestId('school-2-teacher-seats').fill('2')
    
    // Step 4: Set license parameters
    await page.getByTestId('license-start-date').fill('2024-03-01')
    await page.getByTestId('license-end-date').fill('2025-06-30')
    await page.getByTestId('auto-renewal').check()
    
    // Step 5: Notify schools of new licenses
    await page.getByTestId('send-license-notification').click()
    await page.getByTestId('notification-message').fill('New licenses are now available for your school. Please contact IT support for activation assistance.')
    
    await page.getByTestId('send-notifications').click()
    await expect(page.getByText(/notifications sent successfully/i)).toBeVisible()
  })

  test('monthly billing reconciliation and reporting', async ({ page }) => {
    // Step 1: Generate monthly usage report
    await page.getByTestId('nav-reports').click()
    await page.getByTestId('monthly-billing-report').click()
    
    // Step 2: Select reporting period
    await page.getByTestId('report-month').selectOption('February 2024')
    await page.getByTestId('include-all-schools').check()
    
    // Step 3: Generate comprehensive report
    await page.getByTestId('generate-full-report').click()
    
    await expect(page.getByTestId('usage-by-school')).toBeVisible()
    await expect(page.getByTestId('license-utilization-rates')).toBeVisible()
    await expect(page.getByTestId('cost-per-active-user')).toBeVisible()
    
    // Step 4: Review variance from budget
    await page.getByTestId('budget-variance-analysis').click()
    await expect(page.getByTestId('projected-vs-actual')).toBeVisible()
    await expect(page.getByTestId('variance-explanation')).toBeVisible()
    
    // Step 5: Export for finance team
    await page.getByTestId('export-billing-report').click()
    await page.getByTestId('export-format').selectOption('Excel')
    await page.getByTestId('include-detailed-breakdown').check()
    await page.getByTestId('export-report').click()
    
    await expect(page.getByText(/report exported successfully/i)).toBeVisible()
  })

  test('handle payment failure and retry process', async ({ page }) => {
    // Simulate payment failure scenario
    await page.getByTestId('nav-billing').click()
    await page.getByTestId('failed-payment-alerts').click()
    
    // Step 1: Review failed payment
    await expect(page.getByTestId('payment-failure-alert')).toBeVisible()
    await page.getByTestId('view-failed-payment-details').click()
    
    await expect(page.getByText(/payment declined/i)).toBeVisible()
    await expect(page.getByTestId('failure-reason')).toBeVisible()
    
    // Step 2: Update payment method
    await page.getByTestId('update-payment-method').click()
    await page.getByTestId('new-payment-method').selectOption('Bank Transfer')
    await page.getByTestId('bank-account-number').fill('****1234')
    await page.getByTestId('routing-number').fill('021000021')
    
    // Step 3: Retry payment
    await page.getByTestId('retry-payment').click()
    await page.getByTestId('confirm-retry').click()
    
    // Step 4: Monitor payment status
    await expect(page.getByText(/payment processing/i)).toBeVisible()
    
    // Step 5: Handle service continuity during payment issues
    await page.getByTestId('grace-period-settings').click()
    await page.getByTestId('grace-period-duration').fill('7')
    await page.getByTestId('service-continuation').check()
    await page.getByTestId('save-grace-period').click()
    
    await expect(page.getByText(/grace period configured/i)).toBeVisible()
  })

  test('annual contract renewal and budget planning', async ({ page }) => {
    // Step 1: Navigate to contract management
    await page.getByTestId('nav-contracts').click()
    
    // Step 2: Review current contract status
    await expect(page.getByTestId('current-contract-details')).toBeVisible()
    await expect(page.getByTestId('contract-expiration-date')).toBeVisible()
    await expect(page.getByTestId('renewal-timeline')).toBeVisible()
    
    // Step 3: Analyze usage trends for renewal planning
    await page.getByTestId('usage-trend-analysis').click()
    await expect(page.getByTestId('12-month-usage-chart')).toBeVisible()
    await expect(page.getByTestId('growth-projections')).toBeVisible()
    
    // Step 4: Generate renewal proposal
    await page.getByTestId('generate-renewal-proposal').click()
    
    // Projected needs
    await page.getByTestId('projected-student-seats').fill('1250')
    await page.getByTestId('projected-teacher-seats').fill('125')
    await page.getByTestId('projected-admin-seats').fill('15')
    
    // Additional features
    await page.getByTestId('advanced-analytics').check()
    await page.getByTestId('priority-support').check()
    
    // Step 5: Submit for executive review
    await page.getByTestId('renewal-justification').fill('Platform has demonstrated significant positive impact on student outcomes. Recommend renewal with expanded capacity for district growth.')
    
    await page.getByTestId('submit-renewal-proposal').click()
    await expect(page.getByText(/renewal proposal submitted/i)).toBeVisible()
    
    // Step 6: Schedule renewal meeting
    await page.getByTestId('schedule-renewal-meeting').click()
    await page.getByTestId('meeting-date').fill('2024-04-15')
    await page.getByTestId('meeting-attendees').fill('Superintendent, CFO, IT Director, Curriculum Director')
    
    await page.getByTestId('send-meeting-invite').click()
    await expect(page.getByText(/meeting scheduled successfully/i)).toBeVisible()
  })
})
