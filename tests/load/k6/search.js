import http from "k6/http";
import { check, sleep } from "k6";
import { Rate, Trend } from "k6/metrics";

// Custom metrics for SLO tracking
export const errorRate = new Rate("search_errors");
export const suggestDuration = new Trend("search_suggest_duration");
export const searchDuration = new Trend("search_query_duration");
export const indexDuration = new Trend("search_index_duration");

// SLO thresholds
export const options = {
  scenarios: {
    // Smoke test for PRs
    smoke: {
      executor: "constant-vus",
      vus: 8,
      duration: "30s",
      tags: { test_type: "smoke" },
      env: { TEST_TYPE: "smoke" },
    },
    // Load test for nightly runs
    load: {
      executor: "ramping-vus",
      stages: [
        { duration: "1m", target: 25 }, // Ramp up
        { duration: "3m", target: 60 }, // Stay at load
        { duration: "2m", target: 100 }, // Peak load
        { duration: "3m", target: 100 }, // Stay at peak
        { duration: "1m", target: 0 }, // Ramp down
      ],
      tags: { test_type: "load" },
      env: { TEST_TYPE: "load" },
    },
    // Stress test for capacity planning
    stress: {
      executor: "ramping-vus",
      stages: [
        { duration: "2m", target: 100 },
        { duration: "3m", target: 200 },
        { duration: "3m", target: 300 },
        { duration: "2m", target: 0 },
      ],
      tags: { test_type: "stress" },
      env: { TEST_TYPE: "stress" },
    },
  },
  thresholds: {
    // SLO: Search suggest p95 ≤ 120ms
    "http_req_duration{endpoint:suggest}": ["p(95)<120"],
    // Search query should be fast
    "http_req_duration{endpoint:search}": ["p(95)<200"],
    // Indexing can be slower
    "http_req_duration{endpoint:index}": ["p(95)<500"],
    // Error rate SLO: < 1% for smoke, < 0.5% for load
    search_errors: [
      { threshold: "rate<0.01", abortOnFail: true, delayAbortEval: "10s" },
      { threshold: "rate<0.005", abortOnFail: false },
    ],
    // Availability SLO: > 99.9%
    http_req_failed: ["rate<0.001"],
    // Response time SLO compliance
    search_suggest_duration: ["p(95)<120", "p(99)<200"],
    search_query_duration: ["p(95)<200", "p(99)<350"],
    search_index_duration: ["p(95)<500", "p(99)<800"],
  },
};

// Test configuration
const BASE_URL = __ENV.BASE_URL || "http://localhost:8080";
const API_KEY = __ENV.API_KEY || "test-api-key";
const TENANT_ID = __ENV.TENANT_ID || "test-tenant";

// Test data for search queries
const searchQueries = [
  "machine learning",
  "artificial intelligence",
  "neural networks",
  "python programming",
  "data science",
  "computer vision",
  "natural language processing",
  "deep learning",
  "statistics",
  "mathematics",
  "algorithms",
  "software engineering",
  "web development",
  "database design",
  "cloud computing",
  "cybersecurity",
  "blockchain",
  "quantum computing",
  "robotics",
  "data analytics",
];

const suggestQueries = [
  "mach",
  "artif",
  "neur",
  "pyth",
  "data",
  "comp",
  "natur",
  "deep",
  "stat",
  "math",
  "algo",
  "soft",
  "web",
  "data",
  "clou",
  "cyber",
  "bloc",
  "quan",
  "robo",
  "anal",
  "learn",
  "intel",
  "netw",
  "prog",
];

const indexDocuments = [
  {
    id: "doc-1",
    title: "Introduction to Machine Learning",
    content:
      "Machine learning is a subset of artificial intelligence that enables computers to learn and improve from experience without being explicitly programmed.",
    subject: "computer_science",
    tags: ["ml", "ai", "programming"],
    difficulty: "beginner",
  },
  {
    id: "doc-2",
    title: "Neural Network Fundamentals",
    content:
      "Neural networks are computing systems inspired by biological neural networks. They consist of interconnected nodes that process information.",
    subject: "computer_science",
    tags: ["neural_networks", "deep_learning"],
    difficulty: "intermediate",
  },
  {
    id: "doc-3",
    title: "Python for Data Science",
    content:
      "Python is a versatile programming language widely used in data science for data analysis, visualization, and machine learning applications.",
    subject: "programming",
    tags: ["python", "data_science", "programming"],
    difficulty: "beginner",
  },
];

export function setup() {
  console.log(`Starting search load test against ${BASE_URL}`);
  console.log(`Test type: ${__ENV.TEST_TYPE || "default"}`);

  // Health check
  const healthCheck = http.get(`${BASE_URL}/health`);
  check(healthCheck, {
    "search service is healthy": (r) => r.status === 200,
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

  // Weighted scenario selection (60% suggest, 30% search, 10% index)
  const scenarios = [
    { name: "suggest", weight: 0.6 },
    { name: "search", weight: 0.3 },
    { name: "index", weight: 0.1 },
  ];

  const random = Math.random();
  let cumulative = 0;
  let selectedScenario = "suggest";

  for (const scenario of scenarios) {
    cumulative += scenario.weight;
    if (random <= cumulative) {
      selectedScenario = scenario.name;
      break;
    }
  }

  switch (selectedScenario) {
    case "suggest":
      testSearchSuggest(data.baseUrl, headers);
      break;
    case "search":
      testSearchQuery(data.baseUrl, headers);
      break;
    case "index":
      testIndexDocument(data.baseUrl, headers);
      break;
  }

  // Think time between requests
  sleep(Math.random() * 1 + 0.2); // 0.2-1.2s
}

function testSearchSuggest(baseUrl, headers) {
  const query =
    suggestQueries[Math.floor(Math.random() * suggestQueries.length)];

  const params = {
    q: query,
    limit: 10,
  };

  const url = `${baseUrl}/api/v1/search/suggest?${Object.entries(params)
    .map(([key, value]) => `${key}=${encodeURIComponent(value)}`)
    .join("&")}`;

  const startTime = Date.now();
  const response = http.get(url, {
    headers,
    tags: { endpoint: "suggest", query_length: query.length },
  });
  const duration = Date.now() - startTime;

  suggestDuration.add(duration);

  const success = check(response, {
    "suggest status is 200": (r) => r.status === 200,
    "suggest has results": (r) => {
      try {
        const body = JSON.parse(r.body);
        return Array.isArray(body.suggestions);
      } catch (e) {
        return false;
      }
    },
    "suggest response time < 150ms": (r) => duration < 150,
    "suggest response time < 120ms (SLO)": (r) => duration < 120,
  });

  if (!success) {
    errorRate.add(1);
    console.error(
      `Search suggest failed: ${response.status} - ${response.body}`,
    );
  } else {
    errorRate.add(0);
  }

  if (duration > 120) {
    console.warn(`Slow search suggest: ${duration}ms for query "${query}"`);
  }
}

function testSearchQuery(baseUrl, headers) {
  const query = searchQueries[Math.floor(Math.random() * searchQueries.length)];

  const payload = {
    query: query,
    filters: {
      subject: Math.random() > 0.7 ? "computer_science" : null,
      difficulty: Math.random() > 0.8 ? "beginner" : null,
    },
    limit: Math.floor(Math.random() * 20) + 10, // 10-30 results
    offset: Math.floor(Math.random() * 50), // Random pagination
    sort_by: Math.random() > 0.5 ? "relevance" : "date",
    include_highlights: true,
  };

  const startTime = Date.now();
  const response = http.post(
    `${baseUrl}/api/v1/search/query`,
    JSON.stringify(payload),
    {
      headers,
      tags: { endpoint: "search", query_type: "full_text" },
    },
  );
  const duration = Date.now() - startTime;

  searchDuration.add(duration);

  const success = check(response, {
    "search status is 200": (r) => r.status === 200,
    "search has results": (r) => {
      try {
        const body = JSON.parse(r.body);
        return Array.isArray(body.results) && typeof body.total === "number";
      } catch (e) {
        return false;
      }
    },
    "search response time < 300ms": (r) => duration < 300,
    "search response time < 200ms (SLO)": (r) => duration < 200,
  });

  if (!success) {
    errorRate.add(1);
    console.error(`Search query failed: ${response.status} - ${response.body}`);
  } else {
    errorRate.add(0);
  }

  if (duration > 200) {
    console.warn(`Slow search query: ${duration}ms for "${query}"`);
  }
}

function testIndexDocument(baseUrl, headers) {
  const doc = indexDocuments[Math.floor(Math.random() * indexDocuments.length)];

  // Add random suffix to make unique
  const payload = {
    ...doc,
    id: doc.id + "-" + Math.floor(Math.random() * 10000),
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  };

  const startTime = Date.now();
  const response = http.post(
    `${baseUrl}/api/v1/search/index`,
    JSON.stringify(payload),
    {
      headers,
      tags: { endpoint: "index", subject: doc.subject },
    },
  );
  const duration = Date.now() - startTime;

  indexDuration.add(duration);

  const success = check(response, {
    "index status is 201 or 200": (r) => r.status === 201 || r.status === 200,
    "index has confirmation": (r) => {
      try {
        const body = JSON.parse(r.body);
        return body.indexed === true || body.status === "indexed";
      } catch (e) {
        return false;
      }
    },
    "index response time < 600ms": (r) => duration < 600,
    "index response time < 500ms (SLO)": (r) => duration < 500,
  });

  if (!success) {
    errorRate.add(1);
    console.error(
      `Index document failed: ${response.status} - ${response.body}`,
    );
  } else {
    errorRate.add(0);
  }

  if (duration > 500) {
    console.warn(`Slow index operation: ${duration}ms for ${doc.subject}`);
  }
}

export function teardown(data) {
  console.log("Search load test completed");

  // Final health check
  const healthCheck = http.get(`${data.baseUrl}/health`);
  check(healthCheck, {
    "search service still healthy after test": (r) => r.status === 200,
  });
}

// Custom summary for SLO reporting
export function handleSummary(data) {
  const sloReport = {
    timestamp: new Date().toISOString(),
    service: "search",
    test_type: __ENV.TEST_TYPE || "default",
    slo_compliance: {
      suggest_p95: data.metrics.search_suggest_duration?.values?.["p(95)"] || 0,
      suggest_p95_slo:
        (data.metrics.search_suggest_duration?.values?.["p(95)"] || 0) <= 120,
      search_p95: data.metrics.search_query_duration?.values?.["p(95)"] || 0,
      search_p95_slo:
        (data.metrics.search_query_duration?.values?.["p(95)"] || 0) <= 200,
      index_p95: data.metrics.search_index_duration?.values?.["p(95)"] || 0,
      index_p95_slo:
        (data.metrics.search_index_duration?.values?.["p(95)"] || 0) <= 500,
      error_rate: data.metrics.search_errors?.values?.rate || 0,
      error_rate_slo: (data.metrics.search_errors?.values?.rate || 0) < 0.01,
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
    endpoint_breakdown: {
      suggest_avg: data.metrics.search_suggest_duration?.values?.avg || 0,
      search_avg: data.metrics.search_query_duration?.values?.avg || 0,
      index_avg: data.metrics.search_index_duration?.values?.avg || 0,
    },
    query_performance: {
      suggest_p50: data.metrics.search_suggest_duration?.values?.["p(50)"] || 0,
      suggest_p90: data.metrics.search_suggest_duration?.values?.["p(90)"] || 0,
      search_p50: data.metrics.search_query_duration?.values?.["p(50)"] || 0,
      search_p90: data.metrics.search_query_duration?.values?.["p(90)"] || 0,
    },
  };

  return {
    stdout: textSummary(data, { indent: " ", enableColors: true }),
    "search-slo-report.json": JSON.stringify(sloReport, null, 2),
  };
}
