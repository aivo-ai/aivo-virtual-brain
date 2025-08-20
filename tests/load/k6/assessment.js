import http from "k6/http";
import { check, sleep } from "k6";
import { Rate, Trend } from "k6/metrics";
import { textSummary } from "https://jslib.k6.io/k6-summary/0.0.1/index.js";

// Custom metrics for SLO tracking
export const errorRate = new Rate("assessment_errors");
export const answerDuration = new Trend("assessment_answer_duration");
export const createDuration = new Trend("assessment_create_duration");
export const gradeDuration = new Trend("assessment_grade_duration");

// SLO thresholds
export const options = {
  scenarios: {
    // Smoke test for PRs
    smoke: {
      executor: "constant-vus",
      vus: 3,
      duration: "30s",
      tags: { test_type: "smoke" },
      env: { TEST_TYPE: "smoke" },
    },
    // Load test for nightly runs
    load: {
      executor: "ramping-vus",
      stages: [
        { duration: "2m", target: 15 }, // Ramp up
        { duration: "5m", target: 30 }, // Stay at load
        { duration: "2m", target: 50 }, // Peak load
        { duration: "3m", target: 50 }, // Stay at peak
        { duration: "2m", target: 0 }, // Ramp down
      ],
      tags: { test_type: "load" },
      env: { TEST_TYPE: "load" },
    },
    // Stress test for capacity planning
    stress: {
      executor: "ramping-vus",
      stages: [
        { duration: "2m", target: 50 },
        { duration: "3m", target: 100 },
        { duration: "3m", target: 150 },
        { duration: "2m", target: 0 },
      ],
      tags: { test_type: "stress" },
      env: { TEST_TYPE: "stress" },
    },
  },
  thresholds: {
    // SLO: Assessment answer p95 ≤ 150ms
    "http_req_duration{endpoint:answer}": ["p(95)<150"],
    // Assessment creation should be fast
    "http_req_duration{endpoint:create}": ["p(95)<200"],
    // Grading should be reasonably fast
    "http_req_duration{endpoint:grade}": ["p(95)<300"],
    // Error rate SLO: < 1% for smoke, < 0.5% for load
    assessment_errors: [
      { threshold: "rate<0.01", abortOnFail: true, delayAbortEval: "10s" },
      { threshold: "rate<0.005", abortOnFail: false },
    ],
    // Availability SLO: > 99.9%
    http_req_failed: ["rate<0.001"],
    // Response time SLO compliance
    assessment_answer_duration: ["p(95)<150", "p(99)<250"],
    assessment_create_duration: ["p(95)<200", "p(99)<400"],
    assessment_grade_duration: ["p(95)<300", "p(99)<500"],
  },
};

// Test configuration
const BASE_URL = __ENV.BASE_URL || "http://localhost:8080";
const API_KEY = __ENV.API_KEY || "test-api-key";
const TENANT_ID = __ENV.TENANT_ID || "test-tenant";
const LEARNER_ID = __ENV.LEARNER_ID || "test-learner";

// Test data for assessments
const assessmentTemplates = [
  {
    title: "Math Quiz - Algebra",
    description: "Basic algebra assessment",
    subject: "mathematics",
    grade_level: 9,
    questions: [
      {
        type: "multiple_choice",
        question: "Solve for x: 2x + 5 = 15",
        options: ["x = 5", "x = 10", "x = 15", "x = 20"],
        correct_answer: 0,
        points: 10,
      },
      {
        type: "multiple_choice",
        question: "What is the slope of the line y = 3x + 2?",
        options: ["2", "3", "5", "undefined"],
        correct_answer: 1,
        points: 10,
      },
    ],
  },
  {
    title: "Science Quiz - Physics",
    description: "Basic physics concepts",
    subject: "physics",
    grade_level: 10,
    questions: [
      {
        type: "multiple_choice",
        question: "What is the unit of force?",
        options: ["Joule", "Newton", "Watt", "Pascal"],
        correct_answer: 1,
        points: 15,
      },
      {
        type: "short_answer",
        question: "Define velocity in physics.",
        points: 15,
      },
    ],
  },
  {
    title: "English - Reading Comprehension",
    description: "Reading comprehension assessment",
    subject: "english",
    grade_level: 8,
    questions: [
      {
        type: "multiple_choice",
        question: "What is the main theme of the passage?",
        options: ["Adventure", "Friendship", "Discovery", "Challenge"],
        correct_answer: 2,
        points: 20,
      },
    ],
  },
];

const studentAnswers = [
  { question_id: 1, answer: 0, time_spent: 30 },
  { question_id: 2, answer: 1, time_spent: 45 },
  {
    question_id: 3,
    answer:
      "Velocity is the rate of change of displacement with respect to time.",
    time_spent: 90,
  },
];

export function setup() {
  console.log(`Starting assessment load test against ${BASE_URL}`);
  console.log(`Test type: ${__ENV.TEST_TYPE || "default"}`);

  // Health check
  const healthCheck = http.get(`${BASE_URL}/health`);
  check(healthCheck, {
    "assessment service is healthy": (r) => r.status === 200,
  });

  return {
    baseUrl: BASE_URL,
    apiKey: API_KEY,
    tenantId: TENANT_ID,
    learnerId: LEARNER_ID,
  };
}

export default function (data) {
  const headers = {
    "Content-Type": "application/json",
    Authorization: `Bearer ${data.apiKey}`,
    "X-Tenant-ID": data.tenantId,
    "X-Learner-ID": data.learnerId,
  };

  // Weighted scenario selection
  const scenarios = [
    { name: "create", weight: 0.2 },
    { name: "answer", weight: 0.6 },
    { name: "grade", weight: 0.2 },
  ];

  const random = Math.random();
  let cumulative = 0;
  let selectedScenario = "answer";

  for (const scenario of scenarios) {
    cumulative += scenario.weight;
    if (random <= cumulative) {
      selectedScenario = scenario.name;
      break;
    }
  }

  switch (selectedScenario) {
    case "create":
      testCreateAssessment(data.baseUrl, headers);
      break;
    case "answer":
      testAnswerQuestion(data.baseUrl, headers);
      break;
    case "grade":
      testGradeAssessment(data.baseUrl, headers);
      break;
  }

  // Think time between requests
  sleep(Math.random() * 1.5 + 0.5); // 0.5-2s
}

function testCreateAssessment(baseUrl, headers) {
  const template =
    assessmentTemplates[Math.floor(Math.random() * assessmentTemplates.length)];

  const payload = {
    ...template,
    created_by: "load-test-teacher",
    time_limit: 30 * 60, // 30 minutes
    attempts_allowed: 3,
  };

  const startTime = Date.now();
  const response = http.post(
    `${baseUrl}/api/v1/assessments`,
    JSON.stringify(payload),
    {
      headers,
      tags: { endpoint: "create", subject: template.subject },
    },
  );
  const duration = Date.now() - startTime;

  createDuration.add(duration);

  const success = check(response, {
    "create assessment status is 201": (r) => r.status === 201,
    "create assessment has id": (r) => {
      try {
        const body = JSON.parse(r.body);
        return body.id && body.id.length > 0;
      } catch (e) {
        return false;
      }
    },
    "create assessment response time < 300ms": (r) => duration < 300,
    "create assessment response time < 200ms (SLO)": (r) => duration < 200,
  });

  if (!success) {
    errorRate.add(1);
    console.error(
      `Create assessment failed: ${response.status} - ${response.body}`,
    );
  } else {
    errorRate.add(0);
  }

  if (duration > 200) {
    console.warn(
      `Slow create assessment: ${duration}ms for ${template.subject}`,
    );
  }
}

function testAnswerQuestion(baseUrl, headers) {
  // Simulate answering a question
  const assessmentId = "test-assessment-" + Math.floor(Math.random() * 100);
  const questionId = Math.floor(Math.random() * 5) + 1;

  const payload = {
    assessment_id: assessmentId,
    question_id: questionId,
    answer: Math.floor(Math.random() * 4), // Random multiple choice
    time_spent: Math.floor(Math.random() * 60) + 10, // 10-70 seconds
    is_final: Math.random() > 0.3, // 70% chance of final answer
  };

  const startTime = Date.now();
  const response = http.post(
    `${baseUrl}/api/v1/assessments/${assessmentId}/answers`,
    JSON.stringify(payload),
    {
      headers,
      tags: { endpoint: "answer" },
    },
  );
  const duration = Date.now() - startTime;

  answerDuration.add(duration);

  const success = check(response, {
    "answer question status is 200 or 201": (r) =>
      r.status === 200 || r.status === 201,
    "answer question response time < 200ms": (r) => duration < 200,
    "answer question response time < 150ms (SLO)": (r) => duration < 150,
  });

  if (!success) {
    errorRate.add(1);
    console.error(
      `Answer question failed: ${response.status} - ${response.body}`,
    );
  } else {
    errorRate.add(0);
  }

  if (duration > 150) {
    console.warn(`Slow answer question: ${duration}ms`);
  }
}

function testGradeAssessment(baseUrl, headers) {
  const assessmentId = "test-assessment-" + Math.floor(Math.random() * 100);
  const submissionId = "submission-" + Math.floor(Math.random() * 1000);

  const payload = {
    submission_id: submissionId,
    answers: studentAnswers.slice(0, Math.floor(Math.random() * 3) + 1),
    auto_grade: true,
    feedback_level: "detailed",
  };

  const startTime = Date.now();
  const response = http.post(
    `${baseUrl}/api/v1/assessments/${assessmentId}/grade`,
    JSON.stringify(payload),
    {
      headers,
      tags: { endpoint: "grade" },
    },
  );
  const duration = Date.now() - startTime;

  gradeDuration.add(duration);

  const success = check(response, {
    "grade assessment status is 200": (r) => r.status === 200,
    "grade assessment has score": (r) => {
      try {
        const body = JSON.parse(r.body);
        return typeof body.score === "number" && body.score >= 0;
      } catch (e) {
        return false;
      }
    },
    "grade assessment response time < 400ms": (r) => duration < 400,
    "grade assessment response time < 300ms (SLO)": (r) => duration < 300,
  });

  if (!success) {
    errorRate.add(1);
    console.error(
      `Grade assessment failed: ${response.status} - ${response.body}`,
    );
  } else {
    errorRate.add(0);
  }

  if (duration > 300) {
    console.warn(`Slow grade assessment: ${duration}ms`);
  }
}

export function teardown(data) {
  console.log("Assessment load test completed");

  // Final health check
  const healthCheck = http.get(`${data.baseUrl}/health`);
  check(healthCheck, {
    "assessment service still healthy after test": (r) => r.status === 200,
  });
}

// Custom summary for SLO reporting
export function handleSummary(data) {
  const sloReport = {
    timestamp: new Date().toISOString(),
    service: "assessment",
    test_type: __ENV.TEST_TYPE || "default",
    slo_compliance: {
      answer_p95:
        data.metrics.assessment_answer_duration?.values?.["p(95)"] || 0,
      answer_p95_slo:
        (data.metrics.assessment_answer_duration?.values?.["p(95)"] || 0) <=
        150,
      create_p95:
        data.metrics.assessment_create_duration?.values?.["p(95)"] || 0,
      create_p95_slo:
        (data.metrics.assessment_create_duration?.values?.["p(95)"] || 0) <=
        200,
      grade_p95: data.metrics.assessment_grade_duration?.values?.["p(95)"] || 0,
      grade_p95_slo:
        (data.metrics.assessment_grade_duration?.values?.["p(95)"] || 0) <= 300,
      error_rate: data.metrics.assessment_errors?.values?.rate || 0,
      error_rate_slo:
        (data.metrics.assessment_errors?.values?.rate || 0) < 0.01,
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
      answer_avg: data.metrics.assessment_answer_duration?.values?.avg || 0,
      create_avg: data.metrics.assessment_create_duration?.values?.avg || 0,
      grade_avg: data.metrics.assessment_grade_duration?.values?.avg || 0,
    },
  };

  return {
    stdout: textSummary(data, { indent: " ", enableColors: true }),
    "assessment-slo-report.json": JSON.stringify(sloReport, null, 2),
  };
}
