import { test, expect } from '@playwright/test'

test.describe('Golden E2E Flow: Teacher Invitation & Setup', () => {
  test.beforeEach(async ({ page }) => {
    // Mock teacher invitation email link
    await page.goto('/register?invite=teacher_abc123&district=demo-district')
  })

  test('teacher accepts invitation and completes setup', async ({ page }) => {
    // Step 1: Teacher invitation landing
    await expect(page.getByText(/you've been invited/i)).toBeVisible()
    await expect(page.getByText(/demo-district/i)).toBeVisible()
    
    // Step 2: Complete registration
    await page.getByTestId('teacher-email').fill('teacher@democdistrict.edu')
    await page.getByTestId('teacher-password').fill('TeacherPass123!')
    await page.getByTestId('confirm-password').fill('TeacherPass123!')
    await page.getByTestId('accept-invitation').click()

    // Step 3: Professional profile setup
    await expect(page).toHaveURL('/onboarding/teacher-profile')
    await page.getByTestId('teacher-name').fill('Ms. Rodriguez')
    await page.getByTestId('teacher-subject').selectOption('Special Education')
    await page.getByTestId('teacher-grade-levels').selectOption(['K-2', '3-5'])
    await page.getByTestId('teaching-experience').selectOption('5-10 years')
    await page.getByTestId('special-certifications').fill('SPED, Reading Specialist')
    
    await page.getByTestId('save-teacher-profile').click()

    // Step 4: Classroom setup
    await expect(page.getByText(/set up your classroom/i)).toBeVisible()
    await page.getByTestId('create-classroom').click()
    
    await page.getByTestId('classroom-name').fill('Ms. Rodriguez - 3rd Grade SPED')
    await page.getByTestId('classroom-capacity').fill('12')
    await page.getByTestId('classroom-focus').selectOption('Special Education')
    await page.getByTestId('save-classroom').click()

    // Step 5: Student roster (optional for now)
    await expect(page.getByText(/add students/i)).toBeVisible()
    await page.getByTestId('skip-for-now').click() // Can add later

    // Step 6: Complete teacher onboarding
    await expect(page).toHaveURL('/teacher/dashboard')
    await expect(page.getByTestId('teacher-dashboard')).toBeVisible()
    await expect(page.getByText(/welcome, ms. rodriguez/i)).toBeVisible()
  })

  test('teacher can create lesson plan', async ({ page }) => {
    // Assume logged in as teacher
    await page.goto('/teacher/dashboard')
    
    // Navigate to lesson planning
    await page.getByTestId('create-lesson-plan').click()
    await expect(page).toHaveURL('/teacher/lessons/new')

    // Fill lesson details
    await page.getByTestId('lesson-title').fill('Reading Comprehension - Main Idea')
    await page.getByTestId('lesson-subject').selectOption('Reading')
    await page.getByTestId('lesson-grade').selectOption('3rd Grade')
    await page.getByTestId('lesson-duration').fill('45')
    
    // Add learning objectives
    await page.getByTestId('add-objective').click()
    await page.getByTestId('objective-1').fill('Students will identify the main idea in a short passage')
    
    // Add accommodations
    await page.getByTestId('add-accommodation').click()
    await page.getByTestId('accommodation-1').fill('Extended time for reading')
    
    await page.getByTestId('save-lesson').click()
    
    // Verify lesson created
    await expect(page.getByText(/lesson saved/i)).toBeVisible()
    await page.getByTestId('assign-to-students').click()
  })

  test('teacher can view student progress', async ({ page }) => {
    await page.goto('/teacher/students')
    
    // View individual student
    await page.getByTestId('student-card').first().click()
    
    await expect(page.getByTestId('student-overview')).toBeVisible()
    await expect(page.getByTestId('iep-summary')).toBeVisible()
    await expect(page.getByTestId('recent-assessments')).toBeVisible()
    await expect(page.getByTestId('learning-progress')).toBeVisible()
    
    // Add progress note
    await page.getByTestId('add-progress-note').click()
    await page.getByTestId('progress-note-text').fill('Student showed improvement in reading fluency today')
    await page.getByTestId('progress-category').selectOption('Reading')
    await page.getByTestId('save-progress-note').click()
    
    await expect(page.getByText(/progress note saved/i)).toBeVisible()
  })
})
