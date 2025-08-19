import { test, expect } from '@playwright/test'

test.describe('Golden E2E Flow: Learn + Game Journey', () => {
  test.beforeEach(async ({ page }) => {
    // Login as student
    await page.goto('/login')
    await page.getByTestId('student-login-tab').click()
    await page.getByTestId('student-id').fill('emma-johnson-001')
    await page.getByTestId('student-access-code').fill('EJ2024')
    await page.getByTestId('student-login-submit').click()
  })

  test('student completes adaptive learning session with game rewards', async ({ page }) => {
    // Step 1: Student dashboard
    await expect(page).toHaveURL('/student/dashboard')
    await expect(page.getByText(/welcome back, emma/i)).toBeVisible()
    
    // Check learning goals progress
    await expect(page.getByTestId('learning-goals-widget')).toBeVisible()
    await expect(page.getByTestId('progress-bar')).toBeVisible()
    
    // Step 2: Start recommended lesson
    await page.getByTestId('recommended-lesson').first().click()
    
    // Step 3: Lesson introduction
    await expect(page.getByText(/reading comprehension/i)).toBeVisible()
    await page.getByTestId('start-lesson').click()
    
    // Step 4: Adaptive learning content
    // Question 1 - Multiple choice
    await expect(page.getByTestId('lesson-question')).toBeVisible()
    await page.getByTestId('choice-b').click()
    await page.getByTestId('submit-answer').click()
    
    // Feedback and encouragement
    await expect(page.getByText(/great job/i)).toBeVisible()
    await page.getByTestId('continue-learning').click()
    
    // Question 2 - Interactive drag-and-drop
    await page.getByTestId('draggable-item-1').dragTo(page.getByTestId('drop-zone-a'))
    await page.getByTestId('check-answer').click()
    
    // Step 5: Mini-game break (earned after 3 correct answers)
    await expect(page.getByText(/you've earned a game break/i)).toBeVisible()
    await page.getByTestId('play-mini-game').click()
    
    // Simple word matching game
    await expect(page.getByTestId('word-game')).toBeVisible()
    await page.getByTestId('word-pair-1').click()
    await page.getByTestId('word-pair-1-match').click()
    
    // Complete mini-game
    await expect(page.getByText(/mini-game completed/i)).toBeVisible()
    await page.getByTestId('return-to-lesson').click()
    
    // Step 6: Continue lesson with increased difficulty
    for (let i = 3; i <= 5; i++) {
      await page.getByTestId(`question-${i}`).waitFor()
      await page.getByTestId('answer-input').fill('sample answer')
      await page.getByTestId('submit-answer').click()
      await page.getByTestId('continue').click()
    }
    
    // Step 7: Lesson completion and rewards
    await expect(page.getByText(/lesson completed/i)).toBeVisible()
    await expect(page.getByTestId('xp-earned')).toBeVisible()
    await expect(page.getByTestId('badge-earned')).toBeVisible()
    
    // Step 8: Progress update
    await page.getByTestId('view-progress').click()
    await expect(page.getByTestId('updated-progress-bar')).toBeVisible()
    await expect(page.getByTestId('mastery-level')).toBeVisible()
  })

  test('student plays educational game with learning reinforcement', async ({ page }) => {
    // Navigate to games section
    await page.getByTestId('nav-games').click()
    
    // Step 1: Game selection based on learning needs
    await expect(page.getByTestId('recommended-games')).toBeVisible()
    await page.getByTestId('math-adventure-game').click()
    
    // Step 2: Game setup and difficulty selection
    await expect(page.getByText(/math adventure/i)).toBeVisible()
    await page.getByTestId('difficulty-level').selectOption('Grade 4')
    await page.getByTestId('game-focus').selectOption('Addition/Subtraction')
    await page.getByTestId('start-game').click()
    
    // Step 3: Game tutorial
    await expect(page.getByTestId('game-tutorial')).toBeVisible()
    await page.getByTestId('skip-tutorial').click()
    
    // Step 4: Gameplay with math problems
    // Level 1
    await expect(page.getByTestId('math-problem')).toBeVisible()
    await page.getByTestId('answer-15').click() // 7 + 8 = 15
    await expect(page.getByText(/correct/i)).toBeVisible()
    
    // Collect rewards
    await page.getByTestId('collect-coins').click()
    
    // Level 2 with higher difficulty
    await page.getByTestId('next-level').click()
    await page.getByTestId('number-input').fill('23') // 15 + 8 = 23
    await page.getByTestId('submit-math-answer').click()
    
    // Step 5: Game completion and learning summary
    await expect(page.getByText(/level completed/i)).toBeVisible()
    await page.getByTestId('view-learning-summary').click()
    
    await expect(page.getByTestId('skills-practiced')).toBeVisible()
    await expect(page.getByTestId('accuracy-score')).toBeVisible()
    await expect(page.getByTestId('time-spent')).toBeVisible()
    
    // Step 6: Save progress and continue learning
    await page.getByTestId('save-game-progress').click()
    await page.getByTestId('continue-learning').click()
    
    // Return to adaptive lesson suggestions
    await expect(page.getByTestId('suggested-next-lesson')).toBeVisible()
  })

  test('adaptive system adjusts difficulty based on performance', async ({ page }) => {
    // Start a lesson series
    await page.getByTestId('lesson-series-reading').click()
    
    // Step 1: Initial assessment within lesson
    await page.getByTestId('start-adaptive-lesson').click()
    
    // Answer questions incorrectly to trigger difficulty adjustment
    for (let i = 1; i <= 3; i++) {
      await page.getByTestId('wrong-answer').click()
      await page.getByTestId('submit-answer').click()
      await page.getByTestId('continue').click()
    }
    
    // Step 2: System should lower difficulty
    await expect(page.getByText(/let's try something easier/i)).toBeVisible()
    await page.getByTestId('continue-adapted').click()
    
    // Step 3: Easier questions presented
    await expect(page.getByTestId('simplified-question')).toBeVisible()
    await page.getByTestId('correct-answer').click()
    await page.getByTestId('submit-answer').click()
    
    // Positive reinforcement
    await expect(page.getByText(/excellent work/i)).toBeVisible()
    
    // Step 4: Gradually increase difficulty as student succeeds
    for (let i = 1; i <= 3; i++) {
      await page.getByTestId('correct-answer').click()
      await page.getByTestId('submit-answer').click()
      await page.getByTestId('continue').click()
    }
    
    // Step 5: System increases difficulty
    await expect(page.getByText(/ready for a challenge/i)).toBeVisible()
    await page.getByTestId('accept-challenge').click()
    
    await expect(page.getByTestId('advanced-question')).toBeVisible()
  })

  test('parent receives progress report from learning session', async ({ page, context }) => {
    // Complete a learning session first
    await page.getByTestId('quick-lesson').click()
    await page.getByTestId('complete-lesson-fast').click()
    
    // Generate and send parent report
    await page.getByTestId('send-progress-to-parent').click()
    
    // Switch to parent view (simulate parent login)
    const parentPage = await context.newPage()
    await parentPage.goto('/parent/dashboard')
    
    // Parent receives notification
    await expect(parentPage.getByTestId('new-progress-notification')).toBeVisible()
    await parentPage.getByTestId('view-progress-report').click()
    
    // Parent views detailed report
    await expect(parentPage.getByTestId('learning-session-summary')).toBeVisible()
    await expect(parentPage.getByTestId('skills-practiced')).toBeVisible()
    await expect(parentPage.getByTestId('time-spent')).toBeVisible()
    await expect(parentPage.getByTestId('areas-of-strength')).toBeVisible()
    await expect(parentPage.getByTestId('areas-for-improvement')).toBeVisible()
    
    await parentPage.close()
  })
})
