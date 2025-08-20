import http from "k6/http";
import { check, sleep } from "k6";
import { Rate, Trend } from "k6/metrics";

// Custom metrics for SLO tracking
export const errorRate = new Rate("errors");
export const generateDuration = new Trend("generate_duration");
export const embeddingsDuration = new Trend("embeddings_duration");

// SLO thresholds
export const options = {
  scenarios: {
    // Smoke test for PRs
    smoke: {
      executor: "constant-vus",
      vus: 5,
      duration: "30s",
      tags: { test_type: "smoke" },
      env: { TEST_TYPE: "smoke" },
    },
    // Load test for nightly runs
    load: {
      executor: "ramping-vus",
      stages: [
        { duration: "2m", target: 20 }, // Ramp up
        { duration: "5m", target: 50 }, // Stay at load
        { duration: "2m", target: 100 }, // Peak load
        { duration: "5m", target: 100 }, // Stay at peak
        { duration: "2m", target: 0 }, // Ramp down
      ],
      tags: { test_type: "load" },
      env: { TEST_TYPE: "load" },
    },
    // Stress test for capacity planning
    stress: {
      executor: "ramping-vus",
      stages: [
        { duration: "3m", target: 100 },
        { duration: "5m", target: 200 },
        { duration: "5m", target: 300 },
        { duration: "3m", target: 0 },
      ],
      tags: { test_type: "stress" },
      env: { TEST_TYPE: "stress" },
    },
  },
  thresholds: {
    // SLO: Generate endpoint p95 ≤ 300ms
    "http_req_duration{endpoint:generate}": ["p(95)<300"],
    // SLO: Embeddings endpoint p95 ≤ 200ms
    "http_req_duration{endpoint:embeddings}": ["p(95)<200"],
    // Error rate SLO: < 1% for smoke, < 0.5% for load
    errors: [
      { threshold: "rate<0.01", abortOnFail: true, delayAbortEval: "10s" }, // Smoke
      { threshold: "rate<0.005", abortOnFail: false }, // Load
    ],
    // Availability SLO: > 99.9%
    http_req_failed: ["rate<0.001"],
    // Response time SLO compliance
    generate_duration: ["p(95)<300", "p(99)<500"],
    embeddings_duration: ["p(95)<200", "p(99)<400"],
  },
};

// Test configuration based on environment
const BASE_URL = __ENV.BASE_URL || "http://localhost:8080";
const API_KEY = __ENV.API_KEY || "test-api-key";
const TENANT_ID = __ENV.TENANT_ID || "test-tenant";

// Test data for different scenarios
const generatePrompts = [
  {
    model: "gpt-4",
    messages: [
      { role: "system", content: "You are a helpful assistant." },
      { role: "user", content: "Explain quantum computing in simple terms." },
    ],
    max_tokens: 150,
    temperature: 0.7,
  },
  {
    model: "gpt-3.5-turbo",
    messages: [
      {
        role: "user",
        content: "Write a short poem about artificial intelligence.",
      },
    ],
    max_tokens: 100,
    temperature: 0.8,
  },
  {
    model: "gpt-4",
    messages: [
      { role: "system", content: "You are a math tutor." },
      { role: "user", content: "Solve this equation: 2x + 5 = 15" },
    ],
    max_tokens: 200,
    temperature: 0.3,
  },
];

const embeddingTexts = [
  "Machine learning is a subset of artificial intelligence.",
  "Natural language processing enables computers to understand human language.",
  "Deep learning uses neural networks with multiple layers.",
  "Computer vision allows machines to interpret visual information.",
  "Reinforcement learning trains agents through rewards and penalties.",
];

export function setup() {
  console.log(`Starting load test against ${BASE_URL}`);
  console.log(`Test type: ${__ENV.TEST_TYPE || "default"}`);

  // Health check before starting tests
  const healthCheck = http.get(`${BASE_URL}/health`);
  check(healthCheck, {
    "gateway is healthy": (r) => r.status === 200,
  });

  return {
    baseUrl: BASE_URL,
    apiKey: API_KEY,
    tenantId: TENANT_ID,
  };
}

export default function (data) {
  const headers = {
    "Content-Type": "application/json",
    Authorization: `Bearer ${data.apiKey}`,
    "X-Tenant-ID": data.tenantId,
  };

  // Weighted scenario selection (70% generate, 30% embeddings)
  const scenario = Math.random() < 0.7 ? "generate" : "embeddings";

  if (scenario === "generate") {
    testGenerateEndpoint(data.baseUrl, headers);
  } else {
    testEmbeddingsEndpoint(data.baseUrl, headers);
  }

  // Think time between requests
  sleep(Math.random() * 2 + 0.5); // 0.5-2.5s
}

function testGenerateEndpoint(baseUrl, headers) {
  const prompt =
    generatePrompts[Math.floor(Math.random() * generatePrompts.length)];

  const startTime = Date.now();
  const response = http.post(
    `${baseUrl}/v1/chat/completions`,
    JSON.stringify(prompt),
    {
      headers,
      tags: { endpoint: "generate", model: prompt.model },
    },
  );
  const duration = Date.now() - startTime;

  generateDuration.add(duration);

  const success = check(response, {
    "generate status is 200": (r) => r.status === 200,
    "generate has content": (r) => {
      try {
        const body = JSON.parse(r.body);
        return body.choices && body.choices.length > 0;
      } catch (e) {
        return false;
      }
    },
    "generate response time < 500ms": (r) => duration < 500,
    "generate response time < 300ms (SLO)": (r) => duration < 300,
  });

  if (!success) {
    errorRate.add(1);
    console.error(
      `Generate request failed: ${response.status} - ${response.body}`,
    );
  } else {
    errorRate.add(0);
  }

  // Log slow requests for debugging
  if (duration > 300) {
    console.warn(
      `Slow generate request: ${duration}ms for model ${prompt.model}`,
    );
  }
}

function testEmbeddingsEndpoint(baseUrl, headers) {
  const text =
    embeddingTexts[Math.floor(Math.random() * embeddingTexts.length)];

  const payload = {
    model: "text-embedding-ada-002",
    input: text,
  };

  const startTime = Date.now();
  const response = http.post(
    `${baseUrl}/v1/embeddings`,
    JSON.stringify(payload),
    {
      headers,
      tags: { endpoint: "embeddings" },
    },
  );
  const duration = Date.now() - startTime;

  embeddingsDuration.add(duration);

  const success = check(response, {
    "embeddings status is 200": (r) => r.status === 200,
    "embeddings has data": (r) => {
      try {
        const body = JSON.parse(r.body);
        return body.data && body.data.length > 0;
      } catch (e) {
        return false;
      }
    },
    "embeddings response time < 300ms": (r) => duration < 300,
    "embeddings response time < 200ms (SLO)": (r) => duration < 200,
  });

  if (!success) {
    errorRate.add(1);
    console.error(
      `Embeddings request failed: ${response.status} - ${response.body}`,
    );
  } else {
    errorRate.add(0);
  }

  // Log slow requests for debugging
  if (duration > 200) {
    console.warn(`Slow embeddings request: ${duration}ms`);
  }
}

export function teardown(data) {
  console.log("Load test completed");

  // Final health check
  const healthCheck = http.get(`${data.baseUrl}/health`);
  check(healthCheck, {
    "gateway still healthy after test": (r) => r.status === 200,
  });
}

// Custom summary for SLO reporting
export function handleSummary(data) {
  const sloReport = {
    timestamp: new Date().toISOString(),
    test_type: __ENV.TEST_TYPE || "default",
    slo_compliance: {
      generate_p95: data.metrics.generate_duration?.values?.["p(95)"] || 0,
      generate_p95_slo:
        (data.metrics.generate_duration?.values?.["p(95)"] || 0) <= 300,
      embeddings_p95: data.metrics.embeddings_duration?.values?.["p(95)"] || 0,
      embeddings_p95_slo:
        (data.metrics.embeddings_duration?.values?.["p(95)"] || 0) <= 200,
      error_rate: data.metrics.errors?.values?.rate || 0,
      error_rate_slo: (data.metrics.errors?.values?.rate || 0) < 0.01,
      availability: 1 - (data.metrics.http_req_failed?.values?.rate || 0),
      availability_slo:
        (data.metrics.http_req_failed?.values?.rate || 0) < 0.001,
    },
    performance_summary: {
      total_requests: data.metrics.http_reqs?.values?.count || 0,
      avg_duration: data.metrics.http_req_duration?.values?.avg || 0,
      p95_duration: data.metrics.http_req_duration?.values?.["p(95)"] || 0,
      p99_duration: data.metrics.http_req_duration?.values?.["p(99)"] || 0,
      error_count: data.metrics.http_req_failed?.values?.count || 0,
    },
  };

  return {
    stdout: textSummary(data, { indent: " ", enableColors: true }),
    "slo-report.json": JSON.stringify(sloReport, null, 2),
  };
}
