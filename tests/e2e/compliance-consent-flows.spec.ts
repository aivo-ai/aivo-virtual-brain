import { test, expect } from "@playwright/test";
import { Page } from "@playwright/test";

interface TestUser {
  email: string;
  age: number;
  location: string;
  isMinor: boolean;
  parentEmail?: string;
}

interface ConsentRecord {
  version: string;
  timestamp: string;
  consents: Record<string, boolean>;
  locale: string;
  ipAddress: string;
  userAgent: string;
}

// Test users for different compliance scenarios
const testUsers = {
  usChild: {
    email: "child.test@example.com",
    age: 10,
    location: "US",
    isMinor: true,
    parentEmail: "parent.test@example.com",
  },
  usAdult: {
    email: "adult.test@example.com",
    age: 25,
    location: "US",
    isMinor: false,
  },
  euMinor: {
    email: "eu.minor@example.com",
    age: 15,
    location: "EU",
    isMinor: true,
    parentEmail: "eu.parent@example.com",
  },
  euAdult: {
    email: "eu.adult@example.com",
    age: 28,
    location: "EU",
    isMinor: false,
  },
  caResident: {
    email: "ca.resident@example.com",
    age: 22,
    location: "CA",
    isMinor: false,
  },
};

class ConsentFlowHelper {
  constructor(private page: Page) {}

  async navigateToConsentPage(userContext: TestUser) {
    const params = new URLSearchParams({
      age: userContext.age.toString(),
      location: userContext.location,
      isMinor: userContext.isMinor.toString(),
      locale: "en",
    });

    await this.page.goto(`/consent?${params.toString()}`);
  }

  async verifyApplicableFrameworks(expectedFrameworks: string[]) {
    const frameworkBadges = this.page.locator(
      '[data-testid="framework-badge"]',
    );

    for (const framework of expectedFrameworks) {
      await expect(
        frameworkBadges.filter({ hasText: framework }),
      ).toBeVisible();
    }
  }

  async verifyAgeGating(userContext: TestUser) {
    if (userContext.isMinor) {
      await expect(
        this.page.locator('[data-testid="age-gating-notice"]'),
      ).toBeVisible();

      if (userContext.age < 13 && userContext.location === "US") {
        await expect(this.page.locator("text=COPPA")).toBeVisible();
        await expect(this.page.locator("text=parental consent")).toBeVisible();
      }
    }
  }

  async giveConsent(consentCategories: string[]) {
    for (const category of consentCategories) {
      const checkbox = this.page.locator(`[data-testid="consent-${category}"]`);
      await checkbox.check();
    }
  }

  async submitConsent() {
    await this.page.locator('[data-testid="submit-consent"]').click();
  }

  async verifyConsentRecorded(expectedVersion: string) {
    await expect(
      this.page.locator(`text=Consent Version: ${expectedVersion}`),
    ).toBeVisible();
    await expect(
      this.page.locator('[data-testid="consent-timestamp"]'),
    ).toBeVisible();
  }
}

class ParentalConsentHelper {
  constructor(private page: Page) {}

  async submitParentalVerification(parentEmail: string) {
    await this.page.fill('[data-testid="parent-email"]', parentEmail);
    await this.page.selectOption(
      '[data-testid="verification-method"]',
      "email-plus",
    );
    await this.page.click('[data-testid="send-verification"]');

    await expect(
      this.page.locator("text=Verification email sent"),
    ).toBeVisible();
  }

  async completeEmailVerification(verificationCode: string) {
    await this.page.fill('[data-testid="verification-code"]', verificationCode);
    await this.page.click('[data-testid="verify-parent"]');

    await expect(
      this.page.locator("text=Parent verified successfully"),
    ).toBeVisible();
  }

  async verifyParentalConsentForm() {
    // Check required parental consent elements
    await expect(
      this.page.locator("text=PARENTAL CONSENT FOR CHILDREN UNDER 13"),
    ).toBeVisible();
    await expect(
      this.page.locator("text=INFORMATION WE COLLECT"),
    ).toBeVisible();
    await expect(
      this.page.locator("text=HOW WE USE THIS INFORMATION"),
    ).toBeVisible();
    await expect(this.page.locator("text=RIGHTS AND CONTROLS")).toBeVisible();
  }
}

test.describe("Multi-Locale Compliance Flow Tests", () => {
  let consentHelper: ConsentFlowHelper;
  let parentalHelper: ParentalConsentHelper;

  test.beforeEach(async ({ page }) => {
    consentHelper = new ConsentFlowHelper(page);
    parentalHelper = new ParentalConsentHelper(page);
  });

  test.describe("COPPA Compliance (US Children Under 13)", () => {
    test("should require parental consent for US children under 13", async ({
      page,
    }) => {
      await consentHelper.navigateToConsentPage(testUsers.usChild);

      // Verify COPPA framework is shown
      await consentHelper.verifyApplicableFrameworks(["COPPA", "FERPA"]);

      // Verify age gating message
      await consentHelper.verifyAgeGating(testUsers.usChild);

      // Verify parental consent required
      await expect(
        page.locator("text=Parental Consent Required"),
      ).toBeVisible();
      await expect(
        page.locator('[data-testid="parental-consent-mode"]'),
      ).toBeVisible();
    });

    test("should complete parental verification flow", async ({ page }) => {
      await consentHelper.navigateToConsentPage(testUsers.usChild);

      // Navigate to parental verification
      await page.click('[data-testid="start-parental-verification"]');

      // Verify parental consent form
      await parentalHelper.verifyParentalConsentForm();

      // Submit parental verification
      await parentalHelper.submitParentalVerification(
        testUsers.usChild.parentEmail!,
      );

      // Simulate email verification (in real test, would need email integration)
      await parentalHelper.completeEmailVerification("TEST123");

      // Complete child consent with limited options
      await consentHelper.giveConsent(["essential", "educational"]);
      await consentHelper.submitConsent();

      // Verify consent recorded with COPPA compliance
      await consentHelper.verifyConsentRecorded("2025-v1");
      await expect(
        page.locator("text=COPPA compliant consent recorded"),
      ).toBeVisible();
    });

    test("should block registration without parental consent", async ({
      page,
    }) => {
      await consentHelper.navigateToConsentPage(testUsers.usChild);

      // Try to proceed without parental verification
      await page.click('[data-testid="skip-parental-consent"]');

      // Should show blocking message
      await expect(
        page.locator("text=Parental consent is required"),
      ).toBeVisible();
      await expect(
        page.locator('[data-testid="registration-blocked"]'),
      ).toBeVisible();
    });
  });

  test.describe("GDPR Compliance (EU Residents)", () => {
    test("should show GDPR rights for EU adult users", async ({ page }) => {
      await consentHelper.navigateToConsentPage(testUsers.euAdult);

      // Verify GDPR framework
      await consentHelper.verifyApplicableFrameworks(["GDPR"]);

      // Verify GDPR-specific consent options
      await expect(page.locator("text=Legitimate Interests")).toBeVisible();
      await expect(page.locator("text=Right to Object")).toBeVisible();

      // Verify granular consent options
      await expect(
        page.locator('[data-testid="consent-educational"]'),
      ).toBeVisible();
      await expect(
        page.locator('[data-testid="consent-analytics"]'),
      ).toBeVisible();
      await expect(
        page.locator('[data-testid="consent-marketing"]'),
      ).toBeVisible();
    });

    test("should handle EU minor consent (under 16)", async ({ page }) => {
      await consentHelper.navigateToConsentPage(testUsers.euMinor);

      // Verify both GDPR and parental consent requirements
      await consentHelper.verifyApplicableFrameworks(["GDPR"]);
      await expect(
        page.locator("text=Parental consent required under GDPR"),
      ).toBeVisible();

      // Verify enhanced protection for minors
      await expect(
        page.locator("text=Enhanced protection for users under 16"),
      ).toBeVisible();
    });

    test("should allow selective consent withdrawal", async ({ page }) => {
      await consentHelper.navigateToConsentPage(testUsers.euAdult);

      // Give initial consent
      await consentHelper.giveConsent([
        "essential",
        "educational",
        "analytics",
        "marketing",
      ]);
      await consentHelper.submitConsent();

      // Navigate to consent management
      await page.click('[data-testid="manage-consent"]');

      // Withdraw specific consent
      await page.uncheck('[data-testid="consent-marketing"]');
      await page.click('[data-testid="update-consent"]');

      // Verify consent updated
      await expect(
        page.locator("text=Consent preferences updated"),
      ).toBeVisible();
      await expect(
        page.locator("text=Marketing consent withdrawn"),
      ).toBeVisible();
    });
  });

  test.describe("CCPA/CPRA Compliance (California Residents)", () => {
    test("should display CCPA rights for California residents", async ({
      page,
    }) => {
      await consentHelper.navigateToConsentPage(testUsers.caResident);

      // Verify CCPA framework
      await consentHelper.verifyApplicableFrameworks(["CCPA/CPRA"]);

      // Verify CCPA-specific rights
      await expect(page.locator("text=Right to Know")).toBeVisible();
      await expect(page.locator("text=Right to Delete")).toBeVisible();
      await expect(page.locator("text=Right to Correct")).toBeVisible();
      await expect(page.locator("text=Right to Opt-Out")).toBeVisible();
    });

    test("should provide Do Not Sell link", async ({ page }) => {
      await consentHelper.navigateToConsentPage(testUsers.caResident);

      // Verify Do Not Sell link is prominent
      await expect(
        page.locator('[data-testid="do-not-sell-link"]'),
      ).toBeVisible();
      await expect(
        page.locator("text=Do Not Sell My Personal Information"),
      ).toBeVisible();

      // Click opt-out link
      await page.click('[data-testid="do-not-sell-link"]');

      // Verify opt-out form
      await expect(page.locator("text=Opt-Out of Sale/Sharing")).toBeVisible();
      await expect(
        page.locator('[data-testid="ccpa-opt-out-form"]'),
      ).toBeVisible();
    });

    test("should respect Global Privacy Control (GPC)", async ({ page }) => {
      // Set GPC header
      await page.setExtraHTTPHeaders({
        "Sec-GPC": "1",
      });

      await consentHelper.navigateToConsentPage(testUsers.caResident);

      // Verify automatic opt-out recognition
      await expect(
        page.locator("text=Global Privacy Control detected"),
      ).toBeVisible();
      await expect(
        page.locator("text=Automatically opted out of data sale/sharing"),
      ).toBeVisible();
    });
  });

  test.describe("FERPA Compliance (Educational Context)", () => {
    test("should show FERPA protections for US educational users", async ({
      page,
    }) => {
      await consentHelper.navigateToConsentPage(testUsers.usAdult);

      // Verify FERPA framework
      await consentHelper.verifyApplicableFrameworks(["FERPA"]);

      // Verify educational-specific protections
      await expect(
        page.locator("text=Educational Records Protection"),
      ).toBeVisible();
      await expect(page.locator("text=Directory Information")).toBeVisible();
      await expect(page.locator("text=FERPA Rights")).toBeVisible();
    });

    test("should handle directory information opt-out", async ({ page }) => {
      await consentHelper.navigateToConsentPage(testUsers.usAdult);

      // Navigate to FERPA settings
      await page.click('[data-testid="ferpa-settings"]');

      // Opt out of directory information
      await page.check('[data-testid="directory-opt-out"]');
      await page.click('[data-testid="save-ferpa-settings"]');

      // Verify opt-out recorded
      await expect(
        page.locator("text=Directory information opt-out recorded"),
      ).toBeVisible();
    });
  });

  test.describe("Consent Version History", () => {
    test("should maintain consent version history", async ({ page }) => {
      await consentHelper.navigateToConsentPage(testUsers.usAdult);

      // Give initial consent
      await consentHelper.giveConsent(["essential", "educational"]);
      await consentHelper.submitConsent();

      // Navigate to consent history
      await page.click('[data-testid="consent-history"]');

      // Verify history shows initial consent
      await expect(
        page.locator('[data-testid="consent-record-0"]'),
      ).toBeVisible();
      await expect(page.locator("text=2025-v1")).toBeVisible();

      // Update consent
      await page.click('[data-testid="manage-consent"]');
      await page.check('[data-testid="consent-analytics"]');
      await page.click('[data-testid="update-consent"]');

      // Verify new version in history
      await page.click('[data-testid="consent-history"]');
      await expect(
        page.locator('[data-testid="consent-record-1"]'),
      ).toBeVisible();
    });

    test("should show consent changes with timestamps", async ({ page }) => {
      await consentHelper.navigateToConsentPage(testUsers.euAdult);

      // Give initial consent
      await consentHelper.giveConsent([
        "essential",
        "educational",
        "analytics",
      ]);
      await consentHelper.submitConsent();

      // Wait and update consent
      await page.waitForTimeout(1000);
      await page.click('[data-testid="manage-consent"]');
      await page.uncheck('[data-testid="consent-analytics"]');
      await page.check('[data-testid="consent-marketing"]');
      await page.click('[data-testid="update-consent"]');

      // Check history shows detailed changes
      await page.click('[data-testid="consent-history"]');
      await expect(page.locator("text=Analytics: ✓ → ✗")).toBeVisible();
      await expect(page.locator("text=Marketing: ✗ → ✓")).toBeVisible();
    });
  });

  test.describe("Locale-Specific Consent Flows", () => {
    test("should adapt consent text for different locales", async ({
      page,
    }) => {
      // Test Spanish locale
      const spanishParams = new URLSearchParams({
        age: "25",
        location: "US",
        isMinor: "false",
        locale: "es",
      });

      await page.goto(`/consent?${spanishParams.toString()}`);

      // Verify Spanish text (assuming i18n is set up)
      await expect(
        page.locator("text=Privacidad y Protección de Datos"),
      ).toBeVisible();

      // Test French locale for EU context
      const frenchParams = new URLSearchParams({
        age: "25",
        location: "EU",
        isMinor: "false",
        locale: "fr",
      });

      await page.goto(`/consent?${frenchParams.toString()}`);
      await expect(
        page.locator("text=Confidentialité et Protection des Données"),
      ).toBeVisible();
    });

    test("should show appropriate legal framework text by locale", async ({
      page,
    }) => {
      // German user should see GDPR in German context
      const germanParams = new URLSearchParams({
        age: "25",
        location: "EU",
        isMinor: "false",
        locale: "de",
      });

      await page.goto(`/consent?${germanParams.toString()}`);

      // Verify GDPR references appropriate for German users
      await expect(
        page.locator("text=Datenschutz-Grundverordnung"),
      ).toBeVisible();
      await expect(page.locator("text=Artikel 6 DSGVO")).toBeVisible();
    });
  });

  test.describe("Error Handling and Edge Cases", () => {
    test("should handle invalid age input gracefully", async ({ page }) => {
      const invalidParams = new URLSearchParams({
        age: "invalid",
        location: "US",
        isMinor: "false",
        locale: "en",
      });

      await page.goto(`/consent?${invalidParams.toString()}`);

      // Should default to adult consent flow with validation
      await expect(page.locator("text=Please verify your age")).toBeVisible();
    });

    test("should handle unknown location codes", async ({ page }) => {
      const unknownParams = new URLSearchParams({
        age: "25",
        location: "XX",
        isMinor: "false",
        locale: "en",
      });

      await page.goto(`/consent?${unknownParams.toString()}`);

      // Should show general privacy framework
      await expect(
        page.locator("text=General Privacy Protection"),
      ).toBeVisible();
    });

    test("should handle consent form submission errors", async ({ page }) => {
      await consentHelper.navigateToConsentPage(testUsers.usAdult);

      // Try to submit without required consents
      await page.click('[data-testid="submit-consent"]');

      // Should show validation error
      await expect(
        page.locator("text=Please review required consents"),
      ).toBeVisible();
    });
  });

  test.describe("Data Export and Rights Exercise", () => {
    test("should allow data export in multiple formats", async ({ page }) => {
      await consentHelper.navigateToConsentPage(testUsers.euAdult);
      await consentHelper.giveConsent([
        "essential",
        "educational",
        "analytics",
      ]);
      await consentHelper.submitConsent();

      // Navigate to privacy controls
      await page.click('[data-testid="privacy-controls"]');

      // Test JSON export
      await page.selectOption('[data-testid="export-format"]', "JSON");
      await page.click('[data-testid="request-export"]');

      await expect(page.locator("text=Export request submitted")).toBeVisible();
      await expect(page.locator("text=JSON format")).toBeVisible();

      // Test PDF export
      await page.selectOption('[data-testid="export-format"]', "PDF");
      await page.click('[data-testid="request-export"]');

      await expect(page.locator("text=PDF format")).toBeVisible();
    });

    test("should verify identity for sensitive rights requests", async ({
      page,
    }) => {
      await consentHelper.navigateToConsentPage(testUsers.euAdult);

      // Request account deletion (high-risk request)
      await page.click('[data-testid="request-deletion"]');

      // Should require additional verification
      await expect(
        page.locator("text=Identity Verification Required"),
      ).toBeVisible();
      await expect(
        page.locator('[data-testid="identity-verification-form"]'),
      ).toBeVisible();

      // Fill verification form
      await page.fill('[data-testid="verify-email"]', testUsers.euAdult.email);
      await page.fill('[data-testid="verify-birthdate"]', "1995-01-01");
      await page.click('[data-testid="send-verification"]');

      await expect(page.locator("text=Verification email sent")).toBeVisible();
    });
  });
});

test.describe("API Integration Tests", () => {
  test("should record consent via API", async ({ request }) => {
    const consentData = {
      userId: "test-user-123",
      age: 25,
      location: "US",
      consents: {
        essential: true,
        educational: true,
        analytics: false,
        marketing: false,
      },
      version: "2025-v1",
      locale: "en",
      ipAddress: "127.0.0.1",
      userAgent: "test-agent",
    };

    const response = await request.post("/api/consent/record", {
      data: consentData,
    });

    expect(response.ok()).toBeTruthy();

    const result = await response.json();
    expect(result.consentId).toBeDefined();
    expect(result.timestamp).toBeDefined();
  });

  test("should retrieve consent history via API", async ({ request }) => {
    const response = await request.get("/api/consent/history/test-user-123");

    expect(response.ok()).toBeTruthy();

    const history = await response.json();
    expect(Array.isArray(history)).toBeTruthy();
    expect(history[0]).toHaveProperty("version");
    expect(history[0]).toHaveProperty("timestamp");
    expect(history[0]).toHaveProperty("consents");
  });

  test("should process data subject rights request via API", async ({
    request,
  }) => {
    const requestData = {
      userId: "test-user-123",
      requestType: "access",
      verificationData: {
        email: "test@example.com",
        birthDate: "1995-01-01",
      },
    };

    const response = await request.post("/api/privacy/request", {
      data: requestData,
    });

    expect(response.ok()).toBeTruthy();

    const result = await response.json();
    expect(result.requestId).toBeDefined();
    expect(result.status).toBe("pending-verification");
  });
});
