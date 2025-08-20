// K6 Load Testing Script for Edge Security Validation
// Tests rate limiting, geographic controls, and WAF under load

import http from "k6/http";
import { check, sleep } from "k6";
import { Rate } from "k6/metrics";

// Custom metrics
const rateLimit429Rate = new Rate("rate_limit_429_rate");
const wafBlock403Rate = new Rate("waf_block_403_rate");
const botBlock403Rate = new Rate("bot_block_403_rate");

// Test configuration
export const options = {
  scenarios: {
    // Normal traffic simulation
    normal_traffic: {
      executor: "constant-vus",
      vus: 10,
      duration: "2m",
      tags: { test_type: "normal" },
    },

    // Authentication spray attack simulation
    auth_spray: {
      executor: "constant-arrival-rate",
      rate: 20, // 20 requests per second
      timeUnit: "1s",
      duration: "1m",
      preAllocatedVUs: 5,
      maxVUs: 15,
      tags: { test_type: "auth_spray" },
      exec: "authSprayAttack",
    },

    // Inference generation load test
    inference_load: {
      executor: "ramping-vus",
      startVUs: 1,
      stages: [
        { duration: "30s", target: 5 },
        { duration: "1m", target: 15 },
        { duration: "30s", target: 0 },
      ],
      tags: { test_type: "inference_load" },
      exec: "inferenceLoadTest",
    },

    // WAF evasion attempts
    waf_evasion: {
      executor: "constant-vus",
      vus: 3,
      duration: "1m",
      tags: { test_type: "waf_evasion" },
      exec: "wafEvasionTest",
    },

    // Bot attack simulation
    bot_attack: {
      executor: "constant-arrival-rate",
      rate: 10,
      timeUnit: "1s",
      duration: "1m",
      preAllocatedVUs: 3,
      maxVUs: 8,
      tags: { test_type: "bot_attack" },
      exec: "botAttackTest",
    },
  },

  thresholds: {
    http_req_duration: ["p(95)<2000"], // 95% of requests under 2s
    rate_limit_429_rate: ["rate>0.1"], // Expect some rate limiting
    waf_block_403_rate: ["rate>0.8"], // WAF should block most attacks
    bot_block_403_rate: ["rate>0.8"], // Bot detection should work
  },
};

// Base URL from environment variable
const BASE_URL = __ENV.BASE_URL || "https://api.aivo.dev";

// Helper function to generate random strings
function randomString(length) {
  const chars =
    "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789";
  let result = "";
  for (let i = 0; i < length; i++) {
    result += chars.charAt(Math.floor(Math.random() * chars.length));
  }
  return result;
}

// Default scenario - normal traffic
export default function () {
  const responses = http.batch([
    ["GET", `${BASE_URL}/api/health`],
    ["GET", `${BASE_URL}/api/models`],
    [
      "POST",
      `${BASE_URL}/api/analytics/events`,
      JSON.stringify({
        event: "page_view",
        page: "/dashboard",
        timestamp: Date.now(),
      }),
      {
        headers: { "Content-Type": "application/json" },
      },
    ],
  ]);

  responses.forEach((response, index) => {
    check(response, {
      [`normal_traffic_${index}_status_ok`]: (r) =>
        r.status === 200 || r.status === 201,
      [`normal_traffic_${index}_response_time_ok`]: (r) =>
        r.timings.duration < 1000,
    });
  });

  sleep(Math.random() * 2 + 1); // Random sleep 1-3 seconds
}

// Authentication spray attack simulation
export function authSprayAttack() {
  const credentials = [
    { username: "admin", password: "password" },
    { username: "admin", password: "123456" },
    { username: "admin", password: "admin" },
    { username: "user", password: "password" },
    { username: "test", password: "test" },
    { username: "administrator", password: "admin123" },
    // SQL injection attempts
    { username: "admin' OR 1=1--", password: "anything" },
    { username: "admin'; DROP TABLE users;--", password: "anything" },
  ];

  const randomCred =
    credentials[Math.floor(Math.random() * credentials.length)];

  const response = http.post(
    `${BASE_URL}/api/auth/login`,
    JSON.stringify(randomCred),
    {
      headers: { "Content-Type": "application/json" },
      tags: { attack_type: "auth_spray" },
    },
  );

  check(response, {
    auth_spray_blocked_or_rate_limited: (r) =>
      r.status === 403 || r.status === 429,
  });

  // Track rate limiting
  rateLimit429Rate.add(response.status === 429);

  // Track WAF blocks (SQL injection should be blocked)
  if (randomCred.username.includes("'") || randomCred.username.includes("--")) {
    wafBlock403Rate.add(response.status === 403);
  }

  sleep(0.1); // Short sleep between attempts
}

// Inference generation load test
export function inferenceLoadTest() {
  const prompts = [
    "Generate a lesson plan for elementary math",
    "Create an educational quiz about photosynthesis",
    "Write a story about space exploration for kids",
    "Explain quantum physics in simple terms",
    "Create flashcards for Spanish vocabulary",
  ];

  const randomPrompt = prompts[Math.floor(Math.random() * prompts.length)];

  const response = http.post(
    `${BASE_URL}/api/inference/generate`,
    JSON.stringify({
      prompt: randomPrompt,
      model: "gpt-3.5-turbo",
      max_tokens: 150,
      temperature: 0.7,
    }),
    {
      headers: {
        "Content-Type": "application/json",
        Authorization: "Bearer test-token",
        "X-User-ID": `user-${Math.floor(Math.random() * 100)}`,
      },
      tags: { endpoint: "inference" },
    },
  );

  check(response, {
    inference_response_valid: (r) =>
      r.status === 200 || r.status === 429 || r.status === 403,
    inference_rate_limit_working: (r) => {
      // After several requests, should hit rate limit
      return r.status === 429 || r.status === 200;
    },
  });

  rateLimit429Rate.add(response.status === 429);

  sleep(1);
}

// WAF evasion test
export function wafEvasionTest() {
  const attacks = [
    // SQL injection variants
    {
      url: `${BASE_URL}/api/auth/login`,
      method: "POST",
      payload: {
        username: "admin' UNION SELECT * FROM users--",
        password: "test",
      },
    },
    {
      url: `${BASE_URL}/api/users/search?q='; DROP TABLE users; --`,
      method: "GET",
    },
    // XSS attempts
    {
      url: `${BASE_URL}/api/users/profile`,
      method: "POST",
      payload: { bio: '<script>alert("xss")</script>' },
    },
    {
      url: `${BASE_URL}/api/search?q=<img src=x onerror=alert("xss")>`,
      method: "GET",
    },
    // Path traversal
    {
      url: `${BASE_URL}/api/files?path=../../../etc/passwd`,
      method: "GET",
    },
    // Command injection
    {
      url: `${BASE_URL}/api/system/info`,
      method: "POST",
      payload: { command: "ls && cat /etc/passwd" },
    },
  ];

  const attack = attacks[Math.floor(Math.random() * attacks.length)];

  let response;
  if (attack.method === "POST") {
    response = http.post(attack.url, JSON.stringify(attack.payload), {
      headers: { "Content-Type": "application/json" },
      tags: { attack_type: "waf_evasion" },
    });
  } else {
    response = http.get(attack.url, {
      tags: { attack_type: "waf_evasion" },
    });
  }

  check(response, {
    waf_blocked_attack: (r) => r.status === 403,
    waf_or_rate_limit_active: (r) => r.status === 403 || r.status === 429,
  });

  wafBlock403Rate.add(response.status === 403);

  sleep(Math.random() * 2);
}

// Bot attack simulation
export function botAttackTest() {
  const maliciousUserAgents = [
    "sqlmap/1.0.12",
    "nikto/2.1.6",
    "Nessus SOAP",
    "w3af.org",
    "masscan/1.0.5",
    "ZmEu",
    "python-requests/2.25.1", // Generic bot signature
    "curl/7.68.0",
  ];

  const userAgent =
    maliciousUserAgents[Math.floor(Math.random() * maliciousUserAgents.length)];

  const response = http.get(`${BASE_URL}/`, {
    headers: { "User-Agent": userAgent },
    tags: { attack_type: "bot_attack" },
  });

  check(response, {
    bot_blocked: (r) => r.status === 403,
    bot_challenged_or_blocked: (r) => r.status === 403 || r.status === 429,
  });

  botBlock403Rate.add(response.status === 403);

  sleep(0.5);
}

// Test geographic controls (requires VPN or proxy)
export function geoControlTest() {
  const countries = ["CN", "RU", "KP", "IR"]; // Blocked countries
  const country = countries[Math.floor(Math.random() * countries.length)];

  const response = http.get(`${BASE_URL}/admin/`, {
    headers: { "CF-IPCountry": country },
    tags: { test_type: "geo_control" },
  });

  check(response, {
    geo_blocked: (r) => r.status === 403,
  });

  sleep(1);
}

// Setup function
export function setup() {
  console.log("Starting AIVO Edge Security Load Tests");
  console.log(`Target URL: ${BASE_URL}`);
  console.log("Test scenarios:");
  console.log("- Normal traffic simulation");
  console.log("- Authentication spray attack");
  console.log("- Inference generation load");
  console.log("- WAF evasion attempts");
  console.log("- Bot attack simulation");

  // Warm up the system
  http.get(`${BASE_URL}/api/health`);
}

// Teardown function
export function teardown(data) {
  console.log("Edge Security Load Tests completed");
}

// Custom summary
export function handleSummary(data) {
  const summary = {
    timestamp: new Date().toISOString(),
    test_duration: data.metrics.iteration_duration?.avg || 0,
    total_requests: data.metrics.http_reqs?.count || 0,

    // Rate limiting metrics
    rate_limited_requests: data.metrics.rate_limit_429_rate?.count || 0,
    rate_limit_effectiveness:
      ((data.metrics.rate_limit_429_rate?.count || 0) /
        (data.metrics.http_reqs?.count || 1)) *
      100,

    // WAF metrics
    waf_blocked_requests: data.metrics.waf_block_403_rate?.count || 0,
    waf_effectiveness:
      ((data.metrics.waf_block_403_rate?.count || 0) /
        (data.metrics.http_reqs?.count || 1)) *
      100,

    // Bot detection metrics
    bot_blocked_requests: data.metrics.bot_block_403_rate?.count || 0,
    bot_detection_effectiveness:
      ((data.metrics.bot_block_403_rate?.count || 0) /
        (data.metrics.http_reqs?.count || 1)) *
      100,

    // Performance metrics
    avg_response_time: data.metrics.http_req_duration?.avg || 0,
    p95_response_time: data.metrics.http_req_duration?.["p(95)"] || 0,

    // Scenarios breakdown
    scenarios: {},
  };

  // Add scenario-specific metrics
  Object.keys(data.metrics).forEach((metric) => {
    if (metric.includes("scenario_")) {
      const scenarioName = metric.split("_")[1];
      if (!summary.scenarios[scenarioName]) {
        summary.scenarios[scenarioName] = {};
      }
      summary.scenarios[scenarioName][metric] = data.metrics[metric];
    }
  });

  return {
    "edge-security-results.json": JSON.stringify(summary, null, 2),
    stdout: textSummary(data, { indent: " ", enableColors: true }),
  };
}
