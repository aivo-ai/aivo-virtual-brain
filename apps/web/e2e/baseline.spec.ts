import { test, expect } from '@playwright/test'

test.describe('Golden E2E Flow: Baseline Assessment', () => {
  test.beforeEach(async ({ page }) => {
    // Login as teacher
    await page.goto('/login')
    await page.getByTestId('login-email').fill('teacher@democdistrict.edu')
    await page.getByTestId('login-password').fill('TeacherPass123!')
    await page.getByTestId('login-submit').click()
  })

  test('teacher initiates baseline assessment for new student', async ({ page }) => {
    // Step 1: Navigate to student management
    await page.getByTestId('nav-students').click()
    await page.getByTestId('add-new-student').click()
    
    // Step 2: Add student basic info
    await page.getByTestId('student-name').fill('Emma Johnson')
    await page.getByTestId('student-grade').selectOption('4th Grade')
    await page.getByTestId('student-age').fill('9')
    await page.getByTestId('student-id').fill('EJ-2024-001')
    await page.getByTestId('save-student').click()
    
    // Step 3: Start baseline assessment
    await expect(page.getByText(/student added successfully/i)).toBeVisible()
    await page.getByTestId('start-baseline-assessment').click()
    
    // Step 4: Assessment configuration
    await expect(page.getByText(/baseline assessment setup/i)).toBeVisible()
    await page.getByTestId('assessment-areas').selectOption(['Reading', 'Math', 'Writing'])
    await page.getByTestId('adaptive-difficulty').check()
    await page.getByTestId('time-limit').fill('60')
    await page.getByTestId('accommodation-text-to-speech').check()
    await page.getByTestId('start-assessment').click()
    
    // Step 5: Assessment instructions for student
    await expect(page.getByText(/assessment started/i)).toBeVisible()
    await expect(page.getByTestId('assessment-code')).toBeVisible()
    
    // Share assessment link with student (mocked)
    await page.getByTestId('copy-assessment-link').click()
    await expect(page.getByText(/link copied/i)).toBeVisible()
  })

  test('student completes baseline assessment', async ({ page }) => {
    // Open student assessment interface
    await page.goto('/assessment/start?code=BA-2024-001&student=emma-johnson')
    
    // Step 1: Student login/verification
    await page.getByTestId('student-name-verify').fill('Emma Johnson')
    await page.getByTestId('start-assessment-button').click()
    
    // Step 2: Assessment instructions
    await expect(page.getByText(/welcome to your assessment/i)).toBeVisible()
    await page.getByTestId('understand-instructions').check()
    await page.getByTestId('begin-assessment').click()
    
    // Step 3: Reading assessment section
    await expect(page.getByText(/reading section/i)).toBeVisible()
    
    // Sample reading question
    await page.getByTestId('reading-question-1').click()
    await page.getByTestId('answer-choice-b').click()
    await page.getByTestId('next-question').click()
    
    // Multiple choice questions (simulate 5 questions)
    for (let i = 2; i <= 5; i++) {
      await page.getByTestId(`reading-question-${i}`).waitFor()
      await page.getByTestId('answer-choice-a').click() // Simulate answers
      await page.getByTestId('next-question').click()
    }
    
    // Step 4: Math assessment section
    await expect(page.getByText(/math section/i)).toBeVisible()
    
    // Math problem solving
    for (let i = 1; i <= 5; i++) {
      await page.getByTestId(`math-question-${i}`).waitFor()
      await page.getByTestId('math-answer-input').fill((i * 2).toString()) // Simple answers
      await page.getByTestId('submit-answer').click()
    }
    
    // Step 5: Writing assessment
    await expect(page.getByText(/writing section/i)).toBeVisible()
    await page.getByTestId('writing-prompt').waitFor()
    await page.getByTestId('writing-response').fill('This is my sample writing response for the baseline assessment. I like to read books and play outside.')
    await page.getByTestId('submit-writing').click()
    
    // Step 6: Assessment completion
    await expect(page.getByText(/assessment completed/i)).toBeVisible()
    await page.getByTestId('finish-assessment').click()
    
    await expect(page.getByText(/thank you for completing/i)).toBeVisible()
  })

  test('teacher reviews baseline results and creates learning plan', async ({ page }) => {
    // Navigate to assessment results
    await page.goto('/teacher/assessments/results/BA-2024-001')
    
    // Step 1: Review overall results
    await expect(page.getByTestId('assessment-overview')).toBeVisible()
    await expect(page.getByTestId('overall-score')).toBeVisible()
    await expect(page.getByTestId('grade-level-equivalent')).toBeVisible()
    
    // Step 2: Detailed subject analysis
    await page.getByTestId('reading-results-tab').click()
    await expect(page.getByTestId('reading-strengths')).toBeVisible()
    await expect(page.getByTestId('reading-areas-for-growth')).toBeVisible()
    await expect(page.getByTestId('reading-recommendations')).toBeVisible()
    
    await page.getByTestId('math-results-tab').click()
    await expect(page.getByTestId('math-concept-mastery')).toBeVisible()
    
    // Step 3: Generate learning recommendations
    await page.getByTestId('generate-learning-plan').click()
    await expect(page.getByText(/ai-generated recommendations/i)).toBeVisible()
    
    // Step 4: Customize and approve learning plan
    await page.getByTestId('edit-learning-goals').click()
    await page.getByTestId('goal-1-text').fill('Improve reading comprehension to grade level')
    await page.getByTestId('goal-2-text').fill('Strengthen basic math fact fluency')
    
    await page.getByTestId('save-learning-plan').click()
    await expect(page.getByText(/learning plan created/i)).toBeVisible()
    
    // Step 5: Share results with parent
    await page.getByTestId('share-with-parent').click()
    await page.getByTestId('parent-email').fill('parent@example.com')
    await page.getByTestId('include-recommendations').check()
    await page.getByTestId('send-results').click()
    
    await expect(page.getByText(/results shared with parent/i)).toBeVisible()
  })
})
