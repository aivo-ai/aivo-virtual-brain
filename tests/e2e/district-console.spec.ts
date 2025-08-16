import { test, expect } from "@playwright/test";

test.describe("District Console", () => {
  test.beforeEach(async ({ page }) => {
    // Mock authentication
    await page.goto("/district");
    await page.waitForLoadState("networkidle");
  });

  test("should display district dashboard with stats", async ({ page }) => {
    // Check page title and header
    await expect(page.locator("h1")).toContainText("District Console");

    // Check that stat cards are visible
    await expect(
      page.locator('[data-testid="stat-card-schools"]'),
    ).toBeVisible();
    await expect(
      page.locator('[data-testid="stat-card-utilization"]'),
    ).toBeVisible();
    await expect(page.locator('[data-testid="stat-card-users"]')).toBeVisible();
    await expect(
      page.locator('[data-testid="stat-card-imports"]'),
    ).toBeVisible();

    // Check quick actions are present
    await expect(page.locator("text=Add School")).toBeVisible();
    await expect(page.locator("text=Purchase Seats")).toBeVisible();
    await expect(page.locator("text=Import Roster")).toBeVisible();
    await expect(page.locator("text=Settings")).toBeVisible();
  });

  test("should navigate to schools management", async ({ page }) => {
    // Click on schools navigation
    await page.click("text=Add School");

    // Should navigate to schools page
    await expect(page).toHaveURL("/district/schools");
    await expect(page.locator("h1")).toContainText("Schools Management");

    // Check for Add School button
    await expect(page.locator('button:has-text("Add School")')).toBeVisible();
  });

  test("should navigate to seats management", async ({ page }) => {
    // Click on seats navigation
    await page.click("text=Purchase Seats");

    // Should navigate to seats page
    await expect(page).toHaveURL("/district/seats");
    await expect(page.locator("h1")).toContainText("Seat Management");

    // Check for Purchase Seats button
    await expect(
      page.locator('button:has-text("Purchase Seats")'),
    ).toBeVisible();
  });

  test("should navigate to roster import", async ({ page }) => {
    // Click on roster import navigation
    await page.click("text=Import Roster");

    // Should navigate to roster import page
    await expect(page).toHaveURL("/district/roster-import");
    await expect(page.locator("h1")).toContainText("Roster Import");

    // Check for download template button
    await expect(
      page.locator('button:has-text("Download Template")'),
    ).toBeVisible();
  });

  test("should navigate to settings", async ({ page }) => {
    // Click on settings navigation
    await page.click("text=Settings");

    // Should navigate to settings page
    await expect(page).toHaveURL("/district/settings");
    await expect(page.locator("h1")).toContainText("District Settings");

    // Check for save settings button
    await expect(
      page.locator('button:has-text("Save Settings")'),
    ).toBeVisible();
  });
});

test.describe("Schools Management", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/district/schools");
    await page.waitForLoadState("networkidle");
  });

  test("should show add school form when clicked", async ({ page }) => {
    // Click Add School button
    await page.click('button:has-text("Add School")');

    // Form should be visible
    await expect(page.locator('h2:has-text("Add New School")')).toBeVisible();
    await expect(page.locator('input[id="name"]')).toBeVisible();
    await expect(page.locator('input[id="address"]')).toBeVisible();
  });

  test("should validate required fields", async ({ page }) => {
    // Click Add School button
    await page.click('button:has-text("Add School")');

    // Try to submit without filling required fields
    await page.click('button:has-text("Add School"):last-of-type');

    // Check that form validation prevents submission
    await expect(page.locator('input[id="name"]:invalid')).toBeVisible();
    await expect(page.locator('input[id="address"]:invalid')).toBeVisible();
  });

  test("should allow grade selection", async ({ page }) => {
    // Click Add School button
    await page.click('button:has-text("Add School")');

    // Click on some grade buttons
    await page.click('button:has-text("K")');
    await page.click('button:has-text("1")');
    await page.click('button:has-text("2")');

    // Check that grades are selected (blue background)
    await expect(page.locator('button:has-text("K")')).toHaveClass(
      /bg-blue-600/,
    );
    await expect(page.locator('button:has-text("1")')).toHaveClass(
      /bg-blue-600/,
    );
    await expect(page.locator('button:has-text("2")')).toHaveClass(
      /bg-blue-600/,
    );
  });
});

test.describe("Seat Management", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/district/seats");
    await page.waitForLoadState("networkidle");
  });

  test("should show purchase form when clicked", async ({ page }) => {
    // Click Purchase Seats button
    await page.click('button:has-text("Purchase Seats")');

    // Form should be visible
    await expect(
      page.locator('h2:has-text("Purchase Additional Seats")'),
    ).toBeVisible();
    await expect(page.locator('select[id="schoolId"]')).toBeVisible();
    await expect(page.locator('input[id="seatCount"]')).toBeVisible();
    await expect(page.locator('select[id="duration"]')).toBeVisible();
  });

  test("should calculate pricing correctly", async ({ page }) => {
    // Click Purchase Seats button
    await page.click('button:has-text("Purchase Seats")');

    // Fill in the form
    await page.selectOption('select[id="duration"]', "12");
    await page.fill('input[id="seatCount"]', "100");

    // Check that pricing breakdown appears
    await expect(page.locator("text=Pricing Breakdown")).toBeVisible();
    await expect(
      page.locator("text=100 seats × $15/month × 12 months"),
    ).toBeVisible();
  });

  test("should show seat utilization stats", async ({ page }) => {
    // Check that utilization stats are visible
    await expect(page.locator("text=Total Seats")).toBeVisible();
    await expect(page.locator("text=Used Seats")).toBeVisible();
    await expect(page.locator("text=Available")).toBeVisible();
    await expect(page.locator("text=Utilization")).toBeVisible();
  });
});

test.describe("Roster Import", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/district/roster-import");
    await page.waitForLoadState("networkidle");
  });

  test("should allow template download", async ({ page }) => {
    const downloadPromise = page.waitForEvent("download");

    // Click download template button
    await page.click('button:has-text("Download Template")');

    const download = await downloadPromise;
    expect(download.suggestedFilename()).toBe("roster_template.csv");
  });

  test("should show file upload area", async ({ page }) => {
    // Check that upload area is visible
    await expect(page.locator("text=Drop your CSV file here")).toBeVisible();
    await expect(page.locator("text=CSV files up to 10MB")).toBeVisible();
  });

  test("should require school selection for upload", async ({ page }) => {
    // Try to upload without selecting school should show error or disable button
    await expect(
      page.locator('select:has-text("Choose a school")'),
    ).toBeVisible();
  });
});

test.describe("District Settings", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/district/settings");
    await page.waitForLoadState("networkidle");
  });

  test("should show all settings sections", async ({ page }) => {
    // Check all main sections are present
    await expect(page.locator('h2:has-text("General Settings")')).toBeVisible();
    await expect(page.locator('h2:has-text("SCIM Integration")')).toBeVisible();
    await expect(page.locator('h2:has-text("Single Sign-On")')).toBeVisible();
    await expect(
      page.locator('h2:has-text("Privacy & Compliance")'),
    ).toBeVisible();
  });

  test("should toggle SCIM settings", async ({ page }) => {
    // Initially SCIM fields should be hidden
    await expect(page.locator('input[placeholder*="scim"]')).not.toBeVisible();

    // Enable SCIM
    await page.check("text=Enable SCIM Integration");

    // SCIM fields should now be visible
    await expect(page.locator('input[placeholder*="scim"]')).toBeVisible();
  });

  test("should allow saving settings", async ({ page }) => {
    // Fill in required field
    await page.fill(
      'input[placeholder="Enter district name"]',
      "Test District",
    );
    await page.fill(
      'input[placeholder="admin@district.edu"]',
      "admin@test.edu",
    );

    // Click save
    await page.click('button:has-text("Save Settings")');

    // Should show saving state
    await expect(page.locator('button:has-text("Saving")')).toBeVisible();
  });
});

test.describe("Navigation and Accessibility", () => {
  test("should support keyboard navigation", async ({ page }) => {
    await page.goto("/district");

    // Tab through navigation elements
    await page.keyboard.press("Tab");
    await page.keyboard.press("Tab");

    // Should be able to activate with Enter
    await page.keyboard.press("Enter");
  });

  test("should have proper ARIA labels", async ({ page }) => {
    await page.goto("/district");

    // Check for screen reader accessibility
    await expect(page.locator("[aria-label]")).toHaveCount({ greaterThan: 0 });
  });

  test("should support dark mode", async ({ page }) => {
    await page.goto("/district");

    // Check that dark mode classes are present
    await expect(page.locator(".dark\\:bg-gray-900")).toBeVisible();
  });
});

test.describe("Error Handling", () => {
  test("should handle API errors gracefully", async ({ page }) => {
    // Mock API failure
    await page.route("**/api/v1/district/stats", (route) => {
      route.fulfill({ status: 500, body: "Internal Server Error" });
    });

    await page.goto("/district");

    // Should show error message and retry option
    await expect(page.locator("text=Failed to load")).toBeVisible();
    await expect(page.locator('button:has-text("Retry")')).toBeVisible();
  });

  test("should validate file uploads", async ({ page }) => {
    await page.goto("/district/roster-import");

    // Try to upload non-CSV file
    const fileInput = page.locator('input[type="file"]');
    await fileInput.setInputFiles({
      name: "test.txt",
      mimeType: "text/plain",
      buffer: Buffer.from("test content"),
    });

    // Should show error message
    await expect(page.locator("text=Please upload a CSV file")).toBeVisible();
  });
});
