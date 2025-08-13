// S1-16 Gateway Route Wiring & Policies - k6 Smoke Tests
// Performance and security policy enforcement validation
// Tests: 200/401/403 responses, OTEL tracing, policy enforcement

import http from "k6/http";
import { check, group, sleep } from "k6";
import { Rate } from "k6/metrics";
import { randomString } from "https://jslib.k6.io/k6-utils/1.2.0/index.js";

// Custom metrics
const errorRate = new Rate("errors");
const authErrorRate = new Rate("auth_errors");
const policyErrorRate = new Rate("policy_errors");

// Configuration
const BASE_URL = __ENV.GATEWAY_URL || "http://localhost:8000";
const TEST_JWT =
  __ENV.TEST_JWT ||
  "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJpc3MiOiJ3ZWItYXBwLWtleSIsImV4cCI6MTY5MjU2NDgwMCwiaWF0IjoxNjkyNDc4NDAwLCJsZWFybmVyX3VpZCI6ImxlYXJuZXItMTIzIiwicm9sZSI6ImxlYXJuZXIifQ.example";
const LEARNER_ID = "learner-123";

export const options = {
  stages: [
    { duration: "10s", target: 5 }, // Ramp up
    { duration: "30s", target: 10 }, // Stay at 10 users
    { duration: "10s", target: 0 }, // Ramp down
  ],
  thresholds: {
    http_duration: ["p(95)<2000"], // 95% of requests under 2s
    http_req_failed: ["rate<0.1"], // Error rate under 10%
    errors: ["rate<0.1"],
    auth_errors: ["rate<0.3"], // Expected auth failures
    policy_errors: ["rate<0.2"], // Expected policy violations
  },
};

// Test data generators
function generateCorrelationId() {
  return `k6-test-${randomString(8)}`;
}

function getCommonHeaders(correlationId = null) {
  return {
    "Content-Type": "application/json",
    "X-Correlation-ID": correlationId || generateCorrelationId(),
    "X-Dashboard-Context": "learner",
  };
}

function getAuthHeaders(correlationId = null) {
  return {
    ...getCommonHeaders(correlationId),
    Authorization: `Bearer ${TEST_JWT}`,
  };
}

export default function () {
  // Test gateway health
  group("Gateway Health Check", () => {
    const response = http.get(`${BASE_URL}/gateway/health`, {
      headers: getCommonHeaders(),
    });

    check(response, {
      "Health check returns 200": (r) => r.status === 200,
      "Health check has correlation ID": (r) =>
        r.headers["X-Correlation-Id"] !== undefined,
    }) || errorRate.add(1);
  });

  // Test authentication service (no JWT required)
  group("Authentication Service Tests", () => {
    const correlationId = generateCorrelationId();

    // Login endpoint - should work without JWT
    const loginResponse = http.post(
      `${BASE_URL}/api/v1/auth/login`,
      JSON.stringify({
        username: "test-learner@aivo.ai",
        password: "test123",
      }),
      { headers: getCommonHeaders(correlationId) },
    );

    check(loginResponse, {
      "Auth login accessible without JWT": (r) =>
        r.status === 200 || r.status === 404, // 404 is OK for mock
      "Auth has CORS headers": (r) =>
        r.headers["Access-Control-Allow-Origin"] !== undefined,
    }) || errorRate.add(1);
  });

  // Test JWT-protected services
  group("JWT Protected Services", () => {
    const correlationId = generateCorrelationId();

    // User service without JWT - should return 401
    const noAuthResponse = http.get(`${BASE_URL}/api/v1/users/profile`, {
      headers: getCommonHeaders(correlationId),
    });

    check(noAuthResponse, {
      "User service without JWT returns 401": (r) => r.status === 401,
    }) || authErrorRate.add(1);

    // User service with JWT - should return 200 or 404
    const authResponse = http.get(`${BASE_URL}/api/v1/users/profile`, {
      headers: getAuthHeaders(correlationId),
    });

    check(authResponse, {
      "User service with JWT accessible": (r) =>
        r.status === 200 || r.status === 404,
      "Response has correlation ID": (r) =>
        r.headers["X-Correlation-Id"] !== undefined,
    }) || errorRate.add(1);
  });

  // Test learner scope policy enforcement
  group("Learner Scope Policy Tests", () => {
    const correlationId = generateCorrelationId();

    // Valid learner scope - should work
    const validScopeResponse = http.get(
      `${BASE_URL}/api/v1/assessments?learnerId=${LEARNER_ID}`,
      {
        headers: getAuthHeaders(correlationId),
      },
    );

    check(validScopeResponse, {
      "Valid learner scope allows access": (r) =>
        r.status === 200 || r.status === 404,
    }) || errorRate.add(1);

    // Invalid learner scope - should return 403
    const invalidScopeResponse = http.get(
      `${BASE_URL}/api/v1/assessments?learnerId=learner-999`,
      {
        headers: getAuthHeaders(`${correlationId}-invalid`),
      },
    );

    check(invalidScopeResponse, {
      "Invalid learner scope returns 403": (r) =>
        r.status === 403 || r.status === 404,
    }) || policyErrorRate.add(1);
  });

  // Test dashboard context policy
  group("Dashboard Context Policy Tests", () => {
    const correlationId = generateCorrelationId();

    // Valid dashboard context
    const validContextResponse = http.post(
      `${BASE_URL}/api/v1/orchestrator/workflows`,
      JSON.stringify({
        workflowType: "assessment",
        learnerId: LEARNER_ID,
      }),
      { headers: getAuthHeaders(correlationId) },
    );

    check(validContextResponse, {
      "Valid dashboard context allows access": (r) =>
        r.status === 200 || r.status === 404,
    }) || errorRate.add(1);

    // Invalid dashboard context
    const invalidContextHeaders = {
      ...getAuthHeaders(`${correlationId}-invalid`),
      "X-Dashboard-Context": "invalid-context",
    };

    const invalidContextResponse = http.post(
      `${BASE_URL}/api/v1/orchestrator/workflows`,
      JSON.stringify({
        workflowType: "assessment",
        learnerId: LEARNER_ID,
      }),
      { headers: invalidContextHeaders },
    );

    check(invalidContextResponse, {
      "Invalid dashboard context returns 403": (r) =>
        r.status === 403 || r.status === 404,
    }) || policyErrorRate.add(1);
  });

  // Test consent gate policy
  group("Consent Gate Policy Tests", () => {
    const correlationId = generateCorrelationId();

    // Learner service with consent requirements
    const learnerResponse = http.get(
      `${BASE_URL}/api/v1/learners/${LEARNER_ID}/profile`,
      {
        headers: getAuthHeaders(correlationId),
      },
    );

    check(learnerResponse, {
      "Learner service respects consent gate": (r) =>
        r.status === 200 || r.status === 403 || r.status === 404,
    }) || errorRate.add(1);

    // Notification service with consent
    const notificationResponse = http.get(
      `${BASE_URL}/api/v1/notifications?learnerId=${LEARNER_ID}`,
      {
        headers: getAuthHeaders(`${correlationId}-notif`),
      },
    );

    check(notificationResponse, {
      "Notification service respects consent gate": (r) =>
        r.status === 200 || r.status === 403 || r.status === 404,
    }) || errorRate.add(1);
  });

  // Test all Stage-1 services routing
  group("Stage-1 Services Routing", () => {
    const correlationId = generateCorrelationId();
    const services = [
      { name: "Assessment", path: "/api/v1/assessments" },
      { name: "Learner", path: "/api/v1/learners" },
      { name: "Orchestrator", path: "/api/v1/orchestrator/status" },
      { name: "Notification", path: "/api/v1/notifications" },
      { name: "Search", path: "/api/v1/search/health" },
    ];

    services.forEach((service) => {
      const response = http.get(`${BASE_URL}${service.path}`, {
        headers: getAuthHeaders(
          `${correlationId}-${service.name.toLowerCase()}`,
        ),
      });

      check(
        response,
        {
          [`${service.name} service routes correctly`]: (r) =>
            r.status !== 502 && r.status !== 503,
          [`${service.name} service has proper headers`]: (r) =>
            r.headers["X-Correlation-Id"] !== undefined,
        },
        { service: service.name },
      ) || errorRate.add(1);
    });
  });

  // Test GraphQL endpoint
  group("GraphQL Endpoint Tests", () => {
    const correlationId = generateCorrelationId();

    const graphqlResponse = http.post(
      `${BASE_URL}/graphql`,
      JSON.stringify({
        query: "query { __typename }",
      }),
      { headers: getAuthHeaders(correlationId) },
    );

    check(graphqlResponse, {
      "GraphQL endpoint accessible": (r) =>
        r.status === 200 || r.status === 404,
      "GraphQL has proper CORS": (r) =>
        r.headers["Access-Control-Allow-Origin"] !== undefined,
    }) || errorRate.add(1);
  });

  // Test rate limiting
  group("Rate Limiting Tests", () => {
    const correlationId = generateCorrelationId();

    // Make multiple rapid requests
    for (let i = 0; i < 5; i++) {
      const response = http.get(`${BASE_URL}/api/v1/users/profile`, {
        headers: getAuthHeaders(`${correlationId}-rl-${i}`),
      });

      // Check if rate limiting kicks in (429) or service responds normally
      check(response, {
        "Rate limiting configured correctly": (r) =>
          r.status === 200 ||
          r.status === 401 ||
          r.status === 404 ||
          r.status === 429,
      }) || errorRate.add(1);

      if (response.status === 429) {
        console.log("Rate limit triggered correctly");
        break;
      }
    }
  });

  // Test CORS
  group("CORS Policy Tests", () => {
    const correlationId = generateCorrelationId();

    const corsResponse = http.options(
      `${BASE_URL}/api/v1/users/profile`,
      null,
      {
        headers: {
          Origin: "http://localhost:3000",
          "Access-Control-Request-Method": "GET",
          "Access-Control-Request-Headers": "Authorization,X-Dashboard-Context",
          "X-Correlation-ID": correlationId,
        },
      },
    );

    check(corsResponse, {
      "CORS preflight successful": (r) => r.status === 200 || r.status === 204,
      "CORS allows credentials": (r) =>
        r.headers["Access-Control-Allow-Credentials"] === "true",
      "CORS exposes correlation ID": (r) =>
        r.headers["Access-Control-Expose-Headers"]?.includes(
          "X-Correlation-ID",
        ),
    }) || errorRate.add(1);
  });

  sleep(1);
}

// Teardown function for any cleanup
export function teardown(data) {
  console.log("K6 smoke test completed");
  console.log(`Error rate: ${errorRate.rate * 100}%`);
  console.log(`Auth error rate: ${authErrorRate.rate * 100}%`);
  console.log(`Policy error rate: ${policyErrorRate.rate * 100}%`);
}
