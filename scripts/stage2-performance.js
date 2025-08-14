/**
 * Stage-2 Performance Smoke Tests with K6
 *
 * Tests critical SLOs for inference gateway and other services
 * Validates performance under realistic load conditions
 */

import http from "k6/http";
import { check, sleep } from "k6";
import { Rate, Trend } from "k6/metrics";

// Custom metrics
const errorRate = new Rate("errors");
const gatewayResponseTime = new Trend("gateway_response_time");
const searchResponseTime = new Trend("search_response_time");

// Test configuration
export const options = {
  stages: [
    { duration: "30s", target: 10 }, // Ramp up
    { duration: "1m", target: 50 }, // Load test
    { duration: "30s", target: 10 }, // Scale down
    { duration: "30s", target: 0 }, // Cool down
  ],
  thresholds: {
    // Gateway SLO: p95 < 300ms
    gateway_response_time: ["p(95)<300"],

    // Search SLO: p95 < 100ms
    search_response_time: ["p(95)<100"],

    // Error rate < 1%
    errors: ["rate<0.01"],

    // Overall request duration
    http_req_duration: ["p(95)<500"],

    // Request success rate > 99%
    http_req_failed: ["rate<0.01"],
  },
};

const BASE_URL = __ENV.BASE_URL || "http://localhost";
const AUTH_TOKEN = __ENV.AUTH_TOKEN || "";

// Test data
const testScenarios = [
  {
    name: "lesson_generation",
    endpoint: `${BASE_URL}:3006/api/generate/lesson`,
    payload: {
      subject: "mathematics",
      topic: "linear_equations",
      grade: 8,
      length: "medium",
    },
  },
  {
    name: "quick_assessment",
    endpoint: `${BASE_URL}:3004/api/assessments/quick`,
    payload: {
      subject: "mathematics",
      difficulty: "intermediate",
      questionCount: 5,
    },
  },
  {
    name: "search_query",
    endpoint: `${BASE_URL}:3007/api/search`,
    method: "GET",
    params: "q=algebra+equations&subject=mathematics&limit=20",
  },
];

export function setup() {
  // Setup phase - authenticate and prepare test data
  console.log("Setting up Stage-2 performance tests...");

  // Get auth token if not provided
  if (!AUTH_TOKEN) {
    const loginResponse = http.post(`${BASE_URL}:3001/api/auth/login`, {
      email: "test@example.com",
      password: "TestPassword123!",
    });

    if (loginResponse.status === 200) {
      const token = JSON.parse(loginResponse.body).token;
      return { authToken: token };
    }
  }

  return { authToken: AUTH_TOKEN };
}

export default function (data) {
  const headers = {
    "Content-Type": "application/json",
    Authorization: `Bearer ${data.authToken}`,
  };

  // Test 1: AI Lesson Generation (Gateway SLO)
  testLessonGeneration(headers);

  // Test 2: Search Performance
  testSearchPerformance(headers);

  // Test 3: Assessment Creation
  testAssessmentCreation(headers);

  // Test 4: User Profile Operations
  testUserOperations(headers);

  sleep(1); // 1 second between iterations
}

function testLessonGeneration(headers) {
  const payload = {
    subject: "mathematics",
    topic: getRandomTopic(),
    grade: Math.floor(Math.random() * 4) + 6, // Grades 6-9
    learningObjectives: [
      "Understand core concepts",
      "Apply knowledge to problems",
      "Develop problem-solving skills",
    ],
    studentProfile: {
      learningStyle: getRandomLearningStyle(),
      difficulty: getRandomDifficulty(),
    },
  };

  const response = http.post(
    `${BASE_URL}:3006/api/generate/lesson`,
    JSON.stringify(payload),
    {
      headers,
      timeout: "10s", // AI generation timeout
      tags: { test_type: "lesson_generation" },
    },
  );

  // Record custom metrics
  gatewayResponseTime.add(response.timings.duration);

  const success = check(response, {
    "lesson generation status is 200": (r) => r.status === 200,
    "lesson generation response time < 5s": (r) => r.timings.duration < 5000,
    "response contains lesson content": (r) => {
      if (r.status === 200) {
        const body = JSON.parse(r.body);
        return body.content && body.content.length > 100;
      }
      return false;
    },
    "response contains metadata": (r) => {
      if (r.status === 200) {
        const body = JSON.parse(r.body);
        return body.metadata && body.metadata.model;
      }
      return false;
    },
  });

  if (!success) {
    errorRate.add(1);
  } else {
    errorRate.add(0);
  }
}

function testSearchPerformance(headers) {
  const searchTerms = [
    "algebra equations",
    "geometry shapes",
    "fractions decimals",
    "probability statistics",
    "linear functions",
  ];

  const query = searchTerms[Math.floor(Math.random() * searchTerms.length)];
  const url = `${BASE_URL}:3007/api/search?q=${encodeURIComponent(query)}&subject=mathematics&limit=20`;

  const response = http.get(url, {
    headers,
    tags: { test_type: "search_query" },
  });

  // Record search-specific metrics
  searchResponseTime.add(response.timings.duration);

  const success = check(response, {
    "search status is 200": (r) => r.status === 200,
    "search response time < 200ms": (r) => r.timings.duration < 200,
    "search returns results": (r) => {
      if (r.status === 200) {
        const body = JSON.parse(r.body);
        return body.results && body.results.length > 0;
      }
      return false;
    },
    "search includes relevance scores": (r) => {
      if (r.status === 200) {
        const body = JSON.parse(r.body);
        return (
          body.results && body.results[0] && body.results[0].score !== undefined
        );
      }
      return false;
    },
  });

  if (!success) {
    errorRate.add(1);
  } else {
    errorRate.add(0);
  }
}

function testAssessmentCreation(headers) {
  const payload = {
    subject: getRandomSubject(),
    grade: Math.floor(Math.random() * 6) + 6, // Grades 6-11
    assessmentType: "adaptive",
    questionCount: 10,
    difficulty: getRandomDifficulty(),
    timeLimit: 1800, // 30 minutes
  };

  const response = http.post(
    `${BASE_URL}:3004/api/assessments`,
    JSON.stringify(payload),
    {
      headers,
      tags: { test_type: "assessment_creation" },
    },
  );

  const success = check(response, {
    "assessment creation status is 200": (r) => r.status === 200,
    "assessment response time < 1s": (r) => r.timings.duration < 1000,
    "assessment has questions": (r) => {
      if (r.status === 200) {
        const body = JSON.parse(r.body);
        return body.questions && body.questions.length > 0;
      }
      return false;
    },
  });

  if (!success) {
    errorRate.add(1);
  } else {
    errorRate.add(0);
  }
}

function testUserOperations(headers) {
  const userId = `user-${Math.floor(Math.random() * 1000)}`;

  // Test user profile retrieval
  const response = http.get(`${BASE_URL}:3002/api/users/${userId}/profile`, {
    headers,
    tags: { test_type: "user_profile" },
  });

  const success = check(response, {
    "user profile response time < 150ms": (r) => r.timings.duration < 150,
    "user profile status is 200 or 404": (r) =>
      r.status === 200 || r.status === 404,
  });

  if (!success) {
    errorRate.add(1);
  } else {
    errorRate.add(0);
  }
}

// Helper functions
function getRandomTopic() {
  const topics = [
    "linear_equations",
    "quadratic_functions",
    "geometry_basics",
    "fractions_decimals",
    "probability_statistics",
    "algebraic_expressions",
    "coordinate_geometry",
    "trigonometry_basics",
  ];
  return topics[Math.floor(Math.random() * topics.length)];
}

function getRandomSubject() {
  const subjects = ["mathematics", "english", "science", "social_studies"];
  return subjects[Math.floor(Math.random() * subjects.length)];
}

function getRandomLearningStyle() {
  const styles = ["visual", "auditory", "kinesthetic", "reading"];
  return styles[Math.floor(Math.random() * styles.length)];
}

function getRandomDifficulty() {
  const difficulties = ["beginner", "intermediate", "advanced"];
  return difficulties[Math.floor(Math.random() * difficulties.length)];
}

export function teardown(data) {
  console.log("Stage-2 performance tests completed");
}
