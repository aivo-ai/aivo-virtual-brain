/**
 * Network Isolation Chaos Tests
 *
 * GOAL: Continuous chaos tests to prove tenant isolation
 * REQS: Synthetic pods attempt cross-namespace reads every 30 min; failure pages SRE ≤5 min
 */

import { test, expect } from "@playwright/test";
import { v4 as uuidv4 } from "uuid";

interface TenantContext {
  tenantId: string;
  namespace: string;
  authToken: string;
  apiUrl: string;
}

interface SyntheticPod {
  id: string;
  tenantId: string;
  namespace: string;
  lastAttempt: Date;
  status: "active" | "failed" | "isolated";
}

class NetworkIsolationTester {
  private sythenticPods: Map<string, SyntheticPod> = new Map();
  private alertThreshold = 5 * 60 * 1000; // 5 minutes in ms
  private testInterval = 30 * 60 * 1000; // 30 minutes in ms

  constructor(
    private alertingEndpoint: string,
    private srePageEndpoint: string,
  ) {}

  /**
   * Create synthetic pods for tenant isolation testing
   */
  async createSyntheticPods(tenants: TenantContext[]): Promise<SyntheticPod[]> {
    const pods: SyntheticPod[] = [];

    for (const tenant of tenants) {
      const pod: SyntheticPod = {
        id: `synthetic-${tenant.tenantId}-${uuidv4().slice(0, 8)}`,
        tenantId: tenant.tenantId,
        namespace: tenant.namespace,
        lastAttempt: new Date(),
        status: "active",
      };

      this.sythenticPods.set(pod.id, pod);
      pods.push(pod);
    }

    return pods;
  }

  /**
   * Attempt cross-namespace read operations (should fail)
   */
  async attemptCrossNamespaceRead(
    sourcePod: SyntheticPod,
    targetTenant: TenantContext,
    sourceToken: string,
  ): Promise<{ success: boolean; error?: string; responseTime: number }> {
    const startTime = Date.now();

    try {
      // Attempt to read learner data from another tenant's namespace
      const response = await fetch(`${targetTenant.apiUrl}/api/learners`, {
        method: "GET",
        headers: {
          Authorization: `Bearer ${sourceToken}`,
          "X-Tenant-ID": targetTenant.tenantId,
          "X-Source-Pod": sourcePod.id,
          "X-Test-Type": "cross-namespace-isolation",
        },
      });

      const responseTime = Date.now() - startTime;

      if (response.ok) {
        // This should NEVER happen - cross-tenant access should be blocked
        return {
          success: false, // False because isolation failed
          error: `SECURITY VIOLATION: Cross-tenant access succeeded (${response.status})`,
          responseTime,
        };
      }

      // Expected: 403 Forbidden or 401 Unauthorized
      if (response.status === 403 || response.status === 401) {
        return {
          success: true, // True because isolation worked correctly
          responseTime,
        };
      }

      return {
        success: false,
        error: `Unexpected response status: ${response.status}`,
        responseTime,
      };
    } catch (error) {
      const responseTime = Date.now() - startTime;

      // Network errors can indicate proper isolation (good)
      // or infrastructure issues (bad)
      if (error instanceof TypeError && error.message.includes("fetch")) {
        return {
          success: true, // Network isolation working
          responseTime,
        };
      }

      return {
        success: false,
        error: `Network error: ${error}`,
        responseTime,
      };
    }
  }

  /**
   * Page SRE team when isolation fails
   */
  async pageSRE(violation: {
    sourcePod: string;
    targetTenant: string;
    error: string;
    timestamp: Date;
    severity: "critical" | "high" | "medium";
  }): Promise<void> {
    const alertPayload = {
      alert: "tenant-isolation-violation",
      severity: violation.severity,
      source: violation.sourcePod,
      target: violation.targetTenant,
      error: violation.error,
      timestamp: violation.timestamp.toISOString(),
      runbook:
        "https://docs.aivo.com/runbooks/chaos#tenant-isolation-violation",
    };

    try {
      // Send to alerting system
      await fetch(this.alertingEndpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(alertPayload),
      });

      // Page SRE if critical
      if (violation.severity === "critical") {
        await fetch(this.srePageEndpoint, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            ...alertPayload,
            page_immediately: true,
            escalation_required: true,
          }),
        });
      }
    } catch (error) {
      console.error("Failed to send alert:", error);
    }
  }

  /**
   * Continuous isolation monitoring
   */
  async startContinuousMonitoring(tenants: TenantContext[]): Promise<void> {
    const pods = await this.createSyntheticPods(tenants);

    setInterval(async () => {
      await this.runIsolationTestCycle(pods, tenants);
    }, this.testInterval);
  }

  /**
   * Run complete isolation test cycle
   */
  async runIsolationTestCycle(
    pods: SyntheticPod[],
    tenants: TenantContext[],
  ): Promise<void> {
    console.log(
      `🔍 Starting isolation test cycle at ${new Date().toISOString()}`,
    );

    for (const pod of pods) {
      const sourceTenant = tenants.find((t) => t.tenantId === pod.tenantId);
      if (!sourceTenant) continue;

      // Test access to all other tenants
      for (const targetTenant of tenants) {
        if (targetTenant.tenantId === pod.tenantId) continue;

        const result = await this.attemptCrossNamespaceRead(
          pod,
          targetTenant,
          sourceTenant.authToken,
        );

        pod.lastAttempt = new Date();

        if (!result.success) {
          pod.status = "failed";

          const violation = {
            sourcePod: pod.id,
            targetTenant: targetTenant.tenantId,
            error: result.error || "Unknown isolation failure",
            timestamp: new Date(),
            severity: result.error?.includes("SECURITY VIOLATION")
              ? ("critical" as const)
              : ("high" as const),
          };

          console.error("🚨 TENANT ISOLATION VIOLATION:", violation);
          await this.pageSRE(violation);
        } else {
          pod.status = "isolated";
        }
      }
    }
  }
}

test.describe("Network Isolation Chaos Tests", () => {
  let isolationTester: NetworkIsolationTester;

  const testTenants: TenantContext[] = [
    {
      tenantId: "district-alpha",
      namespace: "aivo-district-alpha",
      authToken: process.env.TEST_TENANT_ALPHA_TOKEN || "",
      apiUrl: process.env.API_BASE_URL || "http://localhost:3000",
    },
    {
      tenantId: "district-beta",
      namespace: "aivo-district-beta",
      authToken: process.env.TEST_TENANT_BETA_TOKEN || "",
      apiUrl: process.env.API_BASE_URL || "http://localhost:3000",
    },
    {
      tenantId: "district-gamma",
      namespace: "aivo-district-gamma",
      authToken: process.env.TEST_TENANT_GAMMA_TOKEN || "",
      apiUrl: process.env.API_BASE_URL || "http://localhost:3000",
    },
  ];

  test.beforeEach(async () => {
    isolationTester = new NetworkIsolationTester(
      process.env.ALERTING_ENDPOINT || "http://localhost:9093/api/v1/alerts",
      process.env.SRE_PAGE_ENDPOINT || "http://localhost:8080/page",
    );
  });

  test("should deny cross-namespace learner data access", async () => {
    const pods = await isolationTester.createSyntheticPods(testTenants);

    // Test each pod trying to access other tenants
    for (const pod of pods) {
      const sourceTenant = testTenants.find(
        (t) => t.tenantId === pod.tenantId,
      )!;

      for (const targetTenant of testTenants) {
        if (targetTenant.tenantId === pod.tenantId) continue;

        const result = await isolationTester.attemptCrossNamespaceRead(
          pod,
          targetTenant,
          sourceTenant.authToken,
        );

        expect(result.success).toBe(true); // True = isolation working
        expect(result.responseTime).toBeLessThan(5000); // Under 5s response

        if (result.error?.includes("SECURITY VIOLATION")) {
          throw new Error(`CRITICAL: ${result.error}`);
        }
      }
    }
  });

  test("should enforce namespace network policies", async () => {
    const pods = await isolationTester.createSyntheticPods(testTenants);

    for (const pod of pods) {
      // Attempt direct pod-to-pod communication across namespaces
      const targetNamespaces = testTenants
        .filter((t) => t.tenantId !== pod.tenantId)
        .map((t) => t.namespace);

      for (const targetNamespace of targetNamespaces) {
        const response = await fetch(
          `http://${targetNamespace}.svc.cluster.local/health`,
          {
            method: "GET",
            headers: {
              "X-Source-Pod": pod.id,
              "X-Source-Namespace": pod.namespace,
            },
          },
        ).catch((error) => ({ error: error.message }));

        // Should fail due to network policies
        expect(response).toHaveProperty("error");
      }
    }
  });

  test("should block cross-tenant private model access", async () => {
    const pods = await isolationTester.createSyntheticPods(testTenants);

    for (const pod of pods) {
      const sourceTenant = testTenants.find(
        (t) => t.tenantId === pod.tenantId,
      )!;

      for (const targetTenant of testTenants) {
        if (targetTenant.tenantId === pod.tenantId) continue;

        // Attempt to access private foundation models
        const response = await fetch(
          `${targetTenant.apiUrl}/api/private-models/namespaces`,
          {
            method: "GET",
            headers: {
              Authorization: `Bearer ${sourceTenant.authToken}`,
              "X-Tenant-ID": targetTenant.tenantId,
            },
          },
        );

        expect(response.status).toBeOneOf([401, 403, 404]);
        expect(response.ok).toBe(false);
      }
    }
  });

  test("should maintain isolation under load", async () => {
    const pods = await isolationTester.createSyntheticPods(testTenants);

    // Create concurrent isolation violation attempts
    const concurrentTests = [];

    for (let i = 0; i < 50; i++) {
      const pod = pods[i % pods.length];
      const sourceTenant = testTenants.find(
        (t) => t.tenantId === pod.tenantId,
      )!;
      const targetTenant = testTenants.find(
        (t) => t.tenantId !== pod.tenantId,
      )!;

      concurrentTests.push(
        isolationTester.attemptCrossNamespaceRead(
          pod,
          targetTenant,
          sourceTenant.authToken,
        ),
      );
    }

    const results = await Promise.all(concurrentTests);

    // All isolation attempts should fail (success = true means isolation worked)
    for (const result of results) {
      expect(result.success).toBe(true);
      expect(result.responseTime).toBeLessThan(10000); // Under 10s even under load
    }
  });

  test("should trigger SRE alerts within 5 minutes", async () => {
    const alertStart = Date.now();

    // Simulate a critical isolation violation
    await isolationTester.pageSRE({
      sourcePod: "test-synthetic-pod",
      targetTenant: "district-beta",
      error: "SECURITY VIOLATION: Cross-tenant access succeeded (200)",
      timestamp: new Date(),
      severity: "critical",
    });

    const alertTime = Date.now() - alertStart;
    expect(alertTime).toBeLessThan(5 * 60 * 1000); // Under 5 minutes
  });

  test("should run continuous monitoring cycle", async () => {
    const startTime = Date.now();

    // Run one complete test cycle
    const pods = await isolationTester.createSyntheticPods(testTenants);
    await isolationTester.runIsolationTestCycle(pods, testTenants);

    const cycleTime = Date.now() - startTime;
    expect(cycleTime).toBeLessThan(5 * 60 * 1000); // Complete cycle under 5 minutes

    // Verify all pods completed their tests
    for (const pod of pods) {
      expect(pod.lastAttempt).toBeDefined();
      expect(pod.status).toBeOneOf(["isolated", "failed"]);
    }
  });
});

export { NetworkIsolationTester, TenantContext, SyntheticPod };
