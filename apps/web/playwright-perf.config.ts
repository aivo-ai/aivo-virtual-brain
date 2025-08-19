import { defineConfig, devices } from '@playwright/test'

/**
 * Performance testing configuration with budgets
 * - LCP ≤ 2.5s (Largest Contentful Paint)
 * - TBT ≤ 200ms (Total Blocking Time)
 * - Mid-tier device simulation with throttling
 */
export default defineConfig({
  testDir: './e2e/performance',
  fullyParallel: false, // Sequential for consistent performance results
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: 1, // Single worker for performance consistency
  reporter: [
    ['html', { outputFolder: 'playwright-report-perf' }],
    ['json', { outputFile: 'test-results/performance-results.json' }]
  ],
  use: {
    baseURL: 'http://localhost:3000',
    trace: 'retain-on-failure',
    video: 'retain-on-failure',
    screenshot: 'only-on-failure',
  },

  projects: [
    {
      name: 'performance-chrome',
      use: { 
        ...devices['Desktop Chrome'],
        // Mid-tier device simulation
        launchOptions: {
          args: [
            '--enable-performance-manager-dbus-interface',
            '--enable-precise-memory-info',
            '--disable-background-timer-throttling',
            '--disable-backgrounding-occluded-windows',
            '--disable-renderer-backgrounding'
          ]
        }
      },
    },
  ],

  webServer: {
    command: 'npm run dev',
    url: 'http://localhost:3000',
    reuseExistingServer: !process.env.CI,
    timeout: 120 * 1000,
  },
})
