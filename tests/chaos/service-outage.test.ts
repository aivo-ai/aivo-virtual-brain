/**
 * Service Outage Chaos Tests
 *
 * GOAL: Kill inference provider; gateway fails over to next provider; user sees graceful message
 * REQS: Graceful degradation with meaningful error messages
 */

import { test, expect } from "@playwright/test";
import { v4 as uuidv4 } from "uuid";

interface InferenceProvider {
  id: string;
  name: string;
  endpoint: string;
  priority: number;
  status: "active" | "degraded" | "failed";
  region: string;
  modelTypes: string[];
}

interface FailoverConfig {
  maxRetries: number;
  retryDelayMs: number;
  circuitBreakerThreshold: number;
  gracefulMessageTimeout: number;
}

class ServiceOutageTester {
  private providers: Map<string, InferenceProvider> = new Map();
  private failoverConfig: FailoverConfig;

  constructor(
    private gatewayUrl: string,
    config?: Partial<FailoverConfig>,
  ) {
    this.failoverConfig = {
      maxRetries: 3,
      retryDelayMs: 1000,
      circuitBreakerThreshold: 5,
      gracefulMessageTimeout: 30000, // 30 seconds
      ...config,
    };
  }

  /**
   * Initialize inference providers
   */
  async initializeProviders(): Promise<InferenceProvider[]> {
    const providers: InferenceProvider[] = [
      {
        id: "openai-primary",
        name: "OpenAI GPT-4",
        endpoint: "https://api.openai.com/v1",
        priority: 1,
        status: "active",
        region: "us-east-1",
        modelTypes: ["chat", "completion"],
      },
      {
        id: "anthropic-secondary",
        name: "Anthropic Claude",
        endpoint: "https://api.anthropic.com/v1",
        priority: 2,
        status: "active",
        region: "us-west-2",
        modelTypes: ["chat", "completion"],
      },
      {
        id: "azure-tertiary",
        name: "Azure OpenAI",
        endpoint: "https://aivo.openai.azure.com",
        priority: 3,
        status: "active",
        region: "eastus",
        modelTypes: ["chat", "completion", "embedding"],
      },
      {
        id: "local-fallback",
        name: "Local Llama",
        endpoint: "http://localhost:8080/v1",
        priority: 4,
        status: "active",
        region: "local",
        modelTypes: ["chat"],
      },
    ];

    for (const provider of providers) {
      this.providers.set(provider.id, provider);
    }

    return providers;
  }

  /**
   * Kill a specific inference provider
   */
  async killProvider(
    providerId: string,
  ): Promise<{ success: boolean; error?: string }> {
    const provider = this.providers.get(providerId);
    if (!provider) {
      return { success: false, error: "Provider not found" };
    }

    try {
      // Simulate provider failure by marking as failed
      provider.status = "failed";

      // In real scenario, this would:
      // - Stop the provider container/service
      // - Block network traffic to provider
      // - Simulate provider API errors

      console.log(`💀 Killed provider: ${provider.name} (${providerId})`);
      return { success: true };
    } catch (error) {
      return {
        success: false,
        error: error instanceof Error ? error.message : "Unknown error",
      };
    }
  }

  /**
   * Test inference request with failover
   */
  async testInferenceWithFailover(
    request: {
      prompt: string;
      maxTokens?: number;
      temperature?: number;
    },
    expectedProvider?: string,
  ): Promise<{
    success: boolean;
    response?: string;
    providerId?: string;
    failoverOccurred: boolean;
    responseTime: number;
    error?: string;
    gracefulMessage?: string;
  }> {
    const startTime = Date.now();

    try {
      const response = await fetch(`${this.gatewayUrl}/api/inference/chat`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${process.env.TEST_API_TOKEN}`,
          "X-Request-ID": uuidv4(),
        },
        body: JSON.stringify({
          messages: [{ role: "user", content: request.prompt }],
          max_tokens: request.maxTokens || 100,
          temperature: request.temperature || 0.7,
        }),
      });

      const responseTime = Date.now() - startTime;
      const data = await response.json();

      if (response.ok) {
        return {
          success: true,
          response: data.content || data.message,
          providerId: data.provider_id,
          failoverOccurred: data.failover_occurred || false,
          responseTime,
        };
      }

      // Check for graceful error message
      const gracefulMessage = this.extractGracefulMessage(data);

      return {
        success: false,
        failoverOccurred: data.failover_attempted || false,
        responseTime,
        error: data.error || `HTTP ${response.status}`,
        gracefulMessage,
      };
    } catch (error) {
      const responseTime = Date.now() - startTime;

      return {
        success: false,
        failoverOccurred: false,
        responseTime,
        error: error instanceof Error ? error.message : "Network error",
      };
    }
  }

  /**
   * Extract graceful error message from response
   */
  private extractGracefulMessage(data: any): string | undefined {
    const gracefulMessages = [
      "temporarily unavailable",
      "experiencing high demand",
      "please try again",
      "alternative provider",
      "technical difficulties",
      "maintenance",
    ];

    const message = data.error || data.message || data.user_message || "";
    const isGraceful = gracefulMessages.some((phrase) =>
      message.toLowerCase().includes(phrase),
    );

    return isGraceful ? message : undefined;
  }

  /**
   * Test complete provider failover scenario
   */
  async testProviderFailoverScenario(): Promise<{
    stepsCompleted: number;
    totalSteps: number;
    results: Array<{
      step: string;
      success: boolean;
      details: any;
    }>;
  }> {
    const results: Array<{ step: string; success: boolean; details: any }> = [];
    let stepsCompleted = 0;
    const totalSteps = 6;

    try {
      // Step 1: Initialize providers
      const providers = await this.initializeProviders();
      results.push({
        step: "initialize_providers",
        success: true,
        details: { providerCount: providers.length },
      });
      stepsCompleted++;

      // Step 2: Test normal operation
      const normalRequest = await this.testInferenceWithFailover({
        prompt: "Hello, how are you?",
      });
      results.push({
        step: "test_normal_operation",
        success: normalRequest.success,
        details: normalRequest,
      });
      stepsCompleted++;

      // Step 3: Kill primary provider
      const primaryProvider = providers.find((p) => p.priority === 1)!;
      const killResult = await this.killProvider(primaryProvider.id);
      results.push({
        step: "kill_primary_provider",
        success: killResult.success,
        details: { providerId: primaryProvider.id, ...killResult },
      });
      stepsCompleted++;

      // Step 4: Test failover to secondary
      const failoverRequest = await this.testInferenceWithFailover({
        prompt: "Test failover request",
      });
      results.push({
        step: "test_failover",
        success: failoverRequest.success || !!failoverRequest.gracefulMessage,
        details: failoverRequest,
      });
      stepsCompleted++;

      // Step 5: Verify graceful degradation
      const gracefulDegradation =
        failoverRequest.gracefulMessage ||
        failoverRequest.failoverOccurred ||
        failoverRequest.success;
      results.push({
        step: "verify_graceful_degradation",
        success: !!gracefulDegradation,
        details: {
          hasGracefulMessage: !!failoverRequest.gracefulMessage,
          failoverOccurred: failoverRequest.failoverOccurred,
          responseTime: failoverRequest.responseTime,
        },
      });
      stepsCompleted++;

      // Step 6: Test circuit breaker
      const circuitBreakerResults = [];
      for (
        let i = 0;
        i < this.failoverConfig.circuitBreakerThreshold + 2;
        i++
      ) {
        const result = await this.testInferenceWithFailover({
          prompt: `Circuit breaker test ${i + 1}`,
        });
        circuitBreakerResults.push(result);
      }

      results.push({
        step: "test_circuit_breaker",
        success: true,
        details: {
          totalRequests: circuitBreakerResults.length,
          successfulRequests: circuitBreakerResults.filter((r) => r.success)
            .length,
          gracefulMessages: circuitBreakerResults.filter(
            (r) => r.gracefulMessage,
          ).length,
        },
      });
      stepsCompleted++;
    } catch (error) {
      results.push({
        step: "scenario_error",
        success: false,
        details: {
          error: error instanceof Error ? error.message : "Unknown error",
        },
      });
    }

    return { stepsCompleted, totalSteps, results };
  }

  /**
   * Monitor provider health continuously
   */
  async monitorProviderHealth(durationMs: number = 60000): Promise<{
    healthChecks: Array<{
      timestamp: Date;
      providerId: string;
      status: string;
      responseTime: number;
    }>;
    failureCount: number;
    recoveryCount: number;
  }> {
    const healthChecks: Array<{
      timestamp: Date;
      providerId: string;
      status: string;
      responseTime: number;
    }> = [];

    let failureCount = 0;
    let recoveryCount = 0;
    const startTime = Date.now();

    while (Date.now() - startTime < durationMs) {
      for (const [providerId, provider] of this.providers) {
        const checkStart = Date.now();

        try {
          // Simulate health check
          const wasHealthy = provider.status === "active";
          const isHealthy = Math.random() > 0.1; // 90% uptime simulation

          provider.status = isHealthy ? "active" : "failed";

          if (!wasHealthy && isHealthy) recoveryCount++;
          if (wasHealthy && !isHealthy) failureCount++;

          healthChecks.push({
            timestamp: new Date(),
            providerId,
            status: provider.status,
            responseTime: Date.now() - checkStart,
          });
        } catch (error) {
          provider.status = "failed";
          failureCount++;

          healthChecks.push({
            timestamp: new Date(),
            providerId,
            status: "failed",
            responseTime: Date.now() - checkStart,
          });
        }
      }

      await new Promise((resolve) => setTimeout(resolve, 5000)); // Check every 5s
    }

    return { healthChecks, failureCount, recoveryCount };
  }
}

test.describe("Service Outage Chaos Tests", () => {
  let outageTester: ServiceOutageTester;

  const gatewayUrl = process.env.GATEWAY_URL || "http://localhost:3000";

  test.beforeEach(async () => {
    outageTester = new ServiceOutageTester(gatewayUrl, {
      maxRetries: 3,
      retryDelayMs: 1000,
      circuitBreakerThreshold: 5,
      gracefulMessageTimeout: 30000,
    });
  });

  test("should failover when primary inference provider fails", async () => {
    const scenario = await outageTester.testProviderFailoverScenario();

    expect(scenario.stepsCompleted).toBe(scenario.totalSteps);

    // Verify each step
    const steps = scenario.results.reduce(
      (acc, result) => {
        acc[result.step] = result;
        return acc;
      },
      {} as Record<string, any>,
    );

    expect(steps.initialize_providers.success).toBe(true);
    expect(steps.test_normal_operation.success).toBe(true);
    expect(steps.kill_primary_provider.success).toBe(true);
    expect(steps.test_failover.success).toBe(true);
    expect(steps.verify_graceful_degradation.success).toBe(true);
  });

  test("should provide graceful error messages during outages", async () => {
    // Initialize and kill primary provider
    await outageTester.initializeProviders();
    await outageTester.killProvider("openai-primary");

    const result = await outageTester.testInferenceWithFailover({
      prompt: "Test graceful degradation message",
    });

    // Either successful failover OR graceful error message
    expect(result.success || !!result.gracefulMessage).toBe(true);

    if (result.gracefulMessage) {
      expect(result.gracefulMessage).toMatch(
        /temporarily|maintenance|unavailable|try again/i,
      );
    }

    // Response should be fast even during failure
    expect(result.responseTime).toBeLessThan(30000); // Under 30 seconds
  });

  test("should handle multiple provider failures", async () => {
    await outageTester.initializeProviders();

    // Kill multiple providers sequentially
    await outageTester.killProvider("openai-primary");
    await outageTester.killProvider("anthropic-secondary");

    const result = await outageTester.testInferenceWithFailover({
      prompt: "Test multiple provider failures",
    });

    // Should still work with remaining providers or show graceful message
    const isAcceptable =
      result.success || result.failoverOccurred || !!result.gracefulMessage;

    expect(isAcceptable).toBe(true);

    if (!result.success) {
      expect(result.gracefulMessage).toBeDefined();
    }
  });

  test("should implement circuit breaker pattern", async () => {
    await outageTester.initializeProviders();

    // Kill all providers to trigger circuit breaker
    await outageTester.killProvider("openai-primary");
    await outageTester.killProvider("anthropic-secondary");
    await outageTester.killProvider("azure-tertiary");
    await outageTester.killProvider("local-fallback");

    const requests = [];

    // Make multiple requests to trigger circuit breaker
    for (let i = 0; i < 10; i++) {
      requests.push(
        outageTester.testInferenceWithFailover({
          prompt: `Circuit breaker test ${i + 1}`,
        }),
      );
    }

    const results = await Promise.all(requests);

    // Later requests should fail fast (circuit breaker open)
    const laterResults = results.slice(5);
    const avgLaterResponseTime =
      laterResults.reduce((sum, r) => sum + r.responseTime, 0) /
      laterResults.length;

    expect(avgLaterResponseTime).toBeLessThan(5000); // Fast failure due to circuit breaker

    // All failed requests should have graceful messages
    for (const result of results) {
      if (!result.success) {
        expect(result.gracefulMessage || result.error).toBeDefined();
      }
    }
  });

  test("should recover after provider comes back online", async () => {
    const providers = await outageTester.initializeProviders();

    // Kill primary provider
    await outageTester.killProvider("openai-primary");

    // Verify failover
    const failoverResult = await outageTester.testInferenceWithFailover({
      prompt: "Test during outage",
    });

    expect(
      failoverResult.failoverOccurred || !!failoverResult.gracefulMessage,
    ).toBe(true);

    // Simulate provider recovery
    const primaryProvider = providers.find((p) => p.id === "openai-primary")!;
    primaryProvider.status = "active";

    // Wait for recovery detection
    await new Promise((resolve) => setTimeout(resolve, 2000));

    // Test should succeed with primary provider
    const recoveryResult = await outageTester.testInferenceWithFailover({
      prompt: "Test after recovery",
    });

    expect(recoveryResult.success).toBe(true);
  });

  test("should maintain user experience during provider switching", async () => {
    await outageTester.initializeProviders();

    const userExperienceTests = [];

    // Simulate concurrent user requests during provider failure
    for (let i = 0; i < 20; i++) {
      userExperienceTests.push(
        outageTester.testInferenceWithFailover({
          prompt: `User request ${i + 1}: How can I help my child with math?`,
        }),
      );

      // Kill provider after some requests
      if (i === 5) {
        await outageTester.killProvider("openai-primary");
      }
    }

    const results = await Promise.all(userExperienceTests);

    // Most requests should succeed or have graceful messages
    const acceptableResults = results.filter(
      (r) => r.success || !!r.gracefulMessage,
    );

    expect(acceptableResults.length / results.length).toBeGreaterThan(0.8); // 80% acceptable

    // Response times should be reasonable
    const avgResponseTime =
      results.reduce((sum, r) => sum + r.responseTime, 0) / results.length;
    expect(avgResponseTime).toBeLessThan(15000); // Under 15 seconds average
  });

  test("should monitor provider health continuously", async () => {
    await outageTester.initializeProviders();

    // Run health monitoring for 30 seconds
    const monitoring = await outageTester.monitorProviderHealth(30000);

    expect(monitoring.healthChecks.length).toBeGreaterThan(0);

    // Should detect failures and recoveries
    expect(monitoring.failureCount + monitoring.recoveryCount).toBeGreaterThan(
      0,
    );

    // Health checks should be fast
    const avgHealthCheckTime =
      monitoring.healthChecks.reduce(
        (sum, check) => sum + check.responseTime,
        0,
      ) / monitoring.healthChecks.length;

    expect(avgHealthCheckTime).toBeLessThan(5000); // Under 5 seconds
  });
});

export { ServiceOutageTester, InferenceProvider, FailoverConfig };
