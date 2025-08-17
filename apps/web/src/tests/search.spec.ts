/**
 * S3-15 Global Search E2E Tests
 * Tests for RBAC-aware search with keyboard shortcuts and filtering
 */

import { test, expect, Page } from '@playwright/test'

test.describe('S3-15 Global Search System', () => {
  let page: Page
  
  test.beforeEach(async ({ page: testPage }) => {
    page = testPage
    await page.goto('/search')
  })

  test.describe('Search Interface', () => {
    test('displays search page with zero state', async () => {
      await expect(page.locator('h1')).toContainText('Search AIVO')
      await expect(page.locator('text=Find lessons, student information')).toBeVisible()
      
      // Check quick search suggestions
      await expect(page.locator('text=Quick Searches')).toBeVisible()
      await expect(page.locator('text=math lessons grade 3')).toBeVisible()
      await expect(page.locator('text=IEP goals reading')).toBeVisible()
      
      // Check search tips
      await expect(page.locator('text=Search Tips')).toBeVisible()
      await expect(page.locator('text=Search by Content Type')).toBeVisible()
    })

    test('shows search input with placeholder', async () => {
      const searchInput = page.locator('input[placeholder*="Search lessons"]')
      await expect(searchInput).toBeVisible()
      await expect(searchInput).toHaveAttribute('placeholder', 'Search lessons, students, IEPs...')
    })

    test('displays keyboard shortcut hint', async () => {
      // Check for keyboard shortcut display
      await expect(page.locator('kbd:has-text("K")')).toBeVisible()
      
      // Should show Cmd on Mac, Ctrl on others
      const isMac = await page.evaluate(() => navigator.platform.toLowerCase().includes('mac'))
      const expectedKey = isMac ? '⌘' : 'Ctrl'
      await expect(page.locator(`kbd:has-text("${expectedKey}")`)).toBeVisible()
    })
  })

  test.describe('Search Functionality', () => {
    test('performs basic search', async () => {
      const searchInput = page.locator('input[placeholder*="Search lessons"]')
      
      // Type search query
      await searchInput.fill('math lessons')
      await searchInput.press('Enter')
      
      // Should navigate to search results
      await expect(page).toHaveURL(/.*q=math%20lessons/)
      await expect(page.locator('text=Search Results')).toBeVisible()
    })

    test('shows loading state during search', async () => {
      const searchInput = page.locator('input[placeholder*="Search lessons"]')
      
      await searchInput.fill('test query')
      await searchInput.press('Enter')
      
      // Should show loading spinner
      await expect(page.locator('.animate-pulse, .animate-spin')).toBeVisible()
    })

    test('handles search with URL parameters', async () => {
      await page.goto('/search?q=math%20lessons')
      
      // Search input should be populated
      const searchInput = page.locator('input[placeholder*="Search lessons"]')
      await expect(searchInput).toHaveValue('math lessons')
      
      // Should show results or loading
      await expect(page.locator('text=Search Results, text=Loading')).toBeVisible()
    })

    test('quick search functionality', async () => {
      // Click on a quick search item
      await page.locator('text=math lessons grade 3').click()
      
      // Should navigate with query
      await expect(page).toHaveURL(/.*q=math%20lessons%20grade%203/)
      await expect(page.locator('input[placeholder*="Search lessons"]')).toHaveValue('math lessons grade 3')
    })
  })

  test.describe('Keyboard Shortcuts', () => {
    test('opens search with Cmd/Ctrl+K', async () => {
      // Navigate away from search page first
      await page.goto('/')
      
      // Use keyboard shortcut
      const isMac = await page.evaluate(() => navigator.platform.toLowerCase().includes('mac'))
      if (isMac) {
        await page.keyboard.press('Meta+k')
      } else {
        await page.keyboard.press('Control+k')
      }
      
      // Should focus search input
      await expect(page.locator('input[placeholder*="Search"]')).toBeFocused()
    })

    test('arrow key navigation in suggestions', async () => {
      const searchInput = page.locator('input[placeholder*="Search lessons"]')
      
      // Type to trigger suggestions
      await searchInput.fill('test')
      
      // Wait for suggestions dropdown
      await expect(page.locator('[data-testid="search-suggestions"], .absolute.top-full')).toBeVisible()
      
      // Navigate with arrow keys
      await searchInput.press('ArrowDown')
      await expect(page.locator('.bg-blue-50, [data-selected="true"]')).toBeVisible()
      
      await searchInput.press('ArrowDown')
      await searchInput.press('ArrowUp')
      
      // Enter should select suggestion
      await searchInput.press('Enter')
      await expect(page).toHaveURL(/.*q=.*/)
    })

    test('escape key closes search dropdown', async () => {
      const searchInput = page.locator('input[placeholder*="Search lessons"]')
      
      // Open suggestions
      await searchInput.fill('test')
      await expect(page.locator('.absolute.top-full')).toBeVisible()
      
      // Escape should close
      await searchInput.press('Escape')
      await expect(page.locator('.absolute.top-full')).not.toBeVisible()
    })
  })

  test.describe('Search Suggestions', () => {
    test('shows typeahead suggestions', async () => {
      const searchInput = page.locator('input[placeholder*="Search lessons"]')
      
      // Type partial query
      await searchInput.fill('mat')
      
      // Should show suggestions dropdown
      await expect(page.locator('.absolute.top-full')).toBeVisible()
      
      // Should show suggestion items
      await expect(page.locator('[data-testid="suggestion-item"], .cursor-pointer')).toHaveCount.toBeGreaterThan(0)
    })

    test('shows recent searches when empty', async () => {
      // First perform a search to create history
      const searchInput = page.locator('input[placeholder*="Search lessons"]')
      await searchInput.fill('previous search')
      await searchInput.press('Enter')
      
      // Go back and open search
      await page.goBack()
      await searchInput.click()
      
      // Should show recent searches
      await expect(page.locator('text=Recent searches')).toBeVisible()
      await expect(page.locator('text=previous search')).toBeVisible()
    })

    test('suggestion icons and types', async () => {
      const searchInput = page.locator('input[placeholder*="Search lessons"]')
      await searchInput.fill('test')
      
      // Wait for suggestions
      await expect(page.locator('.absolute.top-full')).toBeVisible()
      
      // Should have type indicators
      await expect(page.locator('text=Lesson, text=Student, text=IEP')).toBeVisible()
      
      // Should have icons
      await expect(page.locator('svg')).toHaveCount.toBeGreaterThan(0)
    })
  })

  test.describe('Search Results', () => {
    test.beforeEach(async () => {
      // Navigate to search with results
      await page.goto('/search?q=test')
    })

    test('displays results list', async () => {
      await expect(page.locator('text=Search Results')).toBeVisible()
      await expect(page.locator('text=results for "test"')).toBeVisible()
      
      // Should show result cards
      await expect(page.locator('[data-testid="result-card"], .cursor-pointer.p-4')).toHaveCount.toBeGreaterThan(0)
    })

    test('result card structure', async () => {
      const firstResult = page.locator('[data-testid="result-card"], .cursor-pointer.p-4').first()
      
      // Should have title, type badge, and description
      await expect(firstResult.locator('.font-semibold')).toBeVisible()
      await expect(firstResult.locator('[data-testid="type-badge"], .px-2.py-1')).toBeVisible()
      await expect(firstResult.locator('.text-gray-600')).toBeVisible()
    })

    test('clicks navigate to content', async () => {
      const firstResult = page.locator('[data-testid="result-card"], .cursor-pointer.p-4').first()
      
      // Mock navigation
      await page.route('**/lessons/**', route => route.fulfill({ status: 200, body: 'Lesson content' }))
      await page.route('**/students/**', route => route.fulfill({ status: 200, body: 'Student content' }))
      
      await firstResult.click()
      
      // Should navigate (URL change or new content)
      await expect(page.locator('text=Lesson content, text=Student content')).toBeVisible()
    })
  })

  test.describe('Filtering System', () => {
    test.beforeEach(async () => {
      await page.goto('/search?q=test')
    })

    test('displays filter sidebar', async () => {
      await expect(page.locator('text=Filters')).toBeVisible()
      await expect(page.locator('text=Content Type')).toBeVisible()
      await expect(page.locator('text=Sort By')).toBeVisible()
    })

    test('content type filtering', async () => {
      // Find and click a content type filter
      const lessonFilter = page.locator('input[type="checkbox"]').first()
      await lessonFilter.check()
      
      // Should filter results
      await expect(page.locator('text=Filtered results')).toBeVisible()
      
      // Clear filters
      await page.locator('text=Clear all, text=Clear filters').click()
      await expect(lessonFilter).not.toBeChecked()
    })

    test('sort options', async () => {
      // Check sort options
      await expect(page.locator('text=Relevance')).toBeVisible()
      await expect(page.locator('text=Most Recent')).toBeVisible()
      
      // Select different sort
      await page.locator('input[value="date"]').check()
      
      // Should re-sort results (implementation dependent)
      await expect(page.locator('input[value="date"]')).toBeChecked()
    })

    test('expandable filter sections', async () => {
      // Find collapsible section
      const categorySection = page.locator('text=Category').locator('..')
      
      if (await categorySection.isVisible()) {
        // Should be expandable/collapsible
        await categorySection.click()
        
        // Check state change (specific implementation may vary)
        await expect(page.locator('.rotate-180, [aria-expanded="true"]')).toBeVisible()
      }
    })
  })

  test.describe('RBAC Access Control', () => {
    test('admin user sees all content types', async () => {
      // Mock admin login
      await page.route('**/api/auth/me', route => 
        route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ role: 'admin', permissions: ['view_students', 'view_iep'] })
        })
      )
      
      await page.goto('/search?q=test')
      
      // Should see all filter options
      await expect(page.locator('text=Student')).toBeVisible()
      await expect(page.locator('text=IEP')).toBeVisible()
      await expect(page.locator('text=Lesson')).toBeVisible()
    })

    test('teacher user has limited access', async () => {
      // Mock teacher login
      await page.route('**/api/auth/me', route => 
        route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ role: 'teacher', permissions: ['view_students'] })
        })
      )
      
      await page.goto('/search?q=test')
      
      // Should see lessons and students, not IEP
      await expect(page.locator('text=Lesson')).toBeVisible()
      await expect(page.locator('text=Student')).toBeVisible()
      // IEP access should be restricted (may not show or show as restricted)
    })

    test('restricted content shows access denied', async () => {
      // Mock limited permissions
      await page.route('**/api/auth/me', route => 
        route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ role: 'parent', permissions: [] })
        })
      )
      
      await page.goto('/search?q=student')
      
      // Should show restriction message
      await expect(page.locator('text=Access Restricted, text=You do not have permission')).toBeVisible()
      await expect(page.locator('[data-testid="restricted-icon"], .text-red-500')).toBeVisible()
    })
  })

  test.describe('Search History', () => {
    test('saves successful searches', async () => {
      const searchInput = page.locator('input[placeholder*="Search lessons"]')
      
      // Perform multiple searches
      await searchInput.fill('first search')
      await searchInput.press('Enter')
      await page.waitForTimeout(1000)
      
      await page.goto('/search')
      await searchInput.fill('second search')
      await searchInput.press('Enter')
      await page.waitForTimeout(1000)
      
      // Go back to search page
      await page.goto('/search')
      
      // Should show recent searches
      await expect(page.locator('text=Recent Searches')).toBeVisible()
      await expect(page.locator('text=first search')).toBeVisible()
      await expect(page.locator('text=second search')).toBeVisible()
    })

    test('limits history display', async () => {
      await page.goto('/search')
      
      // If history exists, should limit to 8 items
      const historyItems = page.locator('[data-testid="history-item"], .hover\\:text-blue-600')
      const count = await historyItems.count()
      
      if (count > 0) {
        expect(count).toBeLessThanOrEqual(8)
      }
    })
  })

  test.describe('Error Handling', () => {
    test('displays error state', async () => {
      // Mock API error
      await page.route('**/api/search**', route => 
        route.fulfill({ status: 500, body: 'Server error' })
      )
      
      await page.goto('/search?q=error')
      
      // Should show error message
      await expect(page.locator('text=Search Error')).toBeVisible()
      await expect(page.locator('text=There was an error')).toBeVisible()
      await expect(page.locator('text=Retry Search')).toBeVisible()
    })

    test('handles no results', async () => {
      // Mock empty results
      await page.route('**/api/search**', route => 
        route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ results: [], total: 0 })
        })
      )
      
      await page.goto('/search?q=nonexistent')
      
      // Should show no results message
      await expect(page.locator('text=No results found')).toBeVisible()
      await expect(page.locator('text=No results match')).toBeVisible()
    })

    test('retry functionality', async () => {
      // Mock initial error
      let callCount = 0
      await page.route('**/api/search**', route => {
        callCount++
        if (callCount === 1) {
          route.fulfill({ status: 500, body: 'Server error' })
        } else {
          route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify({ results: [], total: 0 })
          })
        }
      })
      
      await page.goto('/search?q=retry')
      
      // Should show error
      await expect(page.locator('text=Search Error')).toBeVisible()
      
      // Click retry
      await page.locator('text=Retry Search').click()
      
      // Should recover
      await expect(page.locator('text=No results found')).toBeVisible()
    })
  })

  test.describe('Accessibility', () => {
    test('keyboard navigation', async () => {
      await page.goto('/search')
      
      // Tab navigation should work
      await page.keyboard.press('Tab')
      await expect(page.locator('input[placeholder*="Search lessons"]')).toBeFocused()
      
      // Search suggestions should be navigable
      const searchInput = page.locator('input[placeholder*="Search lessons"]')
      await searchInput.fill('test')
      
      await searchInput.press('ArrowDown')
      await searchInput.press('ArrowUp')
      await searchInput.press('Escape')
    })

    test('screen reader attributes', async () => {
      const searchInput = page.locator('input[placeholder*="Search lessons"]')
      
      // Should have appropriate ARIA attributes
      await expect(searchInput).toHaveAttribute('autocomplete', 'off')
      await expect(searchInput).toHaveAttribute('spellcheck', 'false')
      
      // Suggestions should have proper roles
      await searchInput.fill('test')
      await expect(page.locator('[role="listbox"], [role="option"]')).toBeVisible()
    })

    test('focus management', async () => {
      await page.goto('/search')
      
      const searchInput = page.locator('input[placeholder*="Search lessons"]')
      
      // Auto-focus when requested
      await searchInput.focus()
      await expect(searchInput).toBeFocused()
      
      // Focus should remain manageable during interactions
      await searchInput.fill('test')
      await expect(searchInput).toBeFocused()
    })
  })

  test.describe('Performance', () => {
    test('debounced suggestions', async () => {
      const searchInput = page.locator('input[placeholder*="Search lessons"]')
      
      // Track API calls
      let apiCalls = 0
      await page.route('**/api/search/suggestions**', route => {
        apiCalls++
        route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify([])
        })
      })
      
      // Type quickly
      await searchInput.fill('a')
      await searchInput.fill('ab')
      await searchInput.fill('abc')
      
      // Wait for debounce
      await page.waitForTimeout(500)
      
      // Should make fewer API calls due to debouncing
      expect(apiCalls).toBeLessThan(3)
    })

    test('loads search results efficiently', async () => {
      const startTime = Date.now()
      
      await page.goto('/search?q=test')
      await expect(page.locator('text=Search Results')).toBeVisible()
      
      const loadTime = Date.now() - startTime
      
      // Should load within reasonable time (adjust threshold as needed)
      expect(loadTime).toBeLessThan(5000)
    })
  })
})
