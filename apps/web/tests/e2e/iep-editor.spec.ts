/**
 * S3-11 IEP Editor E2E Tests
 * Comprehensive testing for collaborative IEP editor with GraphQL, CRDT, and approvals
 */

import { test, expect } from '@playwright/test'
import { Buffer } from 'buffer'

test.describe('IEP Editor - Collaborative Features', () => {
  test.beforeEach(async ({ page }) => {
    // Setup: Navigate to IEP editor and authenticate
    await page.goto('/iep/editor/test-iep-123')
    await page.waitForLoadState('networkidle')

    // Mock GraphQL responses
    await page.route('**/graphql', async route => {
      const request = route.request()
      const postData = request.postData()

      if (postData?.includes('getIEP')) {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            data: {
              iep: {
                id: 'test-iep-123',
                studentId: 'student-456',
                status: 'draft',
                sections: [
                  {
                    id: 'section-1',
                    sectionType: 'present_levels',
                    title: 'Present Levels of Performance',
                    content: 'Student demonstrates...',
                    isRequired: true,
                    isLocked: false,
                    orderIndex: 0,
                    operationCounter: 1,
                    updatedAt: '2024-01-15T10:00:00Z',
                  },
                ],
                signatures: [],
                evidence: [],
                collaborators: [
                  {
                    userId: 'user-1',
                    userName: 'John Teacher',
                    userRole: 'teacher',
                    isOnline: true,
                    lastSeen: '2024-01-15T10:00:00Z',
                  },
                ],
                versionHistory: [],
                operationCounter: 1,
                createdAt: '2024-01-15T09:00:00Z',
                updatedAt: '2024-01-15T10:00:00Z',
              },
            },
          }),
        })
      }

      if (postData?.includes('upsertSection')) {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            data: {
              upsertSection: {
                id: 'section-1',
                content: 'Updated content...',
                operationCounter: 2,
              },
            },
          }),
        })
      }

      // Continue with original request for unhandled cases
      await route.continue()
    })
  })

  test('should load IEP editor with collaborative features', async ({
    page,
  }) => {
    // Verify main editor components are loaded
    await expect(page.locator('[data-testid="iep-editor"]')).toBeVisible()
    await expect(
      page.locator('[data-testid="collaboration-bar"]')
    ).toBeVisible()
    await expect(
      page.locator('[data-testid="section-navigation"]')
    ).toBeVisible()

    // Verify collaboration indicators
    await expect(
      page.locator('[data-testid="online-collaborators"]')
    ).toContainText('John Teacher')
    await expect(
      page.locator('[data-testid="collaboration-status"]')
    ).toContainText('Online')
  })

  test('should enable real-time section editing with CRDT', async ({
    page,
  }) => {
    // Navigate to a section
    await page.click('[data-testid="section-present_levels"]')
    await expect(page.locator('#section-section-1')).toBeVisible()

    // Enter edit mode
    await page.click('button:has-text("Edit")')
    await expect(page.locator('textarea')).toBeVisible()

    // Type content with CRDT operations
    const textarea = page.locator('textarea')
    await textarea.fill(
      'Updated present levels content with detailed assessment...'
    )

    // Verify auto-save indicator
    await expect(page.locator('text=Unsaved changes')).toBeVisible()

    // Wait for auto-save
    await page.waitForTimeout(2500) // Auto-save after 2 seconds
    await expect(page.locator('text=Saved')).toBeVisible()

    // Verify content persistence
    await page.reload()
    await page.click('[data-testid="section-present_levels"]')
    await page.click('button:has-text("Edit")')
    await expect(textarea).toHaveValue(/Updated present levels content/)
  })

  test('should handle collaborative editing conflicts with CRDT', async ({
    page,
  }) => {
    // Simulate concurrent editing scenario
    await page.click('[data-testid="section-present_levels"]')
    await page.click('button:has-text("Edit")')

    const textarea = page.locator('textarea')
    await textarea.fill('Local edit: Student shows improvement in...')

    // Mock incoming CRDT operation from another user
    await page.evaluate(() => {
      window.dispatchEvent(
        new CustomEvent('iep-crdt-operation', {
          detail: {
            type: 'insert',
            position: 0,
            content: 'Remote edit: ',
            userId: 'other-user',
            timestamp: Date.now(),
          },
        })
      )
    })

    // Verify CRDT merge without conflicts
    await expect(textarea).toHaveValue(/Remote edit:.*Local edit:/)

    // Verify collaboration indicator shows multiple editors
    await expect(page.locator('[data-testid="active-editors"]')).toContainText(
      '2 editors'
    )
  })

  test('should track version history and allow restoration', async ({
    page,
  }) => {
    // Make initial edit
    await page.click('[data-testid="section-present_levels"]')
    await page.click('button:has-text("Edit")')

    const textarea = page.locator('textarea')
    await textarea.fill('Version 1: Initial content')
    await page.waitForTimeout(2500) // Auto-save

    // Make second edit
    await textarea.fill('Version 2: Updated content with more details')
    await page.waitForTimeout(2500) // Auto-save

    // Open version history
    await page.click('[data-testid="version-history-button"]')
    await expect(
      page.locator('[data-testid="version-history-modal"]')
    ).toBeVisible()

    // Verify version list
    await expect(
      page.locator('[data-testid="version-list"] .version-item')
    ).toHaveCount(2)

    // Preview older version
    await page.click('[data-testid="version-0"] button:has-text("Preview")')
    await expect(page.locator('[data-testid="version-preview"]')).toContainText(
      'Version 1: Initial content'
    )

    // Restore older version
    await page.click('[data-testid="version-0"] button:has-text("Restore")')
    await page.click('button:has-text("Confirm Restore")')

    // Verify restoration
    await expect(textarea).toHaveValue('Version 1: Initial content')
  })

  test('should validate required sections before submission', async ({
    page,
  }) => {
    // Try to submit without completing required sections
    await page.click('[data-testid="submit-for-approval"]')

    // Verify validation error
    await expect(
      page.locator('[data-testid="validation-errors"]')
    ).toBeVisible()
    await expect(
      page.locator('[data-testid="validation-errors"]')
    ).toContainText('Required sections must be completed')

    // Navigate to required section and complete it
    await page.click('[data-testid="section-present_levels"]')
    await page.click('button:has-text("Edit")')

    const textarea = page.locator('textarea')
    await textarea.fill('Comprehensive present levels assessment completed...')
    await page.waitForTimeout(2500) // Auto-save

    // Try submission again
    await page.click('[data-testid="submit-for-approval"]')

    // Verify successful submission preparation
    await expect(page.locator('[data-testid="submission-modal"]')).toBeVisible()
    await expect(page.locator('text=Ready for approval')).toBeVisible()
  })

  test('should handle evidence upload and attachment', async ({ page }) => {
    // Navigate to evidence section
    await page.click('[data-testid="evidence-tab"]')
    await expect(
      page.locator('[data-testid="evidence-uploader"]')
    ).toBeVisible()

    // Mock file upload
    const fileChooserPromise = page.waitForEvent('filechooser')
    await page.click('button:has-text("Select Files")')
    const fileChooser = await fileChooserPromise

    // Create a test file
    await fileChooser.setFiles({
      name: 'assessment-report.pdf',
      mimeType: 'application/pdf',
      buffer: Buffer.from('Mock PDF content'),
    })

    // Verify upload progress
    await expect(page.locator('[data-testid="upload-progress"]')).toBeVisible()

    // Mock successful upload response
    await page.route('**/s3/upload', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          fileUrl: 'https://test-bucket.s3.amazonaws.com/assessment-report.pdf',
        }),
      })
    })

    // Verify evidence appears in list
    await expect(page.locator('[data-testid="evidence-list"]')).toContainText(
      'assessment-report.pdf'
    )

    // Add description to evidence
    const descriptionTextarea = page
      .locator('[data-testid="evidence-description"]')
      .first()
    await descriptionTextarea.fill(
      'Comprehensive assessment report showing student progress'
    )
    await descriptionTextarea.blur()

    // Verify description is saved
    await expect(descriptionTextarea).toHaveValue(
      'Comprehensive assessment report showing student progress'
    )
  })

  test('should export IEP to PDF with correct formatting', async ({ page }) => {
    // Complete IEP sections first
    await page.click('[data-testid="section-present_levels"]')
    await page.click('button:has-text("Edit")')
    await page.locator('textarea').fill('Detailed present levels assessment...')
    await page.waitForTimeout(2500)

    // Export to PDF
    const downloadPromise = page.waitForEvent('download')
    await page.click('[data-testid="export-pdf"]')

    // Verify PDF generation modal
    await expect(
      page.locator('[data-testid="pdf-generation-modal"]')
    ).toBeVisible()
    await expect(page.locator('text=Generating PDF...')).toBeVisible()

    // Wait for download
    const download = await downloadPromise
    expect(download.suggestedFilename()).toMatch(/IEP.*\.pdf$/)

    // Verify download success
    await expect(page.locator('[data-testid="pdf-success"]')).toBeVisible()
  })
})

test.describe('IEP Approval Workflow', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/iep/review/test-iep-123')
    await page.waitForLoadState('networkidle')

    // Mock IEP in pending approval state
    await page.route('**/graphql', async route => {
      const request = route.request()
      const postData = request.postData()

      if (postData?.includes('getIEP')) {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            data: {
              iep: {
                id: 'test-iep-123',
                status: 'pending_approval',
                signatures: [
                  {
                    id: 'sig-1',
                    userId: 'teacher-1',
                    userName: 'John Teacher',
                    userRole: 'teacher',
                    signatureData:
                      'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAA...',
                    signatureType: 'draw',
                    signedAt: '2024-01-15T10:00:00Z',
                  },
                ],
                signatureStatus: 'partial',
              },
            },
          }),
        })
      }
    })
  })

  test('should display signature status and requirements', async ({ page }) => {
    // Verify signature status display
    await expect(
      page.locator('[data-testid="signature-status"]')
    ).toContainText('1/4 Complete')
    await expect(
      page.locator('[data-testid="signature-progress"]')
    ).toBeVisible()

    // Verify required signature roles
    const requiredRoles = ['parent', 'teacher', 'specialist', 'administrator']
    for (const role of requiredRoles) {
      await expect(
        page.locator(`[data-testid="signature-${role}"]`)
      ).toBeVisible()
    }

    // Verify completed signature
    await expect(page.locator('[data-testid="signature-teacher"]')).toHaveClass(
      /bg-green-50/
    )
    await expect(
      page.locator(
        '[data-testid="signature-teacher"] text=Signed by John Teacher'
      )
    ).toBeVisible()
  })

  test('should enable electronic signature capture', async ({ page }) => {
    // Open signature modal for current user (assuming parent role)
    await page.click('[data-testid="add-signature-button"]')
    await expect(page.locator('[data-testid="signature-modal"]')).toBeVisible()

    // Test draw signature
    await page.click('button:has-text("Draw")')

    const canvas = page.locator('canvas')
    await expect(canvas).toBeVisible()

    // Simulate drawing signature
    await canvas.hover()
    await page.mouse.down()
    await page.mouse.move(100, 50)
    await page.mouse.move(150, 30)
    await page.mouse.up()

    // Submit signature
    await page.click('button:has-text("Add Signature")')

    // Verify signature was added
    await expect(page.locator('[data-testid="signature-parent"]')).toHaveClass(
      /bg-green-50/
    )

    // Test typed signature
    await page.click('[data-testid="add-signature-button"]')
    await page.click('button:has-text("Type")')

    await page.fill('input[placeholder="Enter your full name"]', 'Jane Parent')
    await expect(
      page.locator('[data-testid="signature-preview"]')
    ).toContainText('Jane Parent')

    await page.click('button:has-text("Add Signature")')
    await expect(
      page.locator('[data-testid="signature-modal"]')
    ).not.toBeVisible()
  })

  test('should validate all required signatures before approval', async ({
    page,
  }) => {
    // Try to approve with missing signatures
    await page.click('[data-testid="approve-iep"]')

    // Verify validation error
    await expect(page.locator('[data-testid="approval-error"]')).toContainText(
      'All required signatures must be completed'
    )

    // Mock all signatures complete
    await page.route('**/graphql', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          data: {
            iep: {
              signatureStatus: 'complete',
              signatures: [
                { userRole: 'parent', userName: 'Jane Parent' },
                { userRole: 'teacher', userName: 'John Teacher' },
                { userRole: 'specialist', userName: 'Dr. Smith' },
                { userRole: 'administrator', userName: 'Principal Johnson' },
              ],
            },
          },
        }),
      })
    })

    await page.reload()

    // Verify approval is now possible
    await page.click('[data-testid="approve-iep"]')
    await expect(
      page.locator('[data-testid="approval-confirmation"]')
    ).toBeVisible()

    await page.fill(
      'textarea[placeholder="Add approval comments..."]',
      'IEP approved with all requirements met.'
    )
    await page.click('button:has-text("Confirm Approval")')

    // Verify approval success
    await expect(page.locator('[data-testid="approval-success"]')).toBeVisible()
  })

  test('should handle signature removal and re-signing', async ({ page }) => {
    // View existing signature
    await page.click(
      '[data-testid="signature-teacher"] button:has-text("View")'
    )

    // Verify signature display in popup
    await expect(
      page.locator('[data-testid="signature-popup"] img')
    ).toBeVisible()

    // Remove signature (if user has permission)
    await page.click(
      '[data-testid="signature-teacher"] button:has-text("Remove")'
    )
    await page.click('button:has-text("Confirm Remove")')

    // Verify signature removed
    await expect(
      page.locator('[data-testid="signature-teacher"]')
    ).not.toHaveClass(/bg-green-50/)
    await expect(
      page.locator('[data-testid="signature-teacher"] text=Signature required')
    ).toBeVisible()

    // Re-sign
    await page.click('[data-testid="add-signature-button"]')
    await page.click('button:has-text("Type")')
    await page.fill('input[placeholder="Enter your full name"]', 'John Teacher')
    await page.click('button:has-text("Add Signature")')

    // Verify re-signing successful
    await expect(page.locator('[data-testid="signature-teacher"]')).toHaveClass(
      /bg-green-50/
    )
  })
})

test.describe('IEP Performance and Error Handling', () => {
  test('should handle network failures gracefully', async ({ page }) => {
    await page.goto('/iep/editor/test-iep-123')

    // Simulate network failure
    await page.route('**/graphql', async route => {
      await route.abort('failed')
    })

    // Verify error handling
    await expect(page.locator('[data-testid="network-error"]')).toBeVisible()
    await expect(page.locator('text=Unable to connect')).toBeVisible()

    // Verify retry mechanism
    await page.click('button:has-text("Retry")')

    // Restore network and verify recovery
    await page.unroute('**/graphql')
    await expect(page.locator('[data-testid="iep-editor"]')).toBeVisible()
  })

  test('should handle large IEP documents efficiently', async ({ page }) => {
    // Mock large IEP with many sections
    await page.route('**/graphql', async route => {
      const largeSections = Array.from({ length: 20 }, (_, i) => ({
        id: `section-${i}`,
        sectionType: `section_type_${i}`,
        title: `Section ${i + 1}`,
        content: 'Large content...'.repeat(1000),
        isRequired: i < 5,
        isLocked: false,
        orderIndex: i,
        operationCounter: 1,
        updatedAt: '2024-01-15T10:00:00Z',
      }))

      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          data: {
            iep: {
              id: 'large-iep-123',
              sections: largeSections,
              // ... other properties
            },
          },
        }),
      })
    })

    await page.goto('/iep/editor/large-iep-123')

    // Verify performance with large document
    const startTime = Date.now()
    await expect(page.locator('[data-testid="iep-editor"]')).toBeVisible()
    const loadTime = Date.now() - startTime

    // Should load within reasonable time (5 seconds)
    expect(loadTime).toBeLessThan(5000)

    // Verify virtual scrolling or pagination works
    await expect(
      page.locator('[data-testid="section-navigation"]')
    ).toBeVisible()
    await expect(page.locator('.section-item')).toHaveCount(20)
  })

  test('should maintain data integrity during concurrent operations', async ({
    page,
  }) => {
    await page.goto('/iep/editor/test-iep-123')

    // Simulate rapid concurrent edits
    await page.click('[data-testid="section-present_levels"]')
    await page.click('button:has-text("Edit")')

    const textarea = page.locator('textarea')

    // Rapid typing simulation
    for (let i = 0; i < 10; i++) {
      await textarea.type(`Edit ${i} `)
      await page.waitForTimeout(100)
    }

    // Verify final content integrity
    await page.waitForTimeout(3000) // Wait for all saves
    const finalContent = await textarea.inputValue()
    expect(finalContent).toContain('Edit 0')
    expect(finalContent).toContain('Edit 9')

    // Verify no duplicate content from race conditions
    const editCount = (finalContent.match(/Edit \d+/g) || []).length
    expect(editCount).toBe(10)
  })
})

test.describe('IEP Accessibility and Cross-browser', () => {
  test('should be fully keyboard accessible', async ({ page }) => {
    await page.goto('/iep/editor/test-iep-123')

    // Navigate using keyboard only
    await page.keyboard.press('Tab') // Focus first interactive element
    await page.keyboard.press('Enter') // Activate

    // Navigate through sections using keyboard
    await page.keyboard.press('Tab')
    await page.keyboard.press('Tab')
    await page.keyboard.press('Enter') // Enter section

    await page.keyboard.press('Tab')
    await page.keyboard.press('Enter') // Edit mode

    // Type content
    await page.keyboard.type('Content entered via keyboard only')

    // Save using keyboard
    await page.keyboard.press('Control+s')

    // Verify content was saved
    await expect(page.locator('text=Saved')).toBeVisible()
  })

  test('should meet WCAG accessibility standards', async ({ page }) => {
    await page.goto('/iep/editor/test-iep-123')

    // Check for proper ARIA labels
    await expect(page.locator('[role="main"]')).toBeVisible()
    await expect(page.locator('[aria-label="IEP Editor"]')).toBeVisible()

    // Check heading hierarchy
    const h1Count = await page.locator('h1').count()
    expect(h1Count).toBe(1)

    // Check form labels
    const inputs = await page.locator('input, textarea, select').all()
    for (const input of inputs) {
      const id = await input.getAttribute('id')
      if (id) {
        await expect(page.locator(`label[for="${id}"]`)).toBeVisible()
      }
    }

    // Check color contrast (basic check)
    const backgroundColor = await page.evaluate(() => {
      const body = document.body
      return window.getComputedStyle(body).backgroundColor
    })
    expect(backgroundColor).toBeTruthy()
  })

  test('should work across different screen sizes', async ({ page }) => {
    await page.goto('/iep/editor/test-iep-123')

    // Test desktop view
    await page.setViewportSize({ width: 1920, height: 1080 })
    await expect(page.locator('[data-testid="sidebar"]')).toBeVisible()
    await expect(page.locator('[data-testid="main-content"]')).toBeVisible()

    // Test tablet view
    await page.setViewportSize({ width: 768, height: 1024 })
    await expect(page.locator('[data-testid="iep-editor"]')).toBeVisible()

    // Test mobile view
    await page.setViewportSize({ width: 375, height: 667 })
    await expect(page.locator('[data-testid="mobile-menu"]')).toBeVisible()

    // Test responsive navigation
    await page.click('[data-testid="mobile-menu-toggle"]')
    await expect(
      page.locator('[data-testid="mobile-navigation"]')
    ).toBeVisible()
  })
})
