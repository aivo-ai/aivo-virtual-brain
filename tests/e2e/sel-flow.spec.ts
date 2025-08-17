import { test, expect } from "@playwright/test";

test.describe("SEL Flow E2E Tests", () => {
  test.beforeEach(async ({ page }) => {
    // Mock GraphQL responses for SEL system
    await page.route("**/graphql", async (route) => {
      const request = route.request();
      const body = await request.postDataJSON();

      if (body?.query?.includes("GetUserSettings")) {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            data: {
              getUserSettings: {
                id: "user-1",
                consentToSEL: true,
                gradeBand: "elementary",
                locale: "en",
              },
            },
          }),
        });
      } else if (body?.query?.includes("GetSELStrategies")) {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            data: {
              getSELStrategies: [
                {
                  id: "strategy-1",
                  title: "Deep Breathing",
                  description: "A calming breathing exercise",
                  category: "anxiety",
                  difficulty: "easy",
                  duration: 5,
                  tags: ["breathing", "calm"],
                  mediaUrl: null,
                  instructions: [
                    "Breathe in slowly",
                    "Hold for 4 counts",
                    "Breathe out slowly",
                  ],
                  effectiveness: 4.5,
                  usageCount: 12,
                },
                {
                  id: "strategy-2",
                  title: "Gratitude Journal",
                  description: "Write down things you are grateful for",
                  category: "wellbeing",
                  difficulty: "easy",
                  duration: 10,
                  tags: ["writing", "gratitude"],
                  mediaUrl: null,
                  instructions: [
                    "Find a quiet space",
                    "Write 3 things you are grateful for",
                    "Reflect on why they matter",
                  ],
                  effectiveness: 4.2,
                  usageCount: 8,
                },
              ],
            },
          }),
        });
      } else if (body?.query?.includes("GetTodaysCheckin")) {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            data: {
              getTodaysCheckin: null,
            },
          }),
        });
      }
    });

    await page.goto("/sel/checkin");
  });

  test("displays consent banner when SEL is disabled", async ({ page }) => {
    // Mock user without SEL consent
    await page.route("**/graphql", async (route) => {
      const request = route.request();
      const body = await request.postDataJSON();

      if (body?.query?.includes("GetUserSettings")) {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            data: {
              getUserSettings: {
                id: "user-1",
                consentToSEL: false,
                gradeBand: "elementary",
                locale: "en",
              },
            },
          }),
        });
      }
    });

    await page.reload();

    // Should show consent banner
    await expect(page.getByTestId("sel-consent-banner")).toBeVisible();
    await expect(
      page.getByText(
        "Social-Emotional Learning features are currently disabled",
      ),
    ).toBeVisible();

    // Check-in form should not be visible
    await expect(page.getByTestId("mood-dial")).not.toBeVisible();
  });

  test("completes daily check-in flow", async ({ page }) => {
    // Check initial state
    await expect(page.getByTestId("mood-dial")).toBeVisible();
    await expect(page.getByText("How are you feeling today?")).toBeVisible();

    // Select mood on dial
    const moodDial = page.getByTestId("mood-dial");
    await moodDial.click({ position: { x: 150, y: 100 } }); // Click towards "happy" area

    // Verify mood selection
    await expect(page.getByText("Happy")).toBeVisible();

    // Select emotion tags
    await page.getByTestId("emotion-tag-excited").click();
    await page.getByTestId("emotion-tag-confident").click();

    // Add notes
    await page.getByTestId("checkin-notes").fill("Had a great day at school!");

    // Mock the check-in submission
    await page.route("**/graphql", async (route) => {
      const request = route.request();
      const body = await request.postDataJSON();

      if (body?.query?.includes("CreateSELCheckin")) {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            data: {
              createSELCheckin: {
                id: "checkin-1",
                mood: "happy",
                energy: 7,
                stress: 2,
                tags: ["excited", "confident"],
                notes: "Had a great day at school!",
                createdAt: new Date().toISOString(),
              },
            },
          }),
        });
      }
    });

    // Submit check-in
    await page.getByTestId("submit-checkin").click();

    // Should show success message
    await expect(
      page.getByText("Check-in completed successfully!"),
    ).toBeVisible();
  });

  test("shows SEL alert for concerning mood patterns", async ({ page }) => {
    // Mock check-in with concerning mood
    await page.route("**/graphql", async (route) => {
      const request = route.request();
      const body = await request.postDataJSON();

      if (body?.query?.includes("CreateSELCheckin")) {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            data: {
              createSELCheckin: {
                id: "checkin-1",
                mood: "angry",
                energy: 2,
                stress: 9,
                tags: ["frustrated", "overwhelmed"],
                notes: "Everything is going wrong",
                createdAt: new Date().toISOString(),
                alert: {
                  severity: "high",
                  reason: "High stress levels detected",
                  recommendedStrategies: ["strategy-1"],
                },
              },
            },
          }),
        });
      }
    });

    // Set concerning mood
    const moodDial = page.getByTestId("mood-dial");
    await moodDial.click({ position: { x: 50, y: 150 } }); // Click towards "angry" area

    // Select concerning tags
    await page.getByTestId("emotion-tag-frustrated").click();
    await page.getByTestId("emotion-tag-overwhelmed").click();

    // Add concerning notes
    await page.getByTestId("checkin-notes").fill("Everything is going wrong");

    // Listen for custom SEL_ALERT event
    let alertEmitted = false;
    await page.evaluate(() => {
      window.addEventListener("SEL_ALERT", () => {
        (window as any).selAlertEmitted = true;
      });
    });

    // Submit check-in
    await page.getByTestId("submit-checkin").click();

    // Verify alert was emitted
    const alertWasEmitted = await page.evaluate(
      () => (window as any).selAlertEmitted,
    );
    expect(alertWasEmitted).toBe(true);

    // Should show alert banner
    await expect(page.getByTestId("sel-alert-banner")).toBeVisible();
    await expect(page.getByText("High stress levels detected")).toBeVisible();

    // Should show recommended strategies
    await expect(page.getByText("Recommended strategies:")).toBeVisible();
    await expect(page.getByText("Deep Breathing")).toBeVisible();
  });

  test("navigates to strategies page and uses strategy", async ({ page }) => {
    // Navigate to strategies
    await page.goto("/sel/strategies");

    // Should show strategy cards
    await expect(page.getByTestId("strategy-card-strategy-1")).toBeVisible();
    await expect(page.getByText("Deep Breathing")).toBeVisible();

    // Filter by category
    await page.getByTestId("category-filter").selectOption("anxiety");

    // Should only show anxiety strategies
    await expect(page.getByTestId("strategy-card-strategy-1")).toBeVisible();
    await expect(
      page.getByTestId("strategy-card-strategy-2"),
    ).not.toBeVisible();

    // Search for strategy
    await page.getByTestId("strategy-search").fill("breathing");
    await expect(page.getByTestId("strategy-card-strategy-1")).toBeVisible();

    // Click to expand strategy
    await page.getByTestId("strategy-card-strategy-1").click();

    // Should show instructions
    await expect(page.getByText("Breathe in slowly")).toBeVisible();
    await expect(page.getByText("Hold for 4 counts")).toBeVisible();

    // Mock strategy usage
    await page.route("**/graphql", async (route) => {
      const request = route.request();
      const body = await request.postDataJSON();

      if (body?.query?.includes("UseStrategy")) {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            data: {
              useStrategy: {
                id: "usage-1",
                strategyId: "strategy-1",
                effectiveness: null,
                createdAt: new Date().toISOString(),
              },
            },
          }),
        });
      }
    });

    // Start using strategy
    await page.getByTestId("use-strategy-button").click();

    // Should show timer/progress
    await expect(page.getByTestId("strategy-timer")).toBeVisible();

    // Complete strategy (mock)
    await page.getByTestId("complete-strategy-button").click();

    // Should show effectiveness rating
    await expect(page.getByTestId("effectiveness-rating")).toBeVisible();

    // Rate effectiveness
    await page.getByTestId("effectiveness-star-4").click();

    // Should show success message
    await expect(
      page.getByText("Strategy completed! Thanks for the feedback."),
    ).toBeVisible();
  });

  test("shows grade-band appropriate visuals", async ({ page }) => {
    // Test elementary visuals
    await page.route("**/graphql", async (route) => {
      const request = route.request();
      const body = await request.postDataJSON();

      if (body?.query?.includes("GetUserSettings")) {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            data: {
              getUserSettings: {
                id: "user-1",
                consentToSEL: true,
                gradeBand: "elementary",
                locale: "en",
              },
            },
          }),
        });
      }
    });

    await page.reload();

    // Should show elementary-appropriate colors and styling
    const moodDial = page.getByTestId("mood-dial");
    await expect(moodDial).toHaveClass(/elementary/);

    // Test middle school visuals
    await page.route("**/graphql", async (route) => {
      const request = route.request();
      const body = await request.postDataJSON();

      if (body?.query?.includes("GetUserSettings")) {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            data: {
              getUserSettings: {
                id: "user-1",
                consentToSEL: true,
                gradeBand: "middle",
                locale: "en",
              },
            },
          }),
        });
      }
    });

    await page.reload();

    // Should show middle school appropriate styling
    await expect(moodDial).toHaveClass(/middle/);

    // Test high school visuals
    await page.route("**/graphql", async (route) => {
      const request = route.request();
      const body = await request.postDataJSON();

      if (body?.query?.includes("GetUserSettings")) {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            data: {
              getUserSettings: {
                id: "user-1",
                consentToSEL: true,
                gradeBand: "high",
                locale: "en",
              },
            },
          }),
        });
      }
    });

    await page.reload();

    // Should show high school appropriate styling
    await expect(moodDial).toHaveClass(/high/);
  });

  test("shows localized content", async ({ page }) => {
    // Test Spanish localization
    await page.route("**/graphql", async (route) => {
      const request = route.request();
      const body = await request.postDataJSON();

      if (body?.query?.includes("GetUserSettings")) {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            data: {
              getUserSettings: {
                id: "user-1",
                consentToSEL: true,
                gradeBand: "elementary",
                locale: "es",
              },
            },
          }),
        });
      }
    });

    await page.reload();

    // Should show Spanish text
    await expect(page.getByText("¿Cómo te sientes hoy?")).toBeVisible();

    // Test French localization
    await page.route("**/graphql", async (route) => {
      const request = route.request();
      const body = await request.postDataJSON();

      if (body?.query?.includes("GetUserSettings")) {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            data: {
              getUserSettings: {
                id: "user-1",
                consentToSEL: true,
                gradeBand: "elementary",
                locale: "fr",
              },
            },
          }),
        });
      }
    });

    await page.reload();

    // Should show French text
    await expect(
      page.getByText("Comment vous sentez-vous aujourd'hui?"),
    ).toBeVisible();
  });

  test("handles errors gracefully", async ({ page }) => {
    // Mock GraphQL error
    await page.route("**/graphql", async (route) => {
      await route.fulfill({
        status: 500,
        contentType: "application/json",
        body: JSON.stringify({
          errors: [{ message: "Internal server error" }],
        }),
      });
    });

    await page.reload();

    // Should show error message
    await expect(
      page.getByText("Unable to load SEL features. Please try again later."),
    ).toBeVisible();

    // Should show retry button
    await expect(page.getByTestId("retry-button")).toBeVisible();
  });

  test("persists data across sessions", async ({ page }) => {
    // Complete a check-in
    const moodDial = page.getByTestId("mood-dial");
    await moodDial.click({ position: { x: 150, y: 100 } });

    await page.getByTestId("emotion-tag-happy").click();
    await page.getByTestId("checkin-notes").fill("Great day!");

    // Mock successful submission
    await page.route("**/graphql", async (route) => {
      const request = route.request();
      const body = await request.postDataJSON();

      if (body?.query?.includes("CreateSELCheckin")) {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            data: {
              createSELCheckin: {
                id: "checkin-1",
                mood: "happy",
                energy: 7,
                stress: 2,
                tags: ["happy"],
                notes: "Great day!",
                createdAt: new Date().toISOString(),
              },
            },
          }),
        });
      } else if (body?.query?.includes("GetTodaysCheckin")) {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            data: {
              getTodaysCheckin: {
                id: "checkin-1",
                mood: "happy",
                energy: 7,
                stress: 2,
                tags: ["happy"],
                notes: "Great day!",
                createdAt: new Date().toISOString(),
              },
            },
          }),
        });
      }
    });

    await page.getByTestId("submit-checkin").click();

    // Navigate away and back
    await page.goto("/");
    await page.goto("/sel/checkin");

    // Should show existing check-in data
    await expect(
      page.getByText("You already completed your check-in today!"),
    ).toBeVisible();
    await expect(page.getByText("Great day!")).toBeVisible();
  });
});
