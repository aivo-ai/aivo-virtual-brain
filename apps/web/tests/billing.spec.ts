import { test, expect } from '@playwright/test';

test.describe('S3-17 Billing System', () => {
  test.beforeEach(async ({ page }) => {
    // Mock API responses
    await page.route('**/api/billing/**', (route) => {
      const url = route.request().url();
      
      if (url.includes('/plans')) {
        route.fulfill({
          json: [
            {
              id: 'basic',
              name: 'Basic',
              description: 'Perfect for individual learners',
              price: 9.99,
              currency: 'USD',
              interval: 'month',
              features: ['5 AI tutoring sessions per month', 'Basic progress tracking', 'Parent dashboard'],
              trialDays: 14
            },
            {
              id: 'pro',
              name: 'Pro',
              description: 'Best for families',
              price: 29.99,
              currency: 'USD',
              interval: 'month',
              popular: true,
              features: ['Unlimited AI tutoring', 'Advanced analytics', 'Priority support'],
              trialDays: 14
            }
          ]
        });
      } else if (url.includes('/billing-info')) {
        route.fulfill({
          json: {
            subscription: {
              id: 'sub_123',
              planId: 'pro',
              planName: 'Pro',
              status: 'active',
              amount: 29.99,
              currency: 'USD',
              interval: 'month',
              nextBillingDate: new Date(Date.now() + 30 * 24 * 60 * 60 * 1000).toISOString()
            },
            paymentMethod: {
              id: 'pm_123',
              brand: 'visa',
              last4: '4242',
              expiryMonth: 12,
              expiryYear: 2025
            },
            invoices: [],
            studentCount: 2
          }
        });
      } else if (url.includes('/dunning-state')) {
        route.fulfill({
          json: null
        });
      }
    });
  });

  test('should display available plans with pricing', async ({ page }) => {
    await page.goto('/billing/plans');
    
    // Check page title
    await expect(page.locator('h1')).toContainText('Choose Your Plan');
    
    // Check that plans are displayed
    await expect(page.locator('[data-testid="plan-card"]')).toHaveCount(2);
    
    // Check Basic plan
    const basicPlan = page.locator('[data-testid="plan-card"]').first();
    await expect(basicPlan).toContainText('Basic');
    await expect(basicPlan).toContainText('$9.99');
    await expect(basicPlan).toContainText('14-day free trial');
    
    // Check Pro plan (popular)
    const proPlan = page.locator('[data-testid="plan-card"]').nth(1);
    await expect(proPlan).toContainText('Pro');
    await expect(proPlan).toContainText('$29.99');
    await expect(proPlan).toContainText('Most Popular');
  });

  test('should show sibling discount when multiple students selected', async ({ page }) => {
    await page.goto('/billing/plans');
    
    // Select 2 students
    await page.selectOption('select', '2');
    
    // Check that sibling discount is displayed
    await expect(page.locator('text=15% sibling discount applied')).toBeVisible();
    
    // Check that original price is shown crossed out
    await expect(page.locator('.line-through')).toBeVisible();
  });

  test('should toggle between monthly and yearly billing', async ({ page }) => {
    await page.goto('/billing/plans');
    
    // Initially should show monthly
    await expect(page.locator('text=Monthly')).toHaveClass(/font-medium/);
    
    // Toggle to yearly
    await page.click('[role="switch"]');
    await expect(page.locator('text=Yearly')).toHaveClass(/font-medium/);
    await expect(page.locator('text=Save 20%')).toBeVisible();
  });

  test('should handle plan selection and checkout', async ({ page }) => {
    // Mock checkout creation
    await page.route('**/api/checkout', (route) => {
      route.fulfill({
        json: {
          id: 'cs_test_123',
          url: 'https://checkout.stripe.com/pay/cs_test_123'
        }
      });
    });

    await page.goto('/billing/plans');
    
    // Click on Pro plan button
    await page.click('[data-testid="plan-card"]:nth-child(2) button');
    
    // Should redirect to checkout (we'll mock this)
    await expect(page).toHaveURL(/checkout\.stripe\.com/);
  });

  test('should display billing management page', async ({ page }) => {
    await page.goto('/billing/manage');
    
    // Check page title
    await expect(page.locator('h1')).toContainText('Billing Management');
    
    // Check subscription details
    await expect(page.locator('text=Current Subscription')).toBeVisible();
    await expect(page.locator('text=Pro')).toBeVisible();
    await expect(page.locator('text=active')).toBeVisible();
    await expect(page.locator('text=$29.99/month')).toBeVisible();
    
    // Check payment method
    await expect(page.locator('text=Payment Method')).toBeVisible();
    await expect(page.locator('text=•••• •••• •••• 4242')).toBeVisible();
    await expect(page.locator('text=VISA')).toBeVisible();
    
    // Check student count and discount
    await expect(page.locator('text=Students:')).toBeVisible();
    await expect(page.locator('text=2')).toBeVisible();
    await expect(page.locator('text=15% OFF')).toBeVisible();
  });

  test('should show dunning banner for failed payments', async ({ page }) => {
    // Override dunning state to show failed payment
    await page.route('**/api/billing/dunning-state', (route) => {
      route.fulfill({
        json: {
          status: 'payment_failed',
          lastFailedAt: new Date(Date.now() - 24 * 60 * 60 * 1000).toISOString(),
          attemptCount: 1,
          nextRetryAt: new Date(Date.now() + 24 * 60 * 60 * 1000).toISOString(),
          gracePeriodEnds: new Date(Date.now() + 7 * 24 * 60 * 60 * 1000).toISOString()
        }
      });
    });

    await page.goto('/billing/plans');
    
    // Check that dunning banner is displayed
    await expect(page.locator('[data-testid="dunning-banner"]')).toBeVisible();
    await expect(page.locator('text=Payment Failed')).toBeVisible();
    await expect(page.locator('text=Update Payment Method')).toBeVisible();
  });

  test('should handle subscription cancellation', async ({ page }) => {
    // Mock cancellation
    await page.route('**/api/billing/subscriptions/*/cancel', (route) => {
      route.fulfill({
        json: { success: true }
      });
    });

    await page.goto('/billing/manage');
    
    // Click cancel subscription
    await page.click('text=Cancel Subscription');
    
    // Confirm cancellation in modal
    await expect(page.locator('text=Are you sure you want to cancel')).toBeVisible();
    await page.click('button:has-text("Cancel"):not(:has-text("Keep"))');
    
    // Should show success or redirect
    await expect(page.locator('text=Canceling...')).toBeVisible();
  });

  test('should display checkout success page', async ({ page }) => {
    // Mock checkout status
    await page.route('**/api/checkout/*/status', (route) => {
      route.fulfill({
        json: {
          status: 'complete',
          subscriptionId: 'sub_new_123',
          planName: 'Pro Plan',
          amount: 29.99,
          nextBilling: new Date(Date.now() + 30 * 24 * 60 * 60 * 1000).toISOString()
        }
      });
    });

    await page.goto('/billing/checkout?session_id=cs_test_123');
    
    // Check success message
    await expect(page.locator('text=Payment Successful!')).toBeVisible();
    await expect(page.locator('text=Welcome to your new plan')).toBeVisible();
    
    // Check plan details
    await expect(page.locator('text=Pro Plan')).toBeVisible();
    await expect(page.locator('text=$29.99')).toBeVisible();
    
    // Check action button
    await expect(page.locator('button:has-text("Go to Dashboard")')).toBeVisible();
  });

  test('should show trial information correctly', async ({ page }) => {
    await page.goto('/billing/plans');
    
    // Both plans should show trial info
    await expect(page.locator('text=14-day free trial')).toHaveCount(2);
    
    // Trial button text
    await expect(page.locator('button:has-text("Start 14-Day Free Trial")')).toHaveCount(2);
    
    // Trial disclaimer
    await expect(page.locator('text=No credit card required for trial')).toHaveCount(2);
  });

  test('should display feature comparison table', async ({ page }) => {
    await page.goto('/billing/plans');
    
    // Check feature comparison section
    await expect(page.locator('text=Feature Comparison')).toBeVisible();
    
    // Check table headers
    await expect(page.locator('th:has-text("Basic")')).toBeVisible();
    await expect(page.locator('th:has-text("Pro")')).toBeVisible();
    
    // Check some features
    await expect(page.locator('text=AI Tutoring Sessions')).toBeVisible();
    await expect(page.locator('text=Progress Analytics')).toBeVisible();
    await expect(page.locator('text=Parent Dashboard')).toBeVisible();
  });

  test('should show testimonials and FAQ', async ({ page }) => {
    await page.goto('/billing/plans');
    
    // Check testimonials
    await expect(page.locator('text=math skills improved dramatically')).toBeVisible();
    await expect(page.locator('text=Sarah M., Parent')).toBeVisible();
    
    // Check FAQ toggle
    await page.click('button:has-text("Show FAQ")');
    await expect(page.locator('text=Can I change plans anytime?')).toBeVisible();
    await expect(page.locator('text=What happens during the free trial?')).toBeVisible();
    await expect(page.locator('text=Is there a sibling discount?')).toBeVisible();
  });

  test('should handle payment method updates', async ({ page }) => {
    // Mock payment method update
    await page.route('**/api/billing/payment-method/update', (route) => {
      route.fulfill({
        json: {
          url: 'https://billing.stripe.com/session/123'
        }
      });
    });

    await page.goto('/billing/manage');
    
    // Click update payment method
    await page.click('button:has-text("Update")');
    
    // Should redirect to payment update session
    await expect(page).toHaveURL(/billing\.stripe\.com/);
  });
});
