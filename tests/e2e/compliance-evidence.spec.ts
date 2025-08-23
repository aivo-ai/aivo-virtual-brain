/**
 * S5-09 Compliance Evidence Dashboard E2E Tests
 *
 * Tests for tenant and learner compliance evidence visualization,
 * isolation test results, consent timeline, audit events, and
 * data protection request tracking.
 */

import { test, expect } from "@playwright/test";

test.describe("S5-09 Compliance Evidence Dashboard", () => {
  test.beforeEach(async ({ page }) => {
    // Mock authentication
    await page.addInitScript(() => {
      localStorage.setItem("auth_token", "mock-admin-token");
      localStorage.setItem("user_role", "district_admin");
    });

    // Mock compliance service API responses
    await page.route(
      "**/api/compliance-svc/evidence/tenant/*",
      async (route) => {
        const url = route.request().url();
        const tenantId = url.split("/tenant/")[1].split("?")[0];

        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            tenant_id: tenantId,
            isolation_tests: [
              {
                test_type: "data_isolation",
                total_tests: 100,
                passed_tests: 98,
                failed_tests: 2,
                pass_rate: 0.98,
                last_test_date: "2024-01-15T10:00:00Z",
                average_duration: 45.5,
              },
              {
                test_type: "network_isolation",
                total_tests: 50,
                passed_tests: 47,
                failed_tests: 3,
                pass_rate: 0.94,
                last_test_date: "2024-01-15T09:30:00Z",
                average_duration: 12.3,
              },
            ],
            chaos_checks: {
              tenant_isolation: {
                total: 25,
                passed: 23,
                failed: 2,
                last_run: "2024-01-15T08:00:00Z",
              },
              data_corruption: {
                total: 15,
                passed: 15,
                failed: 0,
                last_run: "2024-01-15T07:00:00Z",
              },
            },
            retention_job_status: {
              last_retention_run: "2024-01-14T23:00:00Z",
              next_scheduled_run: "2024-01-15T23:00:00Z",
              items_processed: 10000,
              items_deleted: 250,
              items_archived: 500,
              status: "completed",
              compliance_policies: {
                user_data: "7 years",
                assessment_data: "10 years",
                audit_logs: "7 years",
              },
            },
            last_updated: "2024-01-15T10:30:00Z",
            overall_isolation_pass_rate: 0.966,
            total_isolation_tests: 150,
            failed_isolation_tests: 5,
            retention_compliance_score: 0.98,
          }),
        });
      },
    );

    await page.route(
      "**/api/compliance-svc/evidence/learner/*",
      async (route) => {
        const url = route.request().url();
        const learnerId = url.split("/learner/")[1].split("?")[0];

        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            learner_id: learnerId,
            consent_records: [
              {
                id: "consent-1",
                purpose: "Educational Analytics",
                granted_at: "2024-01-01T10:00:00Z",
                status: "granted",
                consent_type: "explicit",
                legal_basis: "consent",
                version: "2.1",
                expiry_date: "2025-01-01T10:00:00Z",
              },
              {
                id: "consent-2",
                purpose: "Performance Tracking",
                granted_at: "2024-01-05T14:00:00Z",
                revoked_at: "2024-01-10T16:00:00Z",
                status: "revoked",
                consent_type: "explicit",
                legal_basis: "consent",
                version: "2.1",
              },
            ],
            data_protection_requests: [
              {
                id: "request-1",
                request_type: "data_export",
                status: "completed",
                created_at: "2024-01-12T09:00:00Z",
                completed_at: "2024-01-12T09:30:00Z",
                data_categories: ["user_profile", "assessment_data"],
                retention_policy: "standard_7_years",
                compliance_status: "compliant",
              },
            ],
            audit_events: [
              {
                id: "audit-1",
                timestamp: "2024-01-15T10:00:00Z",
                event_type: "data_access",
                action: "view_profile",
                resource: "learner_profile",
                actor: "teacher@school.edu",
                outcome: "success",
                details: { ip_address: "192.168.1.100" },
                risk_level: "low",
              },
            ],
            last_updated: "2024-01-15T10:30:00Z",
            active_consents: 1,
            revoked_consents: 1,
            pending_requests: 0,
            completed_requests: 1,
            compliance_score: 0.95,
            data_categories_processed: [
              "user_profile",
              "assessment_data",
              "learning_analytics",
            ],
            retention_status: {
              user_profile: "active",
              assessment_data: "active",
              learning_analytics: "active",
            },
          }),
        });
      },
    );
  });

  test("should display tenant compliance evidence dashboard", async ({
    page,
  }) => {
    await page.goto("/compliance/tenant/tenant-123");

    // Wait for page to load
    await page.waitForSelector('[data-testid="tenant-evidence-page"]', {
      timeout: 10000,
    });

    // Check page title
    await expect(page.locator("h4")).toContainText(
      "Tenant Compliance Evidence",
    );

    // Check summary cards
    await expect(
      page.locator('[data-testid="isolation-pass-rate-card"]'),
    ).toContainText("97%");
    await expect(
      page.locator('[data-testid="failed-tests-card"]'),
    ).toContainText("5");
    await expect(
      page.locator('[data-testid="retention-compliance-card"]'),
    ).toContainText("98%");

    // Check isolation tests table
    await expect(page.locator("table")).toBeVisible();
    await expect(page.locator("table tbody tr")).toHaveCount(2);
    await expect(page.locator("table tbody tr").first()).toContainText(
      "Data Isolation",
    );
    await expect(page.locator("table tbody tr").first()).toContainText("98%");

    // Check chaos engineering checks
    await expect(
      page.locator('[data-testid="chaos-checks-section"]'),
    ).toBeVisible();
    await expect(
      page.locator('[data-testid="chaos-checks-section"]'),
    ).toContainText("Tenant Isolation");
    await expect(
      page.locator('[data-testid="chaos-checks-section"]'),
    ).toContainText("Data Corruption");
  });

  test("should display learner compliance evidence dashboard", async ({
    page,
  }) => {
    await page.goto("/compliance/learner/learner-456");

    // Wait for page to load
    await page.waitForSelector('[data-testid="learner-evidence-page"]', {
      timeout: 10000,
    });

    // Check page title
    await expect(page.locator("h4")).toContainText(
      "Learner Compliance Evidence",
    );

    // Check summary cards
    await expect(
      page.locator('[data-testid="compliance-score-card"]'),
    ).toContainText("95%");
    await expect(
      page.locator('[data-testid="active-consents-card"]'),
    ).toContainText("1");
    await expect(
      page.locator('[data-testid="dp-requests-card"]'),
    ).toContainText("1");

    // Check tabs are present
    await expect(page.locator('[role="tab"]')).toHaveCount(4);
    await expect(page.locator('[role="tab"]').first()).toContainText(
      "Consent Timeline",
    );
    await expect(page.locator('[role="tab"]').nth(1)).toContainText(
      "Data Protection Requests",
    );
    await expect(page.locator('[role="tab"]').nth(2)).toContainText(
      "Audit Events",
    );
    await expect(page.locator('[role="tab"]').nth(3)).toContainText(
      "Retention Status",
    );
  });

  test("should navigate through learner evidence tabs", async ({ page }) => {
    await page.goto("/compliance/learner/learner-456");
    await page.waitForSelector('[data-testid="learner-evidence-page"]');

    // Default tab (Consent Timeline)
    await expect(
      page.locator('[data-testid="consent-timeline"]'),
    ).toBeVisible();
    await expect(
      page.locator('[data-testid="consent-timeline"]'),
    ).toContainText("Educational Analytics");
    await expect(
      page.locator('[data-testid="consent-timeline"]'),
    ).toContainText("Performance Tracking");

    // Click Data Protection Requests tab
    await page.click('[role="tab"]:has-text("Data Protection Requests")');
    await expect(
      page.locator('[data-testid="dp-requests-section"]'),
    ).toBeVisible();
    await expect(
      page.locator('[data-testid="dp-requests-section"]'),
    ).toContainText("Data Export");

    // Click Audit Events tab
    await page.click('[role="tab"]:has-text("Audit Events")');
    await expect(page.locator('[data-testid="audit-table"]')).toBeVisible();
    await expect(page.locator("table tbody tr")).toHaveCount(1);
    await expect(page.locator("table")).toContainText("view_profile");

    // Click Retention Status tab
    await page.click('[role="tab"]:has-text("Retention Status")');
    await expect(
      page.locator('[data-testid="retention-status"]'),
    ).toBeVisible();
    await expect(
      page.locator('[data-testid="retention-status"]'),
    ).toContainText("User Profile");
    await expect(
      page.locator('[data-testid="retention-status"]'),
    ).toContainText("Assessment Data");
  });

  test("should expand and view test details in tenant dashboard", async ({
    page,
  }) => {
    await page.goto("/compliance/tenant/tenant-123");
    await page.waitForSelector("table");

    // Click view details button for first test
    await page.click(
      'table tbody tr:first-child button[aria-label="View Details"]',
    );

    // Check modal opened
    await expect(page.locator('[role="dialog"]')).toBeVisible();
    await expect(page.locator('[role="dialog"]')).toContainText(
      "Isolation Test Details",
    );
    await expect(page.locator('[role="dialog"]')).toContainText(
      "Data Isolation",
    );
    await expect(page.locator('[role="dialog"]')).toContainText(
      "Total Tests: 100",
    );
    await expect(page.locator('[role="dialog"]')).toContainText("Passed: 98");
    await expect(page.locator('[role="dialog"]')).toContainText("Failed: 2");

    // Close modal
    await page.click('[role="dialog"] button:has-text("Close")');
    await expect(page.locator('[role="dialog"]')).not.toBeVisible();
  });

  test("should filter audit events in learner dashboard", async ({ page }) => {
    await page.goto("/compliance/learner/learner-456");
    await page.waitForSelector('[data-testid="learner-evidence-page"]');

    // Navigate to audit events tab
    await page.click('[role="tab"]:has-text("Audit Events")');
    await expect(page.locator('[data-testid="audit-table"]')).toBeVisible();

    // Open filters
    await page.click('[data-testid="filter-button"]');
    await expect(page.locator('[data-testid="audit-filters"]')).toBeVisible();

    // Test search filter
    await page.fill('[data-testid="search-filter"]', "view_profile");
    await expect(page.locator("table tbody tr")).toHaveCount(1);

    // Clear search
    await page.fill('[data-testid="search-filter"]', "");

    // Test event type filter
    await page.click('[data-testid="event-type-filter"]');
    await page.click('[role="option"]:has-text("Data Access")');
    await expect(page.locator("table tbody tr")).toHaveCount(1);

    // Clear filters
    await page.click('button:has-text("Clear Filters")');
    await expect(page.locator('[data-testid="search-filter"]')).toHaveValue("");
  });

  test("should export compliance reports", async ({ page }) => {
    // Test tenant export
    await page.goto("/compliance/tenant/tenant-123");
    await page.waitForSelector('[data-testid="tenant-evidence-page"]');

    // Mock download
    const downloadPromise = page.waitForEvent("download");
    await page.click('button:has-text("Export Report")');
    const download = await downloadPromise;
    expect(download.suggestedFilename()).toContain("tenant");

    // Test learner export
    await page.goto("/compliance/learner/learner-456");
    await page.waitForSelector('[data-testid="learner-evidence-page"]');

    const learnerDownloadPromise = page.waitForEvent("download");
    await page.click('button:has-text("Export Report")');
    const learnerDownload = await learnerDownloadPromise;
    expect(learnerDownload.suggestedFilename()).toContain("learner");
  });

  test("should refresh compliance data", async ({ page }) => {
    await page.goto("/compliance/tenant/tenant-123");
    await page.waitForSelector('[data-testid="tenant-evidence-page"]');

    // Click refresh button
    await page.click('button:has-text("Refresh")');

    // Should show refreshing state
    await expect(page.locator("button")).toContainText("Refreshing...");

    // Should return to normal state
    await expect(page.locator('button:has-text("Refresh")')).toBeVisible();
  });

  test("should handle empty compliance data", async ({ page }) => {
    // Mock empty response
    await page.route(
      "**/api/compliance-svc/evidence/tenant/*",
      async (route) => {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            tenant_id: "empty-tenant",
            isolation_tests: [],
            chaos_checks: {},
            retention_job_status: {
              last_retention_run: "2024-01-15T10:00:00Z",
              next_scheduled_run: "2024-01-16T10:00:00Z",
              items_processed: 0,
              items_deleted: 0,
              items_archived: 0,
              status: "pending",
              compliance_policies: {},
            },
            last_updated: "2024-01-15T10:30:00Z",
            overall_isolation_pass_rate: 0,
            total_isolation_tests: 0,
            failed_isolation_tests: 0,
            retention_compliance_score: 0,
          }),
        });
      },
    );

    await page.goto("/compliance/tenant/empty-tenant");
    await page.waitForSelector('[data-testid="tenant-evidence-page"]');

    // Should show empty state message
    await expect(page.locator('[role="alert"]')).toContainText(
      "No isolation tests found",
    );
  });

  test("should handle API errors gracefully", async ({ page }) => {
    // Mock error response
    await page.route(
      "**/api/compliance-svc/evidence/tenant/*",
      async (route) => {
        await route.fulfill({
          status: 500,
          contentType: "application/json",
          body: JSON.stringify({ error: "Internal server error" }),
        });
      },
    );

    await page.goto("/compliance/tenant/error-tenant");

    // Should show error message
    await expect(page.locator('[role="alert"]')).toContainText(
      "Failed to load evidence",
    );

    // Should show retry button
    await expect(page.locator('button:has-text("Try Again")')).toBeVisible();
  });

  test("should display risk levels with appropriate styling", async ({
    page,
  }) => {
    await page.goto("/compliance/learner/learner-456");
    await page.waitForSelector('[data-testid="learner-evidence-page"]');

    // Navigate to audit events
    await page.click('[role="tab"]:has-text("Audit Events")');
    await page.waitForSelector('[data-testid="audit-table"]');

    // Check risk level chip
    const riskChip = page.locator('[data-testid="risk-level-chip"]').first();
    await expect(riskChip).toContainText("Low");
    await expect(riskChip).toHaveClass(/success/); // Should have success color for low risk
  });

  test("should show consent timeline with proper status indicators", async ({
    page,
  }) => {
    await page.goto("/compliance/learner/learner-456");
    await page.waitForSelector('[data-testid="learner-evidence-page"]');

    // Check consent timeline items
    const timelineItems = page.locator('[data-testid="consent-timeline-item"]');
    await expect(timelineItems).toHaveCount(2);

    // Check first consent (granted)
    await expect(timelineItems.first()).toContainText("Educational Analytics");
    await expect(timelineItems.first()).toContainText("GRANTED");

    // Check second consent (revoked)
    await expect(timelineItems.nth(1)).toContainText("Performance Tracking");
    await expect(timelineItems.nth(1)).toContainText("REVOKED");
  });

  test("should validate progress bars and metrics display", async ({
    page,
  }) => {
    await page.goto("/compliance/tenant/tenant-123");
    await page.waitForSelector('[data-testid="tenant-evidence-page"]');

    // Check isolation pass rate progress bar
    const progressBar = page.locator(
      '[data-testid="isolation-pass-rate-progress"]',
    );
    await expect(progressBar).toBeVisible();
    await expect(progressBar).toHaveAttribute("aria-valuenow", "97");

    // Check retention compliance progress
    const retentionProgress = page.locator(
      '[data-testid="retention-compliance-progress"]',
    );
    await expect(retentionProgress).toBeVisible();
    await expect(retentionProgress).toHaveAttribute("aria-valuenow", "98");
  });
});
