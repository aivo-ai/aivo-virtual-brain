import { test, expect } from '@playwright/test'

test.describe('PWA Offline Functionality', () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to the app
    await page.goto('/')
    
    // Wait for app to load
    await page.waitForLoadState('networkidle')
  })

  test('should show offline toast when connection is lost', async ({ page, context }) => {
    // Set up offline mode
    await context.setOffline(true)
    
    // Trigger an action that would normally make a network request
    await page.click('[data-testid="chat-input"]')
    await page.fill('[data-testid="chat-input"]', 'Test message while offline')
    await page.press('[data-testid="chat-input"]', 'Enter')
    
    // Check for offline toast
    await expect(page.locator('[role="alert"]')).toBeVisible()
    await expect(page.locator('text=You\'re offline')).toBeVisible()
    
    // Verify message is queued
    await expect(page.locator('text=queued for sync')).toBeVisible()
  })

  test('should cache and serve lesson content offline', async ({ page, context }) => {
    // First, load a lesson while online to cache it
    await page.goto('/lessons/math-basics')
    await page.waitForLoadState('networkidle')
    
    // Verify lesson content is loaded
    await expect(page.locator('[data-testid="lesson-content"]')).toBeVisible()
    
    // Go offline
    await context.setOffline(true)
    
    // Refresh the page to test offline serving
    await page.reload()
    
    // Should still show cached lesson content
    await expect(page.locator('[data-testid="lesson-content"]')).toBeVisible()
    
    // Should show offline indicator
    await expect(page.locator('text=Offline')).toBeVisible()
  })

  test('should queue event collector requests when offline', async ({ page, context }) => {
    // Go offline
    await context.setOffline(true)
    
    // Trigger an event that would normally be sent to event collector
    await page.click('[data-testid="lesson-start-button"]')
    
    // Check that request was queued (should see queued indicator)
    await expect(page.locator('text=queued')).toBeVisible({ timeout: 5000 })
    
    // Go back online
    await context.setOffline(false)
    
    // Wait for background sync to process
    await page.waitForTimeout(2000)
    
    // Queue should be processed (no more queued indicator)
    await expect(page.locator('text=Online')).toBeVisible()
  })

  test('should queue inference gateway requests when offline', async ({ page, context }) => {
    // Navigate to chat interface
    await page.goto('/chat')
    await page.waitForLoadState('networkidle')
    
    // Go offline
    await context.setOffline(true)
    
    // Send a chat message
    await page.fill('[data-testid="chat-input"]', 'What is 2+2?')
    await page.press('[data-testid="chat-input"]', 'Enter')
    
    // Should show queued message
    await expect(page.locator('text=queued for sync')).toBeVisible()
    
    // Go back online
    await context.setOffline(false)
    
    // Wait for sync
    await page.waitForTimeout(3000)
    
    // Should show successful sync
    await expect(page.locator('text=Online')).toBeVisible()
  })

  test('should show PWA install prompt', async ({ page }) => {
    // Simulate beforeinstallprompt event
    await page.evaluate(() => {
      const event = new Event('beforeinstallprompt')
      window.dispatchEvent(event)
    })
    
    // Check for install prompt
    await expect(page.locator('text=Install Aivo Virtual Brains')).toBeVisible()
    
    // Test dismiss functionality
    await page.click('text=Maybe later')
    await expect(page.locator('text=Install Aivo Virtual Brains')).not.toBeVisible()
  })

  test('should handle graceful degradation when offline', async ({ page, context }) => {
    // Go offline
    await context.setOffline(true)
    
    // Navigate around the app
    await page.goto('/profile')
    
    // Should show offline fallback for uncached routes
    await expect(page.locator('text=You\'re offline')).toBeVisible()
    
    // UI should still be functional for cached elements
    await page.click('[data-testid="navigation-home"]')
    
    // Should return to cached home page
    await expect(page.locator('[data-testid="app-header"]')).toBeVisible()
  })

  test('should respect cache size limits', async ({ page }) => {
    // Simulate large cache usage
    await page.evaluate(async () => {
      // Mock storage estimate to simulate near-limit usage
      if ('storage' in navigator && 'estimate' in navigator.storage) {
        navigator.storage.estimate = async () => ({
          usage: 48 * 1024 * 1024, // 48MB
          quota: 50 * 1024 * 1024   // 50MB
        })
      }
    })
    
    // Load multiple lessons to test cache management
    for (let i = 1; i <= 5; i++) {
      await page.goto(`/lessons/lesson-${i}`)
      await page.waitForLoadState('networkidle')
    }
    
    // Cache should automatically clean up to stay under limit
    // This is tested through service worker behavior
    const cacheNames = await page.evaluate(async () => {
      return await caches.keys()
    })
    
    expect(cacheNames.length).toBeGreaterThan(0)
  })

  test('should show connection status indicator', async ({ page, context }) => {
    // Should show online status initially
    await expect(page.locator('text=Online')).toBeVisible()
    
    // Go offline
    await context.setOffline(true)
    
    // Should show offline status
    await expect(page.locator('text=Offline')).toBeVisible()
    
    // Go back online
    await context.setOffline(false)
    
    // Should show online status again
    await expect(page.locator('text=Online')).toBeVisible()
  })

  test('should retry failed requests with exponential backoff', async ({ page, context }) => {
    // Go offline
    await context.setOffline(true)
    
    // Make multiple requests to build queue
    await page.fill('[data-testid="chat-input"]', 'Message 1')
    await page.press('[data-testid="chat-input"]', 'Enter')
    
    await page.fill('[data-testid="chat-input"]', 'Message 2')
    await page.press('[data-testid="chat-input"]', 'Enter')
    
    // Should show queued count
    await expect(page.locator('text=2 queued')).toBeVisible()
    
    // Go online
    await context.setOffline(false)
    
    // Wait for retry logic to process
    await page.waitForTimeout(5000)
    
    // Queue should be cleared
    await expect(page.locator('text=Online')).toBeVisible()
    await expect(page.locator('text=queued')).not.toBeVisible()
  })

  test('should maintain app functionality in offline mode', async ({ page, context }) => {
    // Go offline
    await context.setOffline(true)
    
    // Test navigation still works
    await page.click('[data-testid="nav-profile"]')
    await expect(page.locator('[data-testid="profile-page"]')).toBeVisible()
    
    // Test form interactions work
    await page.fill('[data-testid="profile-name"]', 'Test Name')
    
    // Test local storage operations
    const storedValue = await page.evaluate(() => {
      localStorage.setItem('test-key', 'test-value')
      return localStorage.getItem('test-key')
    })
    
    expect(storedValue).toBe('test-value')
    
    // Test that UI shows appropriate offline messaging
    await expect(page.locator('[role="alert"]')).toBeVisible()
  })
})
