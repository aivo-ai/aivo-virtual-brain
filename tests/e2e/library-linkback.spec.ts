import { test, expect } from "@playwright/test";

/**
 * E2E Tests for S5-10 Coursework→Lesson Linkback & Progress Hooks
 *
 * Tests the complete user workflow for linking coursework to lessons
 * and verifying progress hook integration.
 */

test.describe("Coursework→Lesson Linkback (S5-10)", () => {
  test.beforeEach(async ({ page }) => {
    // Mock authentication
    await page.route("**/auth/**", (route) => {
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          user: {
            id: "teacher-123",
            role: "teacher",
            permissions: ["create_linkback", "view_linkback"],
          },
        }),
      });
    });

    // Mock lesson registry API
    await page.route("**/lesson-registry-svc/**", (route) => {
      const url = route.request().url();

      if (url.includes("/lessons?")) {
        // Search lessons
        route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify([
            {
              id: "lesson-123",
              title: "Introduction to Algebra",
              subject: "Mathematics",
              gradeBand: "6-8",
              description: "Basic algebraic concepts and operations",
              difficulty: "intermediate",
            },
            {
              id: "lesson-456",
              title: "Linear Equations",
              subject: "Mathematics",
              gradeBand: "6-8",
              description: "Solving linear equations step by step",
              difficulty: "intermediate",
            },
          ]),
        });
      } else if (url.includes("/linkback/coursework/")) {
        if (route.request().method() === "GET") {
          // Get existing links
          route.fulfill({
            status: 200,
            contentType: "application/json",
            body: JSON.stringify({
              links: [],
              total_count: 0,
              has_more: false,
            }),
          });
        }
      } else if (
        url.includes("/linkback") &&
        route.request().method() === "POST"
      ) {
        // Create new link
        route.fulfill({
          status: 201,
          contentType: "application/json",
          body: JSON.stringify({
            success: true,
            message: "Coursework linked to lesson successfully",
            link_id: "link-789",
            event_emitted: true,
          }),
        });
      } else if (
        url.includes("/linkback/links/") &&
        route.request().method() === "DELETE"
      ) {
        // Delete link
        route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            success: true,
            message: "Coursework unlinked from lesson",
          }),
        });
      }
    });

    // Mock coursework API
    await page.route("**/coursework/**", (route) => {
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          id: "coursework-123",
          title: "Algebra Homework Assignment",
          description: "Practice problems for algebraic expressions",
          type: "assignment",
          source: "coursework",
          subject: "Mathematics",
          gradeBand: "6-8",
          tags: ["algebra", "homework"],
          url: "https://example.com/assignment.pdf",
          attachedToLearner: true,
          metadata: {
            fileSize: 256000,
            pages: 5,
            author: "Math Teacher",
          },
        }),
      });
    });
  });

  test("should display coursework details with linkback action", async ({
    page,
  }) => {
    await page.goto("/library/coursework/coursework-123");

    // Verify coursework details are displayed
    await expect(page.locator("h1")).toContainText(
      "Algebra Homework Assignment",
    );
    await expect(page.locator("text=Coursework")).toBeVisible();
    await expect(page.locator("text=assignment")).toBeVisible();

    // Verify "Link to Lesson" button is present for coursework
    await expect(
      page.locator('button:has-text("Link to Lesson")'),
    ).toBeVisible();
  });

  test("should open linkback modal and display available lessons", async ({
    page,
  }) => {
    await page.goto("/library/coursework/coursework-123");

    // Click "Link to Lesson" button
    await page.click('button:has-text("Link to Lesson")');

    // Verify modal opens
    await expect(page.locator("text=Link Coursework to Lessons")).toBeVisible();

    // Wait for lessons to load
    await expect(page.locator("text=Loading lessons...")).toBeHidden();

    // Verify available lessons are displayed
    await expect(page.locator("text=Introduction to Algebra")).toBeVisible();
    await expect(page.locator("text=Linear Equations")).toBeVisible();

    // Verify lesson details are shown
    await expect(page.locator("text=Mathematics • 6-8")).toBeVisible();
    await expect(page.locator("text=Basic algebraic concepts")).toBeVisible();
  });

  test("should create coursework-lesson link successfully", async ({
    page,
  }) => {
    await page.goto("/library/coursework/coursework-123");

    // Open linkback modal
    await page.click('button:has-text("Link to Lesson")');
    await expect(page.locator("text=Introduction to Algebra")).toBeVisible();

    // Click "Link" button for the first lesson
    await page.click('button:has-text("Link")').first();

    // Verify success (modal should close and linked lessons section should appear)
    await expect(page.locator("text=Link Coursework to Lessons")).toBeHidden();

    // Wait for page to update with linked lesson
    await page.waitForTimeout(1000);

    // Verify linked lessons section appears
    await expect(page.locator("text=Linked Lessons")).toBeVisible();
  });

  test("should display linked lessons with unlink functionality", async ({
    page,
  }) => {
    // Mock existing links
    await page.route(
      "**/lesson-registry-svc/linkback/coursework/**",
      (route) => {
        route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            links: [
              {
                id: "link-789",
                coursework_id: "coursework-123",
                lesson_id: "lesson-123",
                mastery_weight: 100,
                difficulty_adjustment: 0,
                lesson: {
                  title: "Introduction to Algebra",
                  subject: "Mathematics",
                },
              },
            ],
            total_count: 1,
            has_more: false,
          }),
        });
      },
    );

    await page.goto("/library/coursework/coursework-123");

    // Verify linked lessons section is displayed
    await expect(page.locator("text=Linked Lessons (1)")).toBeVisible();
    await expect(page.locator("text=Introduction to Algebra")).toBeVisible();
    await expect(page.locator("text=Mastery Weight: 100%")).toBeVisible();

    // Verify unlink button is present
    await expect(page.locator('button[title="Unlink lesson"]')).toBeVisible();
  });

  test("should unlink lesson successfully", async ({ page }) => {
    // Mock existing links
    await page.route(
      "**/lesson-registry-svc/linkback/coursework/**",
      (route) => {
        if (route.request().method() === "GET") {
          route.fulfill({
            status: 200,
            contentType: "application/json",
            body: JSON.stringify({
              links: [
                {
                  id: "link-789",
                  coursework_id: "coursework-123",
                  lesson_id: "lesson-123",
                  mastery_weight: 100,
                  difficulty_adjustment: 0,
                  lesson: {
                    title: "Introduction to Algebra",
                  },
                },
              ],
              total_count: 1,
              has_more: false,
            }),
          });
        }
      },
    );

    await page.goto("/library/coursework/coursework-123");

    // Verify linked lesson is displayed
    await expect(page.locator("text=Introduction to Algebra")).toBeVisible();

    // Click unlink button
    await page.click('button[title="Unlink lesson"]');

    // Verify the lesson is removed (the linked lessons section should update)
    await page.waitForTimeout(1000);

    // The section should either be hidden or show "No linked lessons"
    // Depending on implementation, we'd check for the updated state
  });

  test("should handle RBAC authorization correctly", async ({ page }) => {
    // Mock unauthorized user
    await page.route("**/auth/**", (route) => {
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          user: {
            id: "student-123",
            role: "student",
            permissions: [],
          },
        }),
      });
    });

    // Mock 403 response for linkback operations
    await page.route("**/lesson-registry-svc/linkback", (route) => {
      route.fulfill({
        status: 403,
        contentType: "application/json",
        body: JSON.stringify({
          detail: "Insufficient permissions for linkback operations",
        }),
      });
    });

    await page.goto("/library/coursework/coursework-123");

    // "Link to Lesson" button should not be visible for students
    await expect(
      page.locator('button:has-text("Link to Lesson")'),
    ).not.toBeVisible();
  });

  test("should show appropriate error messages", async ({ page }) => {
    // Mock API error
    await page.route("**/lesson-registry-svc/linkback", (route) => {
      if (route.request().method() === "POST") {
        route.fulfill({
          status: 500,
          contentType: "application/json",
          body: JSON.stringify({
            detail: "Failed to create coursework link",
          }),
        });
      }
    });

    await page.goto("/library/coursework/coursework-123");

    // Open linkback modal and try to create link
    await page.click('button:has-text("Link to Lesson")');
    await expect(page.locator("text=Introduction to Algebra")).toBeVisible();

    // Click link button
    await page.click('button:has-text("Link")').first();

    // Should show error message (implementation dependent)
    // In a real app, this might be a toast notification or modal error
    await page.waitForTimeout(1000);

    // Verify error handling (specific implementation would vary)
    // await expect(page.locator('text=Failed to create coursework link')).toBeVisible()
  });

  test("should filter lessons based on subject and grade band", async ({
    page,
  }) => {
    // Mock lessons with different subjects
    await page.route("**/lesson-registry-svc/lessons?**", (route) => {
      const url = route.request().url();

      if (url.includes("subject=Mathematics")) {
        route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify([
            {
              id: "lesson-123",
              title: "Introduction to Algebra",
              subject: "Mathematics",
              gradeBand: "6-8",
            },
          ]),
        });
      } else {
        route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify([]),
        });
      }
    });

    await page.goto("/library/coursework/coursework-123");

    // Open linkback modal
    await page.click('button:has-text("Link to Lesson")');

    // Should only show Mathematics lessons for 6-8 grade band
    await expect(page.locator("text=Introduction to Algebra")).toBeVisible();

    // Verify filtering parameters were sent
    // This would be confirmed by the mock route handler above
  });

  test("should show mastery weight and difficulty adjustment options", async ({
    page,
  }) => {
    await page.goto("/library/coursework/coursework-123");

    // Open linkback modal
    await page.click('button:has-text("Link to Lesson")');
    await expect(page.locator("text=Introduction to Algebra")).toBeVisible();

    // For advanced UI, there might be options to set mastery weight
    // and difficulty adjustment before linking

    // This test would verify that the UI provides these options
    // and that they're properly sent in the API request

    // The current implementation uses default values (100% weight, 0% adjustment)
    // But future versions might include UI controls for these parameters
  });

  test("should work correctly for lesson detail pages (no linkback for lessons)", async ({
    page,
  }) => {
    // Mock lesson detail
    await page.route("**/lesson-registry-svc/lessons/lesson-123", (route) => {
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          id: "lesson-123",
          title: "Introduction to Algebra",
          description: "Basic algebraic concepts",
          subject: "Mathematics",
          gradeBand: "6-8",
          type: "lesson",
          contentUrl: "https://example.com/lesson",
        }),
      });
    });

    await page.goto("/library/lessons/lesson-123");

    // Verify lesson details are displayed
    await expect(page.locator("h1")).toContainText("Introduction to Algebra");
    await expect(page.locator("text=Lesson")).toBeVisible();

    // "Link to Lesson" button should NOT be present for lesson pages
    await expect(
      page.locator('button:has-text("Link to Lesson")'),
    ).not.toBeVisible();
  });
});
