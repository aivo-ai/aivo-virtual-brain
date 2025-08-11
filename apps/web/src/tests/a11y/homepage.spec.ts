import { test, expect } from '@playwright/test'
import AxeBuilder from '@axe-core/playwright'

test.describe('Accessibility Tests', () => {
  test('should not have any automatically detectable accessibility issues on homepage', async ({
    page,
  }) => {
    await page.goto('/')

    // Wait for page to fully load
    await page.waitForLoadState('networkidle')

    const accessibilityScanResults = await new AxeBuilder({ page })
      .include('body')
      .analyze()

    expect(accessibilityScanResults.violations).toEqual([])
  })

  test('should not have accessibility issues on health page', async ({
    page,
  }) => {
    await page.goto('/health')

    // Wait for health data to load
    await page.waitForSelector('[data-testid="refresh-button"]')

    const accessibilityScanResults = await new AxeBuilder({ page })
      .include('body')
      .analyze()

    expect(accessibilityScanResults.violations).toEqual([])
  })

  test('should not have accessibility issues on dev mocks page', async ({
    page,
  }) => {
    await page.goto('/_dev/mocks')

    // Wait for mock data to render
    await page.waitForSelector('[data-testid="copy-users-button"]')

    const accessibilityScanResults = await new AxeBuilder({ page })
      .include('body')
      .analyze()

    expect(accessibilityScanResults.violations).toEqual([])
  })

  test('should have proper focus management', async ({ page }) => {
    await page.goto('/')

    // Test tab navigation
    await page.keyboard.press('Tab')

    // Should focus on skip link first
    const skipLink = page.locator('.skip-link')
    await expect(skipLink).toBeFocused()

    // Continue tabbing through navigation
    await page.keyboard.press('Tab')
    const homeLink = page.locator('[data-testid="nav-home-link"]')
    await expect(homeLink).toBeFocused()
  })

  test('should have proper heading hierarchy', async ({ page }) => {
    await page.goto('/')

    // Check that page has proper heading structure
    const h1Elements = page.locator('h1')
    await expect(h1Elements).toHaveCount(1)

    const mainHeading = h1Elements.first()
    await expect(mainHeading).toBeVisible()

    // Verify heading text is not empty
    const headingText = await mainHeading.textContent()
    expect(headingText).toBeTruthy()
    expect(headingText!.trim().length).toBeGreaterThan(0)
  })

  test('should have proper ARIA landmarks', async ({ page }) => {
    await page.goto('/')

    // Check for navigation landmark
    const navigation = page.locator('[role="navigation"]')
    await expect(navigation).toBeVisible()

    // Check for main landmark
    const main = page.locator('[role="main"]')
    await expect(main).toBeVisible()

    // Navigation should have proper aria-label
    await expect(navigation).toHaveAttribute('aria-label', 'Main navigation')
  })
})
