// AIVO Mock Service Workers - API Handlers
// S1-15 Contract & SDK Integration

import { rest } from "msw";
import { faker } from "@faker-js/faker";

// Base URL configurations
const BASE_URLS = {
  auth: "http://localhost:8000",
  user: "http://localhost:8000",
  assessment: "http://localhost:8010",
  learner: "http://localhost:8001",
  notification: "http://localhost:8003",
  search: "http://localhost:8004",
  orchestrator: "http://localhost:8080",
};

// Helper function to generate consistent UUIDs
const generateId = () => faker.string.uuid();
const generateTimestamp = () => new Date().toISOString();

// Auth Service Handlers
const authHandlers = [
  rest.get(`${BASE_URLS.auth}/auth/health`, (req, res, ctx) => {
    return res(
      ctx.json({
        status: "healthy",
        timestamp: generateTimestamp(),
      }),
    );
  }),

  rest.post(`${BASE_URLS.auth}/auth/login`, (req, res, ctx) => {
    return res(
      ctx.json({
        access_token: faker.string.alphanumeric(40),
        token_type: "bearer",
        expires_in: 3600,
        user: {
          id: generateId(),
          email: faker.internet.email(),
          name: faker.person.fullName(),
        },
      }),
    );
  }),
];

// Assessment Service Handlers
const assessmentHandlers = [
  rest.get(`${BASE_URLS.assessment}/health`, (req, res, ctx) => {
    return res(
      ctx.json({
        status: "healthy",
        timestamp: generateTimestamp(),
        components: {
          database: "healthy",
          irt_engine: "healthy",
        },
      }),
    );
  }),

  rest.post(`${BASE_URLS.assessment}/assessments`, (req, res, ctx) => {
    return res(
      ctx.status(201),
      ctx.json({
        id: generateId(),
        tenant_id: generateId(),
        learner_id: generateId(),
        assessment_type: "baseline",
        title: "Sample Baseline Assessment",
        description: "Initial assessment for skill evaluation",
        status: "active",
        questions: Array.from({ length: 10 }, () => ({
          id: generateId(),
          question_text: faker.lorem.sentence() + "?",
          question_type: "multiple_choice",
          options: Array.from({ length: 4 }, () => faker.lorem.words(3)),
          difficulty: faker.number.float({ min: 0.1, max: 0.9 }),
          subject_area: faker.helpers.arrayElement([
            "math",
            "reading",
            "science",
          ]),
        })),
        created_at: generateTimestamp(),
        updated_at: generateTimestamp(),
      }),
    );
  }),

  rest.get(`${BASE_URLS.assessment}/assessments/:id`, (req, res, ctx) => {
    const { id } = req.params;
    return res(
      ctx.json({
        id,
        tenant_id: generateId(),
        learner_id: generateId(),
        assessment_type: "baseline",
        title: "Sample Assessment",
        status: "active",
        questions: [],
        created_at: generateTimestamp(),
      }),
    );
  }),

  rest.post(
    `${BASE_URLS.assessment}/baselines/:id/complete`,
    (req, res, ctx) => {
      return res(
        ctx.json({
          assessment_id: req.params.id,
          overall_score: faker.number.float({ min: 0.4, max: 0.95 }),
          percentile: faker.number.int({ min: 20, max: 95 }),
          strengths: ["reading comprehension", "basic arithmetic"],
          challenges: ["writing mechanics", "complex problem solving"],
          recommended_level: "moderate",
          event_published: true,
          event_id: generateId(),
        }),
      );
    },
  ),
];

// Learner Service Handlers
const learnerHandlers = [
  rest.get(`${BASE_URLS.learner}/health`, (req, res, ctx) => {
    return res(
      ctx.json({
        status: "healthy",
        timestamp: generateTimestamp(),
        components: {
          database: "healthy",
          private_brain: "healthy",
          model_bindings: "healthy",
        },
      }),
    );
  }),

  rest.post(`${BASE_URLS.learner}/learners`, (req, res, ctx) => {
    const learnerId = generateId();
    return res(
      ctx.status(201),
      ctx.json({
        id: learnerId,
        tenant_id: generateId(),
        user_id: generateId(),
        name: faker.person.fullName(),
        grade_level: "5th",
        current_level: "moderate",
        private_brain: {
          id: generateId(),
          learner_id: learnerId,
          persona_name: "Alex the Helper",
          personality_traits: {
            curiosity: 0.8,
            patience: 0.9,
            encouragement: 0.85,
            creativity: 0.7,
          },
          communication_style: "encouraging",
          learning_approach: "mixed",
        },
        model_bindings: [
          {
            id: generateId(),
            provider: "openai",
            model_name: "gpt-4",
            is_default: true,
            capabilities: ["text_generation", "math_solving"],
          },
        ],
        created_at: generateTimestamp(),
      }),
    );
  }),

  rest.put(`${BASE_URLS.learner}/learners/:id/level`, (req, res, ctx) => {
    return res(
      ctx.json({
        previous_level: "moderate",
        new_level: "challenging",
        reason: "High performance on recent assessments",
        confidence: 0.85,
        updated_at: generateTimestamp(),
        event_published: true,
      }),
    );
  }),

  rest.get(`${BASE_URLS.learner}/learners/:id/brain`, (req, res, ctx) => {
    return res(
      ctx.json({
        id: generateId(),
        learner_id: req.params.id,
        persona_name: "Sam the Study Buddy",
        personality_traits: {
          curiosity: 0.75,
          patience: 0.9,
          encouragement: 0.8,
          creativity: 0.65,
        },
        communication_style: "casual",
        learning_approach: "visual",
        strengths: ["mathematics", "logical reasoning"],
        growth_areas: ["creative writing", "public speaking"],
        created_at: generateTimestamp(),
      }),
    );
  }),
];

// Notification Service Handlers
const notificationHandlers = [
  rest.get(`${BASE_URLS.notification}/health`, (req, res, ctx) => {
    return res(
      ctx.json({
        status: "healthy",
        timestamp: generateTimestamp(),
        components: {
          websocket_hub: "healthy",
          push_service: "healthy",
          digest_scheduler: "healthy",
        },
      }),
    );
  }),

  rest.post(`${BASE_URLS.notification}/notifications`, (req, res, ctx) => {
    return res(
      ctx.status(201),
      ctx.json({
        id: generateId(),
        tenant_id: generateId(),
        user_id: generateId(),
        type: "game_break",
        title: "Time for a Brain Break!",
        message: "Take a 5-minute movement break to recharge.",
        channels: ["websocket", "push"],
        status: "sent",
        created_at: generateTimestamp(),
      }),
    );
  }),

  rest.post(
    `${BASE_URLS.notification}/notifications/schedule`,
    (req, res, ctx) => {
      return res(
        ctx.json({
          id: generateId(),
          scheduled_for: new Date(Date.now() + 5 * 60 * 1000).toISOString(),
          notification: {
            type: "game_break",
            title: "Scheduled Break Reminder",
            message: "Your break is ready!",
          },
          status: "scheduled",
        }),
      );
    },
  ),
];

// Search Service Handlers
const searchHandlers = [
  rest.get(`${BASE_URLS.search}/health`, (req, res, ctx) => {
    return res(
      ctx.json({
        status: "healthy",
        timestamp: generateTimestamp(),
        components: {
          opensearch: "healthy",
          indexer: "healthy",
          rbac_filter: "healthy",
        },
      }),
    );
  }),

  rest.post(`${BASE_URLS.search}/search`, (req, res, ctx) => {
    return res(
      ctx.json({
        query: req.url.searchParams.get("q") || "sample query",
        results: Array.from({ length: 5 }, () => ({
          id: generateId(),
          type: faker.helpers.arrayElement(["iep", "assessment", "resource"]),
          title: faker.lorem.sentence(),
          excerpt: faker.lorem.paragraph(),
          score: faker.number.float({ min: 0.5, max: 1.0 }),
          metadata: {
            student_id: generateId(),
            school_id: generateId(),
            created_at: generateTimestamp(),
          },
        })),
        total_results: faker.number.int({ min: 5, max: 50 }),
        facets: {
          document_type: {
            iep: faker.number.int({ min: 1, max: 10 }),
            assessment: faker.number.int({ min: 1, max: 8 }),
            resource: faker.number.int({ min: 1, max: 15 }),
          },
        },
      }),
    );
  }),

  rest.get(`${BASE_URLS.search}/suggestions`, (req, res, ctx) => {
    const query = req.url.searchParams.get("q") || "";
    return res(
      ctx.json({
        suggestions: Array.from(
          { length: 3 },
          () => query + " " + faker.lorem.words(2),
        ),
        query,
      }),
    );
  }),
];

// Orchestrator Service Handlers
const orchestratorHandlers = [
  rest.get(`${BASE_URLS.orchestrator}/health`, (req, res, ctx) => {
    return res(
      ctx.json({
        status: "healthy",
        timestamp: generateTimestamp(),
        components: {
          event_consumer: "healthy",
          orchestration_engine: "healthy",
          redis_connection: "healthy",
          service_clients: {
            "learner-svc": "healthy",
            "notification-svc": "healthy",
          },
        },
      }),
    );
  }),

  rest.get(`${BASE_URLS.orchestrator}/stats`, (req, res, ctx) => {
    return res(
      ctx.json({
        total_events_processed: faker.number.int({ min: 100, max: 5000 }),
        level_suggestions_sent: faker.number.int({ min: 20, max: 500 }),
        game_breaks_scheduled: faker.number.int({ min: 50, max: 800 }),
        sel_interventions_triggered: faker.number.int({ min: 5, max: 100 }),
        learning_path_updates: faker.number.int({ min: 30, max: 400 }),
        active_learners: faker.number.int({ min: 10, max: 200 }),
        is_initialized: true,
        uptime_seconds: faker.number.int({ min: 3600, max: 86400 }),
        last_event_processed_at: generateTimestamp(),
      }),
    );
  }),

  rest.post(`${BASE_URLS.orchestrator}/internal/trigger`, (req, res, ctx) => {
    return res(
      ctx.json({
        event_id: generateId(),
        actions_generated: [
          {
            id: generateId(),
            type: "LEVEL_SUGGESTED",
            target_service: "learner-svc",
            action_data: {
              level: "challenging",
              reason: "High performance on baseline assessment",
              confidence: 0.85,
            },
            status: "completed",
            created_at: generateTimestamp(),
          },
        ],
        processing_time_ms: faker.number.int({ min: 50, max: 500 }),
      }),
    );
  }),

  rest.get(`${BASE_URLS.orchestrator}/learners/:id/state`, (req, res, ctx) => {
    return res(
      ctx.json({
        learner_id: req.params.id,
        tenant_id: generateId(),
        current_level: faker.helpers.arrayElement([
          "beginner",
          "easy",
          "moderate",
          "challenging",
          "advanced",
        ]),
        engagement_score: faker.number.float({ min: 0.3, max: 0.95 }),
        performance_score: faker.number.float({ min: 0.4, max: 0.9 }),
        consecutive_correct: faker.number.int({ min: 0, max: 8 }),
        consecutive_incorrect: faker.number.int({ min: 0, max: 3 }),
        session_duration_minutes: faker.number.int({ min: 5, max: 45 }),
        baseline_established: true,
        recent_assessments: [],
        sel_alerts: [],
        updated_at: generateTimestamp(),
      }),
    );
  }),
];

// Export all handlers
export const handlers = [
  ...authHandlers,
  ...assessmentHandlers,
  ...learnerHandlers,
  ...notificationHandlers,
  ...searchHandlers,
  ...orchestratorHandlers,
];

export default handlers;
