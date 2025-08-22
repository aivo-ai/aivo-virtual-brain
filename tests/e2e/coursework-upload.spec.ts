import { test, expect } from "@playwright/test";

test.describe("Coursework Upload Flow", () => {
  test.beforeEach(async ({ page }) => {
    // Mock API endpoints
    await page.route("/api/consent-svc/check-media-consent", async (route) => {
      await route.fulfill({
        json: { hasConsent: true },
      });
    });

    await page.route(
      "/api/coursework-ingest-svc/ocr/preview",
      async (route) => {
        await route.fulfill({
          json: {
            extractedText:
              "Solve for x: 2x + 5 = 15\n\nAnswer: x = 5\n\nShow your work:\n2x + 5 = 15\n2x = 15 - 5\n2x = 10\nx = 10/2\nx = 5",
            confidence: 0.92,
            suggestedMetadata: {
              subject: "Mathematics",
              topics: ["Algebra", "Linear Equations", "Problem Solving"],
              gradeBand: "Grade 6",
              availableSubjects: [
                "Mathematics",
                "Science",
                "English Language Arts",
              ],
              availableTopics: [
                "Algebra",
                "Linear Equations",
                "Problem Solving",
                "Fractions",
                "Geometry",
              ],
              availableGradeBands: ["Grade 5", "Grade 6", "Grade 7"],
            },
          },
        });
      },
    );

    await page.route("/api/coursework-ingest-svc/upload", async (route) => {
      await route.fulfill({
        json: {
          id: "asset-123",
          fileName: "math-homework.jpg",
          status: "processed",
          subject: "Mathematics",
          topics: ["Algebra", "Linear Equations"],
          gradeBand: "Grade 6",
          extractedText: "Solve for x: 2x + 5 = 15...",
          ocrConfidence: 0.92,
          createdAt: new Date().toISOString(),
        },
      });
    });

    await page.route(
      "/api/coursework-ingest-svc/assets/asset-123/attach",
      async (route) => {
        await route.fulfill({ json: { success: true } });
      },
    );

    // Navigate to upload page
    await page.goto("/coursework/upload");
  });

  test("should display upload options", async ({ page }) => {
    // Check page title and subtitle
    await expect(
      page.getByRole("heading", { name: "Upload Coursework" }),
    ).toBeVisible();
    await expect(
      page.getByText("Capture or upload your assignments"),
    ).toBeVisible();

    // Check camera option
    await expect(
      page.getByRole("heading", { name: "Take Photo" }),
    ).toBeVisible();
    await expect(
      page.getByText("Use your camera to capture documents"),
    ).toBeVisible();
    await expect(
      page.getByRole("button", { name: "Open Camera" }),
    ).toBeVisible();

    // Check file upload option
    await expect(
      page.getByRole("heading", { name: "Upload File" }),
    ).toBeVisible();
    await expect(page.getByText("Select images or PDF files")).toBeVisible();
    await expect(
      page.getByRole("button", { name: "Choose File" }),
    ).toBeVisible();

    // Check upload guidelines
    await expect(page.getByText("Upload Guidelines")).toBeVisible();
    await expect(
      page.getByText("Supported: Images (JPG, PNG, WebP) and PDF files"),
    ).toBeVisible();
    await expect(page.getByText("Maximum file size: 10MB")).toBeVisible();
  });

  test("should handle file upload and navigate to review", async ({ page }) => {
    // Create a test image file
    const testImage = Buffer.from(
      "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/5+hHgAHggJ/PchI7wAAAABJRU5ErkJggg==",
      "base64",
    );

    // Set up file chooser
    const fileChooserPromise = page.waitForEvent("filechooser");
    await page.getByRole("button", { name: "Choose File" }).click();
    const fileChooser = await fileChooserPromise;

    // Upload the test file
    await fileChooser.setFiles([
      {
        name: "math-homework.jpg",
        mimeType: "image/jpeg",
        buffer: testImage,
      },
    ]);

    // Should navigate to review page
    await expect(page).toHaveURL("/coursework/review");
  });

  test("should complete full upload flow", async ({ page }) => {
    // Start upload
    const testImage = Buffer.from(
      "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/5+hHgAHggJ/PchI7wAAAABJRU5ErkJggg==",
      "base64",
    );

    const fileChooserPromise = page.waitForEvent("filechooser");
    await page.getByRole("button", { name: "Choose File" }).click();
    const fileChooser = await fileChooserPromise;
    await fileChooser.setFiles([
      {
        name: "math-homework.jpg",
        mimeType: "image/jpeg",
        buffer: testImage,
      },
    ]);

    // Review page
    await expect(page).toHaveURL("/coursework/review");
    await expect(
      page.getByRole("heading", { name: "Review & Edit" }),
    ).toBeVisible();

    // Wait for OCR processing to complete
    await expect(page.getByText("92%")).toBeVisible();
    await expect(page.getByText("Solve for x: 2x + 5 = 15")).toBeVisible();

    // Check suggested metadata
    await expect(page.getByText("Mathematics")).toBeVisible();
    await expect(page.getByText("Grade 6")).toBeVisible();
    await expect(page.getByText("Algebra")).toBeVisible();

    // Continue to confirm
    await page.getByRole("button", { name: "Continue to Confirm" }).click();

    // Confirm page
    await expect(page).toHaveURL("/coursework/confirm");
    await expect(
      page.getByRole("heading", { name: "Confirm Upload" }),
    ).toBeVisible();

    // Check upload summary
    await expect(page.getByText("math-homework.jpg")).toBeVisible();
    await expect(page.getByText("92% confidence")).toBeVisible();
    await expect(page.getByText("Mathematics")).toBeVisible();

    // Select learner
    await page.getByRole("combobox").click();
    await page.getByText("Emma Johnson").click();

    // Confirm upload
    await page.getByRole("button", { name: "Confirm Upload" }).click();

    // Should show upload progress
    await expect(page.getByText("Upload Progress")).toBeVisible();
    await expect(page.getByText("Uploading")).toBeVisible();

    // Should navigate to coursework list on success
    await expect(page).toHaveURL("/coursework");
  });

  test("should handle consent error", async ({ page }) => {
    // Mock consent denied
    await page.route("/api/consent-svc/check-media-consent", async (route) => {
      await route.fulfill({
        json: { hasConsent: false },
      });
    });

    // Try to upload file
    const testImage = Buffer.from(
      "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/5+hHgAHggJ/PchI7wAAAABJRU5ErkJggg==",
      "base64",
    );

    const fileChooserPromise = page.waitForEvent("filechooser");
    await page.getByRole("button", { name: "Choose File" }).click();
    const fileChooser = await fileChooserPromise;
    await fileChooser.setFiles([
      {
        name: "test.jpg",
        mimeType: "image/jpeg",
        buffer: testImage,
      },
    ]);

    // Should show consent error
    await expect(
      page.getByText("Media upload consent is required"),
    ).toBeVisible();
    await expect(
      page.getByRole("button", { name: "Grant Permission" }),
    ).toBeVisible();
  });

  test("should validate file types", async ({ page }) => {
    // Try to upload invalid file type
    const invalidFile = Buffer.from("invalid file content");

    const fileChooserPromise = page.waitForEvent("filechooser");
    await page.getByRole("button", { name: "Choose File" }).click();
    const fileChooser = await fileChooserPromise;
    await fileChooser.setFiles([
      {
        name: "document.txt",
        mimeType: "text/plain",
        buffer: invalidFile,
      },
    ]);

    // Should show error
    await expect(
      page.getByText("Please select a valid image or PDF file"),
    ).toBeVisible();
  });

  test("should validate file size", async ({ page }) => {
    // Create large file (simulate > 10MB)
    const largeBuffer = Buffer.alloc(11 * 1024 * 1024, "a"); // 11MB

    const fileChooserPromise = page.waitForEvent("filechooser");
    await page.getByRole("button", { name: "Choose File" }).click();
    const fileChooser = await fileChooserPromise;
    await fileChooser.setFiles([
      {
        name: "large-image.jpg",
        mimeType: "image/jpeg",
        buffer: largeBuffer,
      },
    ]);

    // Should show error
    await expect(
      page.getByText("File size must be less than 10MB"),
    ).toBeVisible();
  });

  test("should handle OCR processing error", async ({ page }) => {
    // Mock OCR error
    await page.route(
      "/api/coursework-ingest-svc/ocr/preview",
      async (route) => {
        await route.abort("failed");
      },
    );

    // Upload file
    const testImage = Buffer.from(
      "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/5+hHgAHggJ/PchI7wAAAABJRU5ErkJggg==",
      "base64",
    );

    const fileChooserPromise = page.waitForEvent("filechooser");
    await page.getByRole("button", { name: "Choose File" }).click();
    const fileChooser = await fileChooserPromise;
    await fileChooser.setFiles([
      {
        name: "test.jpg",
        mimeType: "image/jpeg",
        buffer: testImage,
      },
    ]);

    // Should show OCR error on review page
    await expect(page).toHaveURL("/coursework/review");
    await expect(page.getByText("Failed to analyze content")).toBeVisible();
    await expect(page.getByRole("button", { name: "Try Again" })).toBeVisible();
  });

  test("should allow editing metadata", async ({ page }) => {
    // Upload and get to review page
    const testImage = Buffer.from(
      "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/5+hHgAHggJ/PchI7wAAAABJRU5ErkJggg==",
      "base64",
    );

    const fileChooserPromise = page.waitForEvent("filechooser");
    await page.getByRole("button", { name: "Choose File" }).click();
    const fileChooser = await fileChooserPromise;
    await fileChooser.setFiles([
      {
        name: "test.jpg",
        mimeType: "image/jpeg",
        buffer: testImage,
      },
    ]);

    await expect(page).toHaveURL("/coursework/review");

    // Wait for OCR to complete
    await expect(page.getByText("92%")).toBeVisible();

    // Change subject
    await page.getByRole("combobox").first().click();
    await page.getByText("Science").click();

    // Add custom topic
    await page.getByPlaceholder("Add a topic").fill("Custom Topic");
    await page.getByRole("button").filter({ hasText: "+" }).first().click();

    // Verify topic was added
    await expect(page.getByText("Custom Topic")).toBeVisible();

    // Continue and verify changes are preserved
    await page.getByRole("button", { name: "Continue to Confirm" }).click();
    await expect(page.getByText("Science")).toBeVisible();
    await expect(page.getByText("Custom Topic")).toBeVisible();
  });

  test("should require subject selection", async ({ page }) => {
    // Upload and get to review page
    const testImage = Buffer.from(
      "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/5+hHgAHggJ/PchI7wAAAABJRU5ErkJggg==",
      "base64",
    );

    const fileChooserPromise = page.waitForEvent("filechooser");
    await page.getByRole("button", { name: "Choose File" }).click();
    const fileChooser = await fileChooserPromise;
    await fileChooser.setFiles([
      {
        name: "test.jpg",
        mimeType: "image/jpeg",
        buffer: testImage,
      },
    ]);

    await expect(page).toHaveURL("/coursework/review");

    // Wait for OCR and clear subject
    await expect(page.getByText("92%")).toBeVisible();
    await page.getByRole("combobox").first().click();
    // TODO: Add logic to clear subject selection

    // Continue button should be disabled
    await expect(
      page.getByRole("button", { name: "Continue to Confirm" }),
    ).toBeDisabled();

    // Should show validation message
    await expect(
      page.getByText("Please select a subject before continuing"),
    ).toBeVisible();
  });
});
