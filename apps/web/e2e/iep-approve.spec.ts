import { test, expect } from '@playwright/test'

test.describe('Golden E2E Flow: IEP Approval Process', () => {
  test.beforeEach(async ({ page }) => {
    // Login as IEP coordinator
    await page.goto('/login')
    await page.getByTestId('staff-login-tab').click()
    await page.getByTestId('email').fill('iep.coordinator@district.edu')
    await page.getByTestId('password').fill('SecurePass123!')
    await page.getByTestId('login-submit').click()
  })

  test('complete IEP creation, review, and approval workflow', async ({ page }) => {
    // Step 1: Navigate to IEP management
    await expect(page).toHaveURL('/staff/dashboard')
    await page.getByTestId('nav-iep-management').click()
    
    // Step 2: Create new IEP
    await page.getByTestId('create-new-iep').click()
    
    // Student selection
    await page.getByTestId('student-search').fill('Marcus Thompson')
    await page.getByTestId('student-marcus-thompson').click()
    await page.getByTestId('confirm-student').click()
    
    // Step 3: IEP Details - Basic Information
    await page.getByTestId('iep-type').selectOption('Annual Review')
    await page.getByTestId('grade-level').selectOption('5')
    await page.getByTestId('disability-category').selectOption('Specific Learning Disability')
    
    // Step 4: Goals and Objectives
    await page.getByTestId('add-academic-goal').click()
    await page.getByTestId('goal-area').selectOption('Reading Comprehension')
    await page.getByTestId('goal-description').fill('Student will improve reading comprehension by identifying main ideas and supporting details in grade-level texts')
    await page.getByTestId('goal-measurable-criteria').fill('80% accuracy on weekly assessments')
    await page.getByTestId('goal-timeline').fill('By end of academic year')
    await page.getByTestId('save-goal').click()
    
    // Add behavioral goal
    await page.getByTestId('add-behavioral-goal').click()
    await page.getByTestId('behavior-goal-description').fill('Student will demonstrate improved focus during instruction')
    await page.getByTestId('behavior-intervention').fill('Provide movement breaks every 20 minutes')
    await page.getByTestId('save-behavioral-goal').click()
    
    // Step 5: Accommodations and Modifications
    await page.getByTestId('accommodations-section').click()
    await page.getByTestId('extended-time').check()
    await page.getByTestId('preferred-seating').check()
    await page.getByTestId('assistive-technology').check()
    
    await page.getByTestId('custom-accommodation').fill('Audio recordings of text materials')
    await page.getByTestId('add-custom-accommodation').click()
    
    // Step 6: Service Provisions
    await page.getByTestId('services-section').click()
    await page.getByTestId('add-service').click()
    await page.getByTestId('service-type').selectOption('Special Education Instruction')
    await page.getByTestId('service-frequency').fill('5 times per week')
    await page.getByTestId('service-duration').fill('45 minutes')
    await page.getByTestId('service-location').selectOption('Resource Room')
    await page.getByTestId('save-service').click()
    
    // Step 7: Generate draft IEP
    await page.getByTestId('generate-draft').click()
    await expect(page.getByText(/iep draft generated/i)).toBeVisible()
    
    // Step 8: Assign for review
    await page.getByTestId('assign-for-review').click()
    await page.getByTestId('reviewer-special-ed-teacher').check()
    await page.getByTestId('reviewer-general-ed-teacher').check()
    await page.getByTestId('reviewer-school-psychologist').check()
    await page.getByTestId('send-for-review').click()
    
    await expect(page.getByText(/iep sent for review/i)).toBeVisible()
  })

  test('teacher reviews and approves IEP with feedback', async ({ page }) => {
    // Switch to teacher account
    await page.goto('/login')
    await page.getByTestId('email').clear()
    await page.getByTestId('email').fill('sarah.johnson@district.edu')
    await page.getByTestId('password').clear()
    await page.getByTestId('password').fill('TeacherPass456!')
    await page.getByTestId('login-submit').click()
    
    // Step 1: Navigate to pending reviews
    await page.getByTestId('nav-iep-reviews').click()
    await expect(page.getByTestId('pending-reviews-count')).toBeVisible()
    
    // Step 2: Open IEP for review
    await page.getByTestId('iep-marcus-thompson-review').click()
    
    // Step 3: Review student information
    await expect(page.getByText(/marcus thompson/i)).toBeVisible()
    await expect(page.getByText(/grade 5/i)).toBeVisible()
    
    // Step 4: Review goals and provide feedback
    await page.getByTestId('goals-section').click()
    await page.getByTestId('goal-1-feedback').fill('This goal is appropriate and achievable. Suggest adding specific comprehension strategies.')
    await page.getByTestId('goal-1-approval').selectOption('Approved with Suggestions')
    
    await page.getByTestId('behavioral-goal-feedback').fill('Excellent intervention strategy. Consider also providing visual schedules.')
    await page.getByTestId('behavioral-goal-approval').selectOption('Approved')
    
    // Step 5: Review accommodations
    await page.getByTestId('accommodations-review').click()
    await page.getByTestId('accommodation-feedback').fill('All accommodations are suitable for student needs.')
    await page.getByTestId('accommodations-approval').selectOption('Approved')
    
    // Step 6: Review services
    await page.getByTestId('services-review').click()
    await page.getByTestId('service-feedback').fill('Frequency and duration appropriate for student level.')
    await page.getByTestId('services-approval').selectOption('Approved')
    
    // Step 7: Overall approval
    await page.getByTestId('overall-recommendation').selectOption('Approve with Minor Revisions')
    await page.getByTestId('general-comments').fill('Well-written IEP that addresses student needs effectively. Minor suggestions provided for enhancement.')
    
    await page.getByTestId('submit-review').click()
    await expect(page.getByText(/review submitted successfully/i)).toBeVisible()
  })

  test('parent receives IEP notification and provides input', async ({ page }) => {
    // Simulate parent receiving notification
    await page.goto('/parent/dashboard')
    await page.getByTestId('parent-email').fill('parent.thompson@email.com')
    await page.getByTestId('parent-password').fill('ParentPass789!')
    await page.getByTestId('parent-login').click()
    
    // Step 1: View IEP notification
    await expect(page.getByTestId('iep-notification')).toBeVisible()
    await page.getByTestId('view-iep-proposal').click()
    
    // Step 2: Review proposed IEP
    await expect(page.getByText(/proposed iep for marcus/i)).toBeVisible()
    await page.getByTestId('iep-summary-view').click()
    
    // Step 3: Review goals
    await expect(page.getByTestId('reading-goal')).toBeVisible()
    await expect(page.getByTestId('behavioral-goal')).toBeVisible()
    
    // Step 4: Provide parent input
    await page.getByTestId('parent-input-section').click()
    await page.getByTestId('parent-concerns').fill('Marcus struggles with reading at home. We support the goals but would like additional homework support.')
    await page.getByTestId('parent-strengths').fill('Marcus is very creative and responds well to visual learning tools.')
    await page.getByTestId('parent-suggestions').fill('Consider incorporating art-based learning activities.')
    
    // Step 5: Request modifications
    await page.getByTestId('request-modification').click()
    await page.getByTestId('modification-request').fill('Please add art therapy as a related service.')
    
    // Step 6: Schedule IEP meeting
    await page.getByTestId('schedule-meeting').click()
    await page.getByTestId('preferred-date-1').click()
    await page.getByTestId('preferred-time-morning').click()
    await page.getByTestId('meeting-preference').selectOption('In-person')
    
    await page.getByTestId('submit-parent-input').click()
    await expect(page.getByText(/input submitted successfully/i)).toBeVisible()
  })

  test('IEP coordinator finalizes approval and implements IEP', async ({ page }) => {
    // Step 1: Review all feedback and approvals
    await page.getByTestId('nav-iep-management').click()
    await page.getByTestId('iep-marcus-thompson-final').click()
    
    // Step 2: Review all stakeholder feedback
    await page.getByTestId('feedback-summary').click()
    await expect(page.getByTestId('teacher-approval-status')).toBeVisible()
    await expect(page.getByTestId('parent-input-summary')).toBeVisible()
    await expect(page.getByTestId('psychologist-approval')).toBeVisible()
    
    // Step 3: Address parent modification request
    await page.getByTestId('parent-modification-request').click()
    await page.getByTestId('modification-response').fill('Art therapy has been added as a related service per parent request.')
    await page.getByTestId('add-art-therapy-service').click()
    
    // Step 4: Finalize IEP
    await page.getByTestId('finalize-iep').click()
    await page.getByTestId('implementation-date').fill('2024-02-01')
    await page.getByTestId('next-review-date').fill('2025-02-01')
    
    // Step 5: Generate final document
    await page.getByTestId('generate-final-iep').click()
    await expect(page.getByText(/final iep generated/i)).toBeVisible()
    
    // Step 6: Send to implementation team
    await page.getByTestId('send-to-implementation').click()
    await page.getByTestId('implementation-team-teachers').check()
    await page.getByTestId('implementation-team-aides').check()
    await page.getByTestId('implementation-team-therapists').check()
    
    await page.getByTestId('implementation-notes').fill('IEP effective immediately. All staff should review accommodations and service schedules.')
    await page.getByTestId('send-implementation-notice').click()
    
    // Step 7: Schedule progress monitoring
    await page.getByTestId('setup-progress-monitoring').click()
    await page.getByTestId('monitoring-frequency').selectOption('Weekly')
    await page.getByTestId('data-collection-method').selectOption('Digital Portfolio')
    await page.getByTestId('assigned-case-manager').selectOption('Sarah Johnson')
    
    await page.getByTestId('save-monitoring-setup').click()
    await expect(page.getByText(/iep implementation complete/i)).toBeVisible()
  })

  test('verify compliance tracking and reporting', async ({ page }) => {
    // Step 1: Navigate to compliance dashboard
    await page.getByTestId('nav-compliance').click()
    
    // Step 2: Check IEP timeline compliance
    await expect(page.getByTestId('compliance-overview')).toBeVisible()
    await expect(page.getByTestId('active-ieps-count')).toBeVisible()
    await expect(page.getByTestId('due-dates-tracking')).toBeVisible()
    
    // Step 3: Review specific student compliance
    await page.getByTestId('student-marcus-thompson-compliance').click()
    await expect(page.getByTestId('iep-implementation-date')).toBeVisible()
    await expect(page.getByTestId('next-review-due-date')).toBeVisible()
    await expect(page.getByTestId('service-delivery-tracking')).toBeVisible()
    
    // Step 4: Generate compliance report
    await page.getByTestId('generate-compliance-report').click()
    await page.getByTestId('report-period').selectOption('Current Quarter')
    await page.getByTestId('include-all-students').check()
    
    await page.getByTestId('run-compliance-report').click()
    await expect(page.getByText(/compliance report generated/i)).toBeVisible()
    
    // Step 5: Export for state reporting
    await page.getByTestId('export-for-state').click()
    await expect(page.getByText(/state report exported/i)).toBeVisible()
  })
})
