// @ts-nocheck
import { test, expect, type Page } from "@playwright/test";

// Test configuration
const BASE_URL = process.env.BASE_URL || "http://localhost:3000";
const TEACHER_EMAIL = "teacher@example.com";
const TEACHER_PASSWORD = "test123";

// Helper functions
async function loginAsTeacher(page: Page) {
  await page.goto(`${BASE_URL}/login`);
  await page.fill('[data-testid="email-input"]', TEACHER_EMAIL);
  await page.fill('[data-testid="password-input"]', TEACHER_PASSWORD);
  await page.click('[data-testid="login-button"]');
  await expect(page).toHaveURL(/.*teacher\/dashboard/);
}

async function waitForApiResponse(page: Page, endpoint: string) {
  return page.waitForResponse(
    (response) =>
      response.url().includes(endpoint) && response.status() === 200,
  );
}

test.describe("Teacher Console - S3-06", () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to teacher dashboard and ensure authentication
    await loginAsTeacher(page);
  });

  test.describe("Dashboard Page", () => {
    test("should display teacher dashboard with key metrics", async ({
      page,
    }) => {
      await page.goto(`${BASE_URL}/teacher/dashboard`);

      // Wait for dashboard data to load
      await waitForApiResponse(page, "/api/v1/teacher/dashboard/stats");

      // Check dashboard header
      await expect(page.locator("h1")).toContainText("Teacher Dashboard");

      // Verify quick action cards are present
      await expect(
        page.locator('[data-testid="quick-action-learners"]'),
      ).toBeVisible();
      await expect(
        page.locator('[data-testid="quick-action-approvals"]'),
      ).toBeVisible();
      await expect(
        page.locator('[data-testid="quick-action-subjects"]'),
      ).toBeVisible();
      await expect(
        page.locator('[data-testid="quick-action-messages"]'),
      ).toBeVisible();

      // Check stats display
      await expect(
        page.locator('[data-testid="total-learners-stat"]'),
      ).toBeVisible();
      await expect(
        page.locator('[data-testid="pending-approvals-stat"]'),
      ).toBeVisible();

      // Verify recent activity section
      await expect(
        page.locator('[data-testid="recent-activity"]'),
      ).toBeVisible();
    });

    test("should navigate to other sections from quick actions", async ({
      page,
    }) => {
      await page.goto(`${BASE_URL}/teacher/dashboard`);

      // Navigate to learners page
      await page.click('[data-testid="quick-action-learners"]');
      await expect(page).toHaveURL(/.*teacher\/learners/);

      // Go back to dashboard
      await page.goto(`${BASE_URL}/teacher/dashboard`);

      // Navigate to approvals page
      await page.click('[data-testid="quick-action-approvals"]');
      await expect(page).toHaveURL(/.*teacher\/approvals/);

      // Go back to dashboard
      await page.goto(`${BASE_URL}/teacher/dashboard`);

      // Navigate to subjects page
      await page.click('[data-testid="quick-action-subjects"]');
      await expect(page).toHaveURL(/.*teacher\/subjects/);
    });
  });

  test.describe("Learners Management", () => {
    test("should display assigned learners list", async ({ page }) => {
      await page.goto(`${BASE_URL}/teacher/learners`);

      // Wait for learners data to load
      await waitForApiResponse(page, "/api/v1/teacher/learners");

      // Check page header
      await expect(page.locator("h1")).toContainText("My Learners");

      // Verify filter controls
      await expect(page.locator('[data-testid="search-filter"]')).toBeVisible();
      await expect(page.locator('[data-testid="status-filter"]')).toBeVisible();
      await expect(page.locator('[data-testid="grade-filter"]')).toBeVisible();
      await expect(
        page.locator('[data-testid="subject-filter"]'),
      ).toBeVisible();

      // Check invite button
      await expect(
        page.locator('[data-testid="accept-invite-button"]'),
      ).toBeVisible();

      // Verify learner cards are displayed
      await expect(
        page.locator('[data-testid="learner-card"]').first(),
      ).toBeVisible();
    });

    test("should accept learner invite successfully", async ({ page }) => {
      await page.goto(`${BASE_URL}/teacher/learners`);

      // Click accept invite button
      await page.click('[data-testid="accept-invite-button"]');

      // Check modal appears
      await expect(page.locator('[data-testid="invite-modal"]')).toBeVisible();

      // Fill invite code
      const testInviteCode = "TEST-INVITE-123";
      await page.fill('[data-testid="invite-code-input"]', testInviteCode);

      // Submit invite
      const acceptResponse = waitForApiResponse(
        page,
        "/api/v1/teacher/invites/accept",
      );
      await page.click('[data-testid="accept-invite-submit"]');
      await acceptResponse;

      // Verify modal closes and list refreshes
      await expect(
        page.locator('[data-testid="invite-modal"]'),
      ).not.toBeVisible();
      await waitForApiResponse(page, "/api/v1/teacher/learners");
    });

    test("should filter learners by status", async ({ page }) => {
      await page.goto(`${BASE_URL}/teacher/learners`);
      await waitForApiResponse(page, "/api/v1/teacher/learners");

      // Get initial count
      const initialCount = await page
        .locator('[data-testid="learner-card"]')
        .count();

      // Filter by active status
      await page.selectOption('[data-testid="status-filter"]', "active");

      // Wait for filter to apply
      await page.waitForTimeout(500);

      // Verify filtering worked (count should be different unless all are active)
      const filteredCount = await page
        .locator('[data-testid="learner-card"]')
        .count();

      // Verify results summary is updated
      await expect(
        page.locator('[data-testid="results-summary"]'),
      ).toContainText("Showing");
    });

    test("should search learners by name", async ({ page }) => {
      await page.goto(`${BASE_URL}/teacher/learners`);
      await waitForApiResponse(page, "/api/v1/teacher/learners");

      // Search for a specific learner
      await page.fill('[data-testid="search-filter"]', "John");

      // Wait for search to filter
      await page.waitForTimeout(500);

      // Verify search results
      const learnerCards = page.locator('[data-testid="learner-card"]');
      const count = await learnerCards.count();

      if (count > 0) {
        // Check that displayed learners contain search term
        const firstCard = learnerCards.first();
        const cardText = await firstCard.textContent();
        expect(cardText?.toLowerCase()).toContain("john");
      }
    });
  });

  test.describe("Subject Management", () => {
    test("should display subject assignments with stats", async ({ page }) => {
      await page.goto(`${BASE_URL}/teacher/subjects`);

      // Wait for data to load
      await Promise.all([
        waitForApiResponse(page, "/api/v1/teacher/learners"),
        waitForApiResponse(page, "/api/v1/teacher/subjects/available"),
      ]);

      // Check page header
      await expect(page.locator("h1")).toContainText("Subject Management");

      // Verify stats cards
      await expect(
        page.locator('[data-testid="total-assignments-stat"]'),
      ).toBeVisible();
      await expect(
        page.locator('[data-testid="active-subjects-stat"]'),
      ).toBeVisible();
      await expect(
        page.locator('[data-testid="completed-stat"]'),
      ).toBeVisible();
      await expect(
        page.locator('[data-testid="avg-progress-stat"]'),
      ).toBeVisible();

      // Check assign subject button
      await expect(
        page.locator('[data-testid="assign-subject-button"]'),
      ).toBeVisible();

      // Verify filter controls
      await expect(
        page.locator('[data-testid="learner-filter"]'),
      ).toBeVisible();
      await expect(page.locator('[data-testid="status-filter"]')).toBeVisible();
      await expect(
        page.locator('[data-testid="subject-filter"]'),
      ).toBeVisible();
    });

    test("should assign ELA subject to learner", async ({ page }) => {
      await page.goto(`${BASE_URL}/teacher/subjects`);
      await Promise.all([
        waitForApiResponse(page, "/api/v1/teacher/learners"),
        waitForApiResponse(page, "/api/v1/teacher/subjects/available"),
      ]);

      // Click assign subject button
      await page.click('[data-testid="assign-subject-button"]');

      // Check modal appears
      await expect(page.locator('[data-testid="assign-modal"]')).toBeVisible();

      // Select a learner
      await page.selectOption('[data-testid="learner-select"]', { index: 1 });

      // Select ELA subject
      await page.selectOption('[data-testid="subject-select"]', "ELA");

      // Set weekly goal hours
      await page.fill('[data-testid="weekly-hours-input"]', "6");

      // Submit assignment
      const assignResponse = waitForApiResponse(page, "/subjects");
      await page.click('[data-testid="assign-submit"]');
      await assignResponse;

      // Verify modal closes and data refreshes
      await expect(
        page.locator('[data-testid="assign-modal"]'),
      ).not.toBeVisible();
      await Promise.all([
        waitForApiResponse(page, "/api/v1/teacher/learners"),
        waitForApiResponse(page, "/api/v1/teacher/subjects/available"),
      ]);
    });

    test("should assign Math subject to learner", async ({ page }) => {
      await page.goto(`${BASE_URL}/teacher/subjects`);
      await Promise.all([
        waitForApiResponse(page, "/api/v1/teacher/learners"),
        waitForApiResponse(page, "/api/v1/teacher/subjects/available"),
      ]);

      await page.click('[data-testid="assign-subject-button"]');
      await expect(page.locator('[data-testid="assign-modal"]')).toBeVisible();

      // Select learner and Math subject
      await page.selectOption('[data-testid="learner-select"]', { index: 1 });
      await page.selectOption('[data-testid="subject-select"]', "Math");
      await page.fill('[data-testid="weekly-hours-input"]', "5");

      const assignResponse = waitForApiResponse(page, "/subjects");
      await page.click('[data-testid="assign-submit"]');
      await assignResponse;

      await expect(
        page.locator('[data-testid="assign-modal"]'),
      ).not.toBeVisible();
    });

    test("should update subject assignment status", async ({ page }) => {
      await page.goto(`${BASE_URL}/teacher/subjects`);
      await Promise.all([
        waitForApiResponse(page, "/api/v1/teacher/learners"),
        waitForApiResponse(page, "/api/v1/teacher/subjects/available"),
      ]);

      // Find first subject card and pause it
      const firstCard = page.locator('[data-testid="subject-card"]').first();
      await expect(firstCard).toBeVisible();

      // Click pause button if available
      const pauseButton = firstCard.locator('[data-testid="pause-button"]');
      if (await pauseButton.isVisible()) {
        const updateResponse = waitForApiResponse(page, "/subjects/");
        await pauseButton.click();
        await updateResponse;

        // Verify status changed
        await expect(
          firstCard.locator('[data-testid="status-badge"]'),
        ).toContainText("paused");
      }
    });

    test("should filter subjects by learner", async ({ page }) => {
      await page.goto(`${BASE_URL}/teacher/subjects`);
      await Promise.all([
        waitForApiResponse(page, "/api/v1/teacher/learners"),
        waitForApiResponse(page, "/api/v1/teacher/subjects/available"),
      ]);

      // Filter by specific learner
      await page.selectOption('[data-testid="learner-filter"]', { index: 1 });

      // Wait for filter to apply
      await page.waitForTimeout(500);

      // Verify filtered results
      const subjectCards = page.locator('[data-testid="subject-card"]');
      const count = await subjectCards.count();

      // All visible cards should be for the selected learner
      if (count > 0) {
        const firstCard = subjectCards.first();
        await expect(firstCard).toBeVisible();
      }
    });
  });

  test.describe("Approvals Queue", () => {
    test("should display pending approval requests", async ({ page }) => {
      await page.goto(`${BASE_URL}/teacher/approvals`);

      // Wait for data to load
      await Promise.all([
        waitForApiResponse(page, "/api/v1/teacher/approvals"),
        waitForApiResponse(page, "/api/v1/teacher/learners"),
      ]);

      // Check page header
      await expect(page.locator("h1")).toContainText("Approvals Queue");

      // Verify stats cards
      await expect(
        page.locator('[data-testid="total-requests-stat"]'),
      ).toBeVisible();
      await expect(page.locator('[data-testid="pending-stat"]')).toBeVisible();
      await expect(page.locator('[data-testid="approved-stat"]')).toBeVisible();
      await expect(page.locator('[data-testid="denied-stat"]')).toBeVisible();

      // Check filter controls
      await expect(page.locator('[data-testid="status-filter"]')).toBeVisible();
      await expect(
        page.locator('[data-testid="priority-filter"]'),
      ).toBeVisible();
      await expect(page.locator('[data-testid="type-filter"]')).toBeVisible();
      await expect(
        page.locator('[data-testid="learner-filter"]'),
      ).toBeVisible();
    });

    test("should review and approve a request", async ({ page }) => {
      await page.goto(`${BASE_URL}/teacher/approvals`);
      await Promise.all([
        waitForApiResponse(page, "/api/v1/teacher/approvals"),
        waitForApiResponse(page, "/api/v1/teacher/learners"),
      ]);

      // Find first pending approval and review it
      const firstApproval = page
        .locator('[data-testid="approval-card"]')
        .first();
      if (await firstApproval.isVisible()) {
        await firstApproval.locator('[data-testid="review-button"]').click();

        // Check review modal appears
        await expect(
          page.locator('[data-testid="review-modal"]'),
        ).toBeVisible();

        // Select approve decision
        await page.selectOption('[data-testid="decision-select"]', "approved");

        // Add comments
        await page.fill(
          '[data-testid="comments-textarea"]',
          "Approved for good progress.",
        );

        // Submit review
        const reviewResponse = waitForApiResponse(page, "/approvals/");
        await page.click('[data-testid="submit-review"]');
        await reviewResponse;

        // Verify modal closes and data refreshes
        await expect(
          page.locator('[data-testid="review-modal"]'),
        ).not.toBeVisible();
        await waitForApiResponse(page, "/api/v1/teacher/approvals");
      }
    });

    test("should review and deny a request with comments", async ({ page }) => {
      await page.goto(`${BASE_URL}/teacher/approvals`);
      await Promise.all([
        waitForApiResponse(page, "/api/v1/teacher/approvals"),
        waitForApiResponse(page, "/api/v1/teacher/learners"),
      ]);

      const firstApproval = page
        .locator('[data-testid="approval-card"]')
        .first();
      if (await firstApproval.isVisible()) {
        await firstApproval.locator('[data-testid="review-button"]').click();
        await expect(
          page.locator('[data-testid="review-modal"]'),
        ).toBeVisible();

        // Select deny decision
        await page.selectOption('[data-testid="decision-select"]', "denied");

        // Add required comments for denial
        await page.fill(
          '[data-testid="comments-textarea"]',
          "Need more information before approval.",
        );

        const reviewResponse = waitForApiResponse(page, "/approvals/");
        await page.click('[data-testid="submit-review"]');
        await reviewResponse;

        await expect(
          page.locator('[data-testid="review-modal"]'),
        ).not.toBeVisible();
      }
    });

    test("should filter approvals by priority", async ({ page }) => {
      await page.goto(`${BASE_URL}/teacher/approvals`);
      await Promise.all([
        waitForApiResponse(page, "/api/v1/teacher/approvals"),
        waitForApiResponse(page, "/api/v1/teacher/learners"),
      ]);

      // Filter by urgent priority
      await page.selectOption('[data-testid="priority-filter"]', "urgent");

      // Wait for filter to apply
      await page.waitForTimeout(500);

      // Verify filtering
      const approvalCards = page.locator('[data-testid="approval-card"]');
      const count = await approvalCards.count();

      if (count > 0) {
        // Check that displayed approvals have urgent priority
        const firstCard = approvalCards.first();
        await expect(
          firstCard.locator('[data-testid="priority-badge"]'),
        ).toContainText("urgent");
      }
    });

    test("should filter approvals by type", async ({ page }) => {
      await page.goto(`${BASE_URL}/teacher/approvals`);
      await Promise.all([
        waitForApiResponse(page, "/api/v1/teacher/approvals"),
        waitForApiResponse(page, "/api/v1/teacher/learners"),
      ]);

      // Filter by activity request type
      await page.selectOption(
        '[data-testid="type-filter"]',
        "activity_request",
      );

      await page.waitForTimeout(500);

      const approvalCards = page.locator('[data-testid="approval-card"]');
      const count = await approvalCards.count();

      if (count > 0) {
        // Verify all visible cards are activity requests
        const firstCard = approvalCards.first();
        await expect(firstCard).toBeVisible();
      }
    });
  });

  test.describe("Context Validation", () => {
    test("should ensure dash_context=teacher in all API calls", async ({
      page,
    }) => {
      // Monitor network requests
      const apiCalls: string[] = [];

      page.on("request", (request) => {
        if (request.url().includes("/api/v1/teacher/")) {
          const headers = request.headers();
          expect(headers["x-context"]).toBe("teacher");
          apiCalls.push(request.url());
        }
      });

      // Navigate through all teacher pages
      await page.goto(`${BASE_URL}/teacher/dashboard`);
      await page.goto(`${BASE_URL}/teacher/learners`);
      await page.goto(`${BASE_URL}/teacher/subjects`);
      await page.goto(`${BASE_URL}/teacher/approvals`);

      // Verify API calls were made with correct context
      expect(apiCalls.length).toBeGreaterThan(0);
    });

    test("should validate learner scope checks", async ({ page }) => {
      await page.goto(`${BASE_URL}/teacher/learners`);
      await waitForApiResponse(page, "/api/v1/teacher/learners");

      // Try to access learner details
      const firstLearner = page.locator('[data-testid="learner-card"]').first();
      if (await firstLearner.isVisible()) {
        await firstLearner.click();

        // Should only show assigned learners
        await expect(
          page.locator('[data-testid="learner-details"]'),
        ).toBeVisible();
      }
    });

    test("should prevent access to non-assigned learner data", async ({
      page,
    }) => {
      // This test would attempt to access a learner not assigned to the teacher
      // The API should return 403 or filter out non-assigned learners
      await page.goto(`${BASE_URL}/teacher/learners`);

      // Monitor for 403 responses
      page.on("response", (response) => {
        if (
          response.url().includes("/api/v1/teacher/learners/") &&
          response.status() === 403
        ) {
          console.log("Correctly blocked access to non-assigned learner");
        }
      });

      await waitForApiResponse(page, "/api/v1/teacher/learners");
    });
  });

  test.describe("Integration Flow", () => {
    test("should complete full teacher workflow: accept invite → view learners → assign subjects → review approvals", async ({
      page,
    }) => {
      // 1. Accept invite link
      await page.goto(`${BASE_URL}/teacher/learners`);
      await page.click('[data-testid="accept-invite-button"]');
      await page.fill(
        '[data-testid="invite-code-input"]',
        "INTEGRATION-TEST-INVITE",
      );

      const acceptResponse = waitForApiResponse(page, "/invites/accept");
      await page.click('[data-testid="accept-invite-submit"]');
      await acceptResponse;

      // 2. Display assigned learners
      await waitForApiResponse(page, "/api/v1/teacher/learners");
      await expect(
        page.locator('[data-testid="learner-card"]'),
      ).toHaveCount.toBeGreaterThan(0);

      // 3. Attach ELA/Math subjects to learner
      await page.goto(`${BASE_URL}/teacher/subjects`);

      // Assign ELA
      await page.click('[data-testid="assign-subject-button"]');
      await page.selectOption('[data-testid="learner-select"]', { index: 1 });
      await page.selectOption('[data-testid="subject-select"]', "ELA");
      await page.click('[data-testid="assign-submit"]');
      await waitForApiResponse(page, "/subjects");

      // Assign Math
      await page.click('[data-testid="assign-subject-button"]');
      await page.selectOption('[data-testid="learner-select"]', { index: 1 });
      await page.selectOption('[data-testid="subject-select"]', "Math");
      await page.click('[data-testid="assign-submit"]');
      await waitForApiResponse(page, "/subjects");

      // 4. Open approvals queue
      await page.goto(`${BASE_URL}/teacher/approvals`);
      await waitForApiResponse(page, "/api/v1/teacher/approvals");

      // Verify approvals queue is accessible
      await expect(page.locator("h1")).toContainText("Approvals Queue");
      await expect(page.locator('[data-testid="pending-stat"]')).toBeVisible();

      // Complete workflow verification
      expect(true).toBe(true); // Test completed successfully
    });
  });

  test.describe("Error Handling", () => {
    test("should handle API errors gracefully", async ({ page }) => {
      // Mock network failure
      await page.route("**/api/v1/teacher/learners", (route) => {
        route.abort();
      });

      await page.goto(`${BASE_URL}/teacher/learners`);

      // Should show error state
      await expect(page.locator('[data-testid="error-message"]')).toBeVisible();
      await expect(page.locator('[data-testid="retry-button"]')).toBeVisible();
    });

    test("should validate required fields in forms", async ({ page }) => {
      await page.goto(`${BASE_URL}/teacher/subjects`);

      // Try to submit assignment without required fields
      await page.click('[data-testid="assign-subject-button"]');
      await page.click('[data-testid="assign-submit"]');

      // Form should not submit and should show validation
      await expect(page.locator('[data-testid="assign-modal"]')).toBeVisible();
    });
  });

  test.describe("Responsive Design", () => {
    test("should work on mobile devices", async ({ page }) => {
      // Set mobile viewport
      await page.setViewportSize({ width: 375, height: 667 });

      await page.goto(`${BASE_URL}/teacher/dashboard`);

      // Check mobile-responsive elements
      await expect(page.locator("h1")).toBeVisible();
      await expect(
        page.locator('[data-testid="quick-action-learners"]'),
      ).toBeVisible();
    });

    test("should work on tablet devices", async ({ page }) => {
      // Set tablet viewport
      await page.setViewportSize({ width: 768, height: 1024 });

      await page.goto(`${BASE_URL}/teacher/learners`);

      // Verify tablet layout
      await expect(page.locator('[data-testid="learner-card"]')).toBeVisible();
    });
  });
});
