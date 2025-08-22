import { test, expect } from "@playwright/test";

test.describe("IEP Assistant Propose Flow", () => {
  const LEARNER_ID = "test-learner-123";
  const ASSISTANT_URL = `/iep/${LEARNER_ID}/assistant`;
  const EDITOR_URL = `/iep/${LEARNER_ID}/editor`;

  test.beforeEach(async ({ page }) => {
    // Mock authentication
    await page.addInitScript(() => {
      window.localStorage.setItem("auth_token", "mock-token");
      window.localStorage.setItem("user_role", "teacher");
    });

    // Mock GraphQL responses
    await page.route("/api/graphql", async (route) => {
      const request = route.request();
      const body = await request.postDataJSON();

      if (body.query?.includes("ProposeIEP")) {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            data: {
              proposeIep: {
                id: "iep-123",
                learnerId: LEARNER_ID,
                status: "proposed",
                content: {
                  goals: [
                    {
                      id: "goal-1",
                      category: "Academic",
                      description: "Improve reading comprehension",
                      measurableOutcome:
                        "Read grade-level text with 80% comprehension",
                      timeline: "1 year",
                      services: ["reading-support"],
                    },
                  ],
                  accommodations: [
                    "Extended time on tests",
                    "Preferential seating",
                  ],
                  services: [
                    {
                      id: "service-1",
                      type: "Speech Therapy",
                      frequency: "2x per week",
                      duration: "30 minutes",
                      location: "Speech room",
                      provider: "SLP",
                    },
                  ],
                  placement: "General education with support",
                  assessments: [
                    {
                      id: "assessment-1",
                      type: "Academic progress monitoring",
                      frequency: "Monthly",
                      accommodations: ["Extended time"],
                    },
                  ],
                },
                metadata: {
                  createdAt: "2025-01-01T00:00:00Z",
                  updatedAt: "2025-01-01T00:00:00Z",
                  createdBy: "teacher@school.edu",
                  proposedAt: "2025-01-01T00:00:00Z",
                  proposedBy: "teacher@school.edu",
                },
                differences: [
                  {
                    section: "goals",
                    field: "description",
                    oldValue: "Old goal description",
                    newValue: "Improve reading comprehension",
                    changeType: "modified",
                  },
                ],
              },
            },
          }),
        });
      } else if (body.query?.includes("SubmitIEPForApproval")) {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            data: {
              submitIepForApproval: {
                id: "iep-123",
                status: "pending_approval",
                approvals: [
                  {
                    id: "approval-1",
                    actor: "parent@example.com",
                    actorRole: "parent",
                    status: "pending",
                    timestamp: "2025-01-01T00:00:00Z",
                  },
                  {
                    id: "approval-2",
                    actor: "teacher@school.edu",
                    actorRole: "teacher",
                    status: "pending",
                    timestamp: "2025-01-01T00:00:00Z",
                  },
                ],
                metadata: {
                  submittedAt: "2025-01-01T00:00:00Z",
                  submittedBy: "teacher@school.edu",
                },
              },
            },
          }),
        });
      } else if (body.query?.includes("GetIEP")) {
        // Return null for no existing IEP initially
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            data: {
              iep: null,
            },
          }),
        });
      }
    });
  });

  test("should display assistant entry page for new learner", async ({
    page,
  }) => {
    await page.goto(ASSISTANT_URL);

    // Check page title and description
    await expect(
      page.getByRole("heading", { name: "IEP Assistant" }),
    ).toBeVisible();
    await expect(
      page.getByText("AI-powered IEP drafting and proposal generation"),
    ).toBeVisible();

    // Check that no existing IEP status is shown
    await expect(page.getByText("Current IEP Status")).not.toBeVisible();

    // Check propose interface is available
    await expect(page.getByText("Generate New IEP Proposal")).toBeVisible();
    await expect(
      page.getByRole("button", { name: "Generate IEP Draft" }),
    ).toBeVisible();
  });

  test("should generate IEP proposal with custom prompt", async ({ page }) => {
    await page.goto(ASSISTANT_URL);

    // Fill in custom prompt
    const customPrompt =
      "Focus on reading and math goals with speech therapy support";
    await page
      .getByPlaceholder(
        "Enter specific requirements, focus areas, or instructions",
      )
      .fill(customPrompt);

    // Ensure learner data checkbox is checked
    await expect(
      page.getByText("Include learner assessment data"),
    ).toBeChecked();

    // Click propose button
    await page.getByRole("button", { name: "Generate IEP Draft" }).click();

    // Should show loading state
    await expect(page.getByText("Generating...")).toBeVisible();

    // Wait for navigation to editor
    await expect(page).toHaveURL(EDITOR_URL);

    // Should show success toast
    await expect(
      page.getByText("IEP proposal generated successfully!"),
    ).toBeVisible();
  });

  test("should handle proposal generation error", async ({ page }) => {
    // Mock error response
    await page.route("/api/graphql", async (route) => {
      const request = route.request();
      const body = await request.postDataJSON();

      if (body.query?.includes("ProposeIEP")) {
        await route.fulfill({
          status: 500,
          contentType: "application/json",
          body: JSON.stringify({
            errors: [{ message: "Server error" }],
          }),
        });
      }
    });

    await page.goto(ASSISTANT_URL);

    // Click propose button
    await page.getByRole("button", { name: "Generate IEP Draft" }).click();

    // Should show error toast
    await expect(
      page.getByText("Failed to generate IEP proposal. Please try again."),
    ).toBeVisible();

    // Should remain on assistant page
    await expect(page).toHaveURL(ASSISTANT_URL);
  });

  test("should display existing IEP status and allow revision", async ({
    page,
  }) => {
    // Mock existing IEP
    await page.route("/api/graphql", async (route) => {
      const request = route.request();
      const body = await request.postDataJSON();

      if (body.query?.includes("GetIEP")) {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            data: {
              iep: {
                id: "existing-iep-123",
                learnerId: LEARNER_ID,
                status: "approved",
                content: {
                  goals: [],
                  accommodations: [],
                  services: [],
                  placement: "General education",
                  assessments: [],
                },
                metadata: {
                  createdAt: "2024-12-01T00:00:00Z",
                  updatedAt: "2024-12-01T00:00:00Z",
                  createdBy: "teacher@school.edu",
                  reviewedAt: "2024-12-15T00:00:00Z",
                  reviewedBy: "admin@school.edu",
                },
                approvals: [],
              },
            },
          }),
        });
      }
    });

    await page.goto(ASSISTANT_URL);

    // Should show existing IEP status
    await expect(page.getByText("Current IEP Status")).toBeVisible();
    await expect(page.getByText("approved")).toBeVisible();

    // Should show status chip
    await expect(page.getByText("Approved")).toBeVisible();

    // Should show warning about existing IEP
    await expect(page.getByText("Existing IEP Found")).toBeVisible();
    await expect(
      page.getByText("Generating a new proposal will create a revision"),
    ).toBeVisible();

    // Button should say "Generate Revision" instead of "Generate IEP Draft"
    await expect(
      page.getByRole("button", { name: "Generate Revision" }),
    ).toBeVisible();
  });

  test("should submit proposed IEP for approval", async ({ page }) => {
    // Mock existing proposed IEP
    await page.route("/api/graphql", async (route) => {
      const request = route.request();
      const body = await request.postDataJSON();

      if (body.query?.includes("GetIEP")) {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            data: {
              iep: {
                id: "proposed-iep-123",
                learnerId: LEARNER_ID,
                status: "proposed",
                content: {
                  goals: [],
                  accommodations: [],
                  services: [],
                  placement: "General education",
                  assessments: [],
                },
                metadata: {
                  createdAt: "2025-01-01T00:00:00Z",
                  updatedAt: "2025-01-01T00:00:00Z",
                  createdBy: "teacher@school.edu",
                  proposedAt: "2025-01-01T00:00:00Z",
                  proposedBy: "teacher@school.edu",
                },
                approvals: [],
              },
            },
          }),
        });
      }
    });

    await page.goto(ASSISTANT_URL);

    // Should show proposal ready banner
    await expect(page.getByText("IEP Proposal Ready")).toBeVisible();
    await expect(page.getByText("Submit for Approval")).toBeVisible();

    // Click submit for approval button
    await page.getByRole("button", { name: "Submit for Approval" }).click();

    // Should show submit form
    await expect(page.getByText("Submit for Approval")).toBeVisible();
    await expect(
      page.getByText("Add any comments for the approval team"),
    ).toBeVisible();

    // Fill optional comments
    await page
      .getByPlaceholder("Add any context, notes, or specific areas")
      .fill("Please review the reading goals section carefully.");

    // Submit for approval
    await page.getByRole("button", { name: "Submit for Approval" }).click();

    // Should show success message
    await expect(
      page.getByText("IEP submitted for approval successfully!"),
    ).toBeVisible();
  });

  test("should display approval status and history", async ({ page }) => {
    // Mock IEP with approval history
    await page.route("/api/graphql", async (route) => {
      const request = route.request();
      const body = await request.postDataJSON();

      if (body.query?.includes("GetIEP")) {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            data: {
              iep: {
                id: "pending-iep-123",
                learnerId: LEARNER_ID,
                status: "pending_approval",
                content: {
                  goals: [],
                  accommodations: [],
                  services: [],
                  placement: "General education",
                  assessments: [],
                },
                metadata: {
                  createdAt: "2025-01-01T00:00:00Z",
                  updatedAt: "2025-01-01T00:00:00Z",
                  createdBy: "teacher@school.edu",
                  submittedAt: "2025-01-01T00:00:00Z",
                  submittedBy: "teacher@school.edu",
                },
                approvals: [
                  {
                    id: "approval-1",
                    actor: "parent@example.com",
                    actorRole: "parent",
                    status: "approved",
                    timestamp: "2025-01-01T10:00:00Z",
                    comments:
                      "Looks good to me. Thank you for including the math goals.",
                  },
                  {
                    id: "approval-2",
                    actor: "teacher@school.edu",
                    actorRole: "teacher",
                    status: "pending",
                    timestamp: "2025-01-01T00:00:00Z",
                  },
                ],
              },
            },
          }),
        });
      }
    });

    await page.goto(ASSISTANT_URL);

    // Should show pending approval banner
    await expect(page.getByText("Pending Approval")).toBeVisible();
    await expect(
      page.getByText("This IEP is currently under review"),
    ).toBeVisible();

    // Should show approval details
    await expect(page.getByText("Approval History")).toBeVisible();

    // Check parent approval
    await expect(page.getByText("parent@example.com")).toBeVisible();
    await expect(page.getByText("Parent/Guardian")).toBeVisible();
    await expect(page.getByText("Approved")).toBeVisible();
    await expect(
      page.getByText(
        "Looks good to me. Thank you for including the math goals.",
      ),
    ).toBeVisible();

    // Check teacher pending
    await expect(page.getByText("teacher@school.edu")).toBeVisible();
    await expect(page.getByText("Teacher")).toBeVisible();
    await expect(page.getByText("Pending")).toBeVisible();
  });

  test("should navigate to quick actions", async ({ page }) => {
    await page.goto(ASSISTANT_URL);

    // Should show quick actions
    await expect(page.getByText("Quick Actions")).toBeVisible();

    // Check view assessments link
    const assessmentsLink = page.getByText("View Assessments");
    await expect(assessmentsLink).toBeVisible();
    await expect(
      page.getByText("Review recent assessments and evaluation data"),
    ).toBeVisible();

    // Check view progress link
    const progressLink = page.getByText("View Progress");
    await expect(progressLink).toBeVisible();
    await expect(
      page.getByText("Check learner progress and performance data"),
    ).toBeVisible();

    // Test navigation (mock the click to avoid actual navigation in test)
    await assessmentsLink.click();
    // In a real test, you'd check navigation, but we'll just verify the click doesn't error
  });

  test("should be accessible", async ({ page }) => {
    await page.goto(ASSISTANT_URL);

    // Check main headings have proper structure
    const mainHeading = page.getByRole("heading", {
      level: 1,
      name: "IEP Assistant",
    });
    await expect(mainHeading).toBeVisible();

    // Check form labels are associated with inputs
    const promptLabel = page.getByText("Custom Instructions (Optional)");
    const promptInput = page.getByPlaceholder(
      "Enter specific requirements, focus areas, or instructions",
    );

    await expect(promptLabel).toBeVisible();
    await expect(promptInput).toBeVisible();

    // Check buttons have proper labels
    const proposeButton = page.getByRole("button", {
      name: "Generate IEP Draft",
    });
    await expect(proposeButton).toBeVisible();
    await expect(proposeButton).toBeEnabled();

    // Check checkboxes have labels
    const dataCheckbox = page.getByRole("checkbox");
    await expect(dataCheckbox).toBeVisible();
    await expect(
      page.getByText("Include learner assessment data"),
    ).toBeVisible();

    // Check status chips have aria labels when present
    // This would be tested when IEP exists
  });

  test("should handle keyboard navigation", async ({ page }) => {
    await page.goto(ASSISTANT_URL);

    // Tab to the prompt textarea
    await page.keyboard.press("Tab");
    await page.keyboard.press("Tab");
    await page.keyboard.press("Tab");
    await page.keyboard.press("Tab"); // Should be on textarea now

    // Type in the textarea
    await page.keyboard.type("Test prompt via keyboard");

    const promptInput = page.getByPlaceholder(
      "Enter specific requirements, focus areas, or instructions",
    );
    await expect(promptInput).toHaveValue("Test prompt via keyboard");

    // Tab to checkbox
    await page.keyboard.press("Tab");
    await page.keyboard.press("Tab");

    // Space to toggle checkbox
    await page.keyboard.press("Space");

    const dataCheckbox = page.getByRole("checkbox");
    await expect(dataCheckbox).not.toBeChecked();

    // Tab to propose button and activate with Enter
    await page.keyboard.press("Tab");
    await page.keyboard.press("Tab");
    await page.keyboard.press("Tab");
    await page.keyboard.press("Enter");

    // Should trigger the propose action
    await expect(page.getByText("Generating...")).toBeVisible();
  });
});
