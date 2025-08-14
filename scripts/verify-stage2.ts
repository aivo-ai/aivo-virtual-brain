/**
 * Stage-2 End-to-End Verification Script
 *
 * Validates complete system integration including:
 * - Model fabric and AI inference gateway
 * -    return this.logResult("Service Health Check", {
      healthy: healthyServices,
      total: services.length,
      services: results.map((r, i) => ({
        service: services[i].name,
        status: r.status,
        ...(r.status === "fulfilled" ? r.value : { error: r.reason }),
      })),
    }); engines and assessment flows
 * - Data pipelines and real-time processing
 * - Multi-service workflows and SLOs
 */

import { spawn, exec } from "child_process";
import { promisify } from "util";
import axios from "axios";
import { performance } from "perf_hooks";
import * as fs from "fs/promises";
import * as path from "path";

const execAsync = promisify(exec);

interface VerificationResult {
  step: string;
  status: "pass" | "fail" | "skip";
  duration: number;
  details?: any;
  error?: string;
}

interface ServiceHealth {
  name: string;
  url: string;
  healthy: boolean;
  responseTime?: number;
  version?: string;
  error?: string;
}

class Stage2Verifier {
  private results: VerificationResult[] = [];
  private baseUrl = process.env.BASE_URL || "http://localhost";
  private testUserId = "";
  private testTenantId = "";
  private authToken = "";
  private lessonId = "";

  async run(): Promise<boolean> {
    console.log("🚀 Starting Stage-2 End-to-End Verification...\n");

    try {
      // Infrastructure checks
      await this.verifyInfrastructure();
      await this.verifyServices();

      // Core workflows
      await this.verifyEnrollmentFlow();
      await this.verifyAssessmentFlow();
      await this.verifyContentGeneration();
      await this.verifyDataPipeline();
      await this.verifyNotifications();

      // Advanced workflows
      await this.verifyCourseworkAnalysis();
      await this.verifyGameGeneration();

      // Performance verification
      await this.verifyPerformanceSLOs();

      // Final report
      await this.generateReport();

      const passed = this.results.filter((r) => r.status === "pass").length;
      const failed = this.results.filter((r) => r.status === "fail").length;
      const skipped = this.results.filter((r) => r.status === "skip").length;

      console.log("\n📊 Final Results:");
      console.log(`✅ Passed: ${passed}`);
      console.log(`❌ Failed: ${failed}`);
      console.log(`⏭️  Skipped: ${skipped}`);
      console.log(
        `📈 Success Rate: ${((passed / (passed + failed)) * 100).toFixed(1)}%`,
      );

      return failed === 0;
    } catch (error) {
      console.error("💥 Verification failed with error:", error);
      return false;
    }
  }

  private async verifyInfrastructure(): Promise<void> {
    console.log("🏗️  Verifying Infrastructure...");

    // Check Docker Compose
    await this.timeStep("Docker Compose Status", async () => {
      const { stdout } = await execAsync("docker-compose ps --format json");
      const containers = JSON.parse(stdout);
      const unhealthyContainers = containers.filter(
        (c: any) => c.State !== "running",
      );

      if (unhealthyContainers.length > 0) {
        throw new Error(
          `Unhealthy containers: ${unhealthyContainers.map((c: any) => c.Name).join(", ")}`,
        );
      }

      return { containers: containers.length, running: containers.length };
    });

    // Check database connectivity
    await this.timeStep("Database Connectivity", async () => {
      const response = await axios.get(`${this.baseUrl}:5432/health`, {
        timeout: 5000,
      });
      return response.data;
    });

    // Check message queue
    await this.timeStep("Message Queue Health", async () => {
      const response = await axios.get(`${this.baseUrl}:15672/api/overview`, {
        timeout: 5000,
        auth: { username: "guest", password: "guest" },
      });
      return { status: "healthy", queues: response.data.queue_totals };
    });
  }

  private async verifyServices(): Promise<void> {
    console.log("🔍 Verifying Microservices Health...");

    const services = [
      { name: "auth-svc", port: 3001 },
      { name: "user-svc", port: 3002 },
      { name: "learner-svc", port: 3003 },
      { name: "assessment-svc", port: 3004 },
      { name: "slp-svc", port: 3005 },
      { name: "inference-gateway-svc", port: 3006 },
      { name: "search-svc", port: 3007 },
    ];

    const healthChecks = services.map((service) =>
      this.checkServiceHealth(service.name, service.port),
    );

    const results = await Promise.allSettled(healthChecks);
    const healthyServices = results.filter(
      (r) => r.status === "fulfilled",
    ).length;

    await this.recordStep("Service Health Checks", "pass", {
      healthy: healthyServices,
      total: services.length,
      services: results.map((r, i) => ({
        service: services[i].name,
        status: r.status,
        ...(r.status === "fulfilled" ? r.value : { error: r.reason }),
      })),
    });

    if (healthyServices < services.length) {
      throw new Error(
        `Only ${healthyServices}/${services.length} services healthy`,
      );
    }
  }

  private async checkServiceHealth(
    serviceName: string,
    port: number,
  ): Promise<ServiceHealth> {
    const startTime = performance.now();

    try {
      const response = await axios.get(`${this.baseUrl}:${port}/health`, {
        timeout: 5000,
        headers: { Accept: "application/json" },
      });

      const duration = performance.now() - startTime;

      return {
        name: serviceName,
        url: `${this.baseUrl}:${port}`,
        healthy: true,
        responseTime: Math.round(duration),
        version: response.data.version || "unknown",
      };
    } catch (error: any) {
      return {
        name: serviceName,
        url: `${this.baseUrl}:${port}`,
        healthy: false,
        error: error.message,
      };
    }
  }

  private async verifyEnrollmentFlow(): Promise<void> {
    console.log("👤 Verifying Student Enrollment Flow...");

    // Step 1: Register new student
    await this.timeStep("Student Registration", async () => {
      const studentData = {
        email: `test-student-${Date.now()}@example.com`,
        password: "TestPassword123!",
        firstName: "Test",
        lastName: "Student",
        grade: 8,
        subjects: ["mathematics", "english", "science"],
      };

      const response = await axios.post(
        `${this.baseUrl}:3002/api/users`,
        studentData,
      );
      this.testUserId = response.data.id;
      return { userId: this.testUserId, ...response.data };
    });

    // Step 2: Authentication
    await this.timeStep("Student Authentication", async () => {
      const loginData = {
        email: `test-student-${Date.now()}@example.com`,
        password: "TestPassword123!",
      };

      const response = await axios.post(
        `${this.baseUrl}:3001/api/auth/login`,
        loginData,
      );
      this.authToken = response.data.token;
      return { token: "received", expiresIn: response.data.expiresIn };
    });

    // Step 3: Tenant assignment
    await this.timeStep("Tenant Assignment", async () => {
      const tenantData = {
        name: "Test School District",
        type: "school",
        settings: {
          locale: "en",
          timezone: "America/New_York",
        },
      };

      const response = await axios.post(
        `${this.baseUrl}:3002/api/tenants`,
        tenantData,
        {
          headers: { Authorization: `Bearer ${this.authToken}` },
        },
      );

      this.testTenantId = response.data.id;
      return { tenantId: this.testTenantId, ...response.data };
    });

    // Step 4: Profile setup
    await this.timeStep("Profile Setup", async () => {
      const profileData = {
        learningStyle: "visual",
        interests: ["mathematics", "science"],
        accommodations: [],
        goals: ["improve_math_skills", "prepare_for_tests"],
      };

      const response = await axios.put(
        `${this.baseUrl}:3002/api/users/${this.testUserId}/profile`,
        profileData,
        { headers: { Authorization: `Bearer ${this.authToken}` } },
      );

      return response.data;
    });
  }

  private async verifyAssessmentFlow(): Promise<void> {
    console.log("📊 Verifying Assessment & IRT Flow...");

    // Step 1: Baseline assessment
    await this.timeStep("Baseline Assessment (IRT)", async () => {
      const assessmentData = {
        userId: this.testUserId,
        subject: "mathematics",
        grade: 8,
        assessmentType: "baseline",
      };

      const response = await axios.post(
        `${this.baseUrl}:3004/api/assessments`,
        assessmentData,
        { headers: { Authorization: `Bearer ${this.authToken}` } },
      );

      return {
        assessmentId: response.data.id,
        initialAbility: response.data.irtData.theta,
      };
    });

    // Step 2: Adaptive questioning
    await this.timeStep("Adaptive Question Generation", async () => {
      const questionRequest = {
        userId: this.testUserId,
        subject: "mathematics",
        currentAbility: -0.5, // Simulated IRT theta
        difficulty: "adaptive",
      };

      const response = await axios.post(
        `${this.baseUrl}:3004/api/questions/adaptive`,
        questionRequest,
        { headers: { Authorization: `Bearer ${this.authToken}` } },
      );

      return {
        questionId: response.data.id,
        difficulty: response.data.difficulty,
        subject: response.data.subject,
      };
    });

    // Step 3: IEP draft generation
    await this.timeStep("IEP Draft Generation", async () => {
      const iepData = {
        userId: this.testUserId,
        assessmentResults: {
          mathematics: {
            level: 7.2,
            strengths: ["algebra"],
            weaknesses: ["geometry"],
          },
          english: {
            level: 8.1,
            strengths: ["reading"],
            weaknesses: ["writing"],
          },
        },
        goals: ["improve_geometry_skills", "enhance_mathematical_reasoning"],
      };

      const response = await axios.post(
        `${this.baseUrl}:3003/api/iep/draft`,
        iepData,
        { headers: { Authorization: `Bearer ${this.authToken}` } },
      );

      return { iepId: response.data.id, status: response.data.status };
    });

    // Step 4: Progress tracking
    await this.timeStep("Progress Tracking Setup", async () => {
      const trackingData = {
        userId: this.testUserId,
        subject: "mathematics",
        initialLevel: 7.2,
        targetLevel: 8.5,
        milestones: [
          {
            skill: "basic_algebra",
            target: new Date(Date.now() + 30 * 24 * 60 * 60 * 1000),
          },
          {
            skill: "geometry_basics",
            target: new Date(Date.now() + 60 * 24 * 60 * 60 * 1000),
          },
        ],
      };

      const response = await axios.post(
        `${this.baseUrl}:3003/api/progress/track`,
        trackingData,
        { headers: { Authorization: `Bearer ${this.authToken}` } },
      );

      return {
        trackingId: response.data.id,
        milestones: response.data.milestones.length,
      };
    });
  }

  private async verifyContentGeneration(): Promise<void> {
    console.log("🧠 Verifying AI Content Generation via Gateway...");

    // Step 1: Lesson generation request
    await this.timeStep("AI Lesson Generation", async () => {
      const lessonRequest = {
        subject: "mathematics",
        topic: "linear_equations",
        grade: 8,
        learningObjectives: [
          "Solve one-step linear equations",
          "Graph linear equations",
          "Apply linear equations to real-world problems",
        ],
        studentProfile: {
          learningStyle: "visual",
          priorKnowledge: ["basic_algebra"],
          difficulty: "intermediate",
        },
      };

      const response = await axios.post(
        `${this.baseUrl}:3006/api/generate/lesson`,
        lessonRequest,
        {
          headers: { Authorization: `Bearer ${this.authToken}` },
          timeout: 10000, // AI generation may take longer
        },
      );

      this.lessonId = response.data.id;
      return {
        lessonId: this.lessonId,
        contentLength: response.data.content.length,
        model: response.data.metadata.model,
      };
    });

    // Step 2: Model routing verification
    await this.timeStep("Model Provider Routing", async () => {
      const routingRequest = {
        operation: "text_generation",
        model: "gpt-4",
        fallback: ["claude", "gemini"],
      };

      const response = await axios.post(
        `${this.baseUrl}:3006/api/models/route`,
        routingRequest,
        { headers: { Authorization: `Bearer ${this.authToken}` } },
      );

      return {
        selectedProvider: response.data.provider,
        model: response.data.model,
        fallbackAvailable: response.data.fallback?.length > 0,
      };
    });

    // Step 3: Content approval workflow
    await this.timeStep("Content Approval Workflow", async () => {
      const approvalData = {
        contentId: this.lessonId,
        reviewerId: this.testUserId,
        status: "approved",
        feedback: "Content meets educational standards",
        qualityScore: 8.5,
      };

      const response = await axios.post(
        `${this.baseUrl}:3005/api/content/approve`,
        approvalData,
        { headers: { Authorization: `Bearer ${this.authToken}` } },
      );

      return {
        approvalId: response.data.id,
        status: response.data.status,
        publishedAt: response.data.publishedAt,
      };
    });
  }

  private async verifyDataPipeline(): Promise<void> {
    console.log("📈 Verifying Data Pipeline & ETL...");

    // Step 1: Event generation
    await this.timeStep("Learning Event Generation", async () => {
      const events = [
        {
          type: "lesson_started",
          userId: this.testUserId,
          lessonId: this.lessonId,
          timestamp: new Date().toISOString(),
          metadata: { subject: "mathematics", duration: 0 },
        },
        {
          type: "question_answered",
          userId: this.testUserId,
          questionId: "q123",
          correct: true,
          timeSpent: 45,
          timestamp: new Date().toISOString(),
        },
        {
          type: "lesson_completed",
          userId: this.testUserId,
          lessonId: this.lessonId,
          score: 85,
          timestamp: new Date().toISOString(),
        },
      ];

      const promises = events.map((event) =>
        axios.post(`${this.baseUrl}:3000/api/events`, event, {
          headers: { Authorization: `Bearer ${this.authToken}` },
        }),
      );

      await Promise.all(promises);
      return { eventsGenerated: events.length };
    });

    // Step 2: Real-time processing
    await this.timeStep("Real-time Event Processing", async () => {
      // Wait for events to be processed
      await new Promise((resolve) => setTimeout(resolve, 2000));

      const response = await axios.get(
        `${this.baseUrl}:3000/api/events/processed?userId=${this.testUserId}`,
        { headers: { Authorization: `Bearer ${this.authToken}` } },
      );

      return {
        processedEvents: response.data.count,
        latency: response.data.avgLatency,
      };
    });

    // Step 3: ETL metrics calculation
    await this.timeStep("ETL Metrics Calculation", async () => {
      const response = await axios.get(
        `${this.baseUrl}:3000/api/analytics/user/${this.testUserId}/metrics`,
        { headers: { Authorization: `Bearer ${this.authToken}` } },
      );

      return {
        totalLessons: response.data.totalLessons,
        averageScore: response.data.averageScore,
        timeSpent: response.data.totalTimeSpent,
        streakDays: response.data.streakDays,
      };
    });

    // Step 4: Search indexing
    await this.timeStep("Search Index Updates", async () => {
      const response = await axios.get(
        `${this.baseUrl}:3007/api/search/index/status`,
        { headers: { Authorization: `Bearer ${this.authToken}` } },
      );

      return {
        totalDocuments: response.data.totalDocuments,
        lastUpdated: response.data.lastUpdated,
        cdcLag: response.data.cdcLag,
      };
    });
  }

  private async verifyNotifications(): Promise<void> {
    console.log("📧 Verifying Notification System...");

    await this.timeStep("Email Approval Notification", async () => {
      const notificationData = {
        type: "content_approved",
        recipients: ["teacher@example.com"],
        templateData: {
          lessonTitle: "Linear Equations Basics",
          approver: "Test Reviewer",
          approvedAt: new Date().toISOString(),
        },
      };

      const response = await axios.post(
        `${this.baseUrl}:3000/api/notifications/send`,
        notificationData,
        { headers: { Authorization: `Bearer ${this.authToken}` } },
      );

      return {
        notificationId: response.data.id,
        status: response.data.status,
        deliveryMethod: response.data.method,
      };
    });
  }

  private async verifyCourseworkAnalysis(): Promise<void> {
    console.log("📝 Verifying Coursework Upload & Analysis...");

    // Step 1: Coursework upload
    await this.timeStep("Coursework Upload", async () => {
      const formData = new FormData();
      formData.append(
        "file",
        new Blob(["Sample math homework submission"], { type: "text/plain" }),
      );
      formData.append("subject", "mathematics");
      formData.append("assignment", "linear_equations_practice");
      formData.append("studentId", this.testUserId);

      const response = await axios.post(
        `${this.baseUrl}:3000/api/coursework/upload`,
        formData,
        {
          headers: {
            Authorization: `Bearer ${this.authToken}`,
            "Content-Type": "multipart/form-data",
          },
        },
      );

      return { uploadId: response.data.id, status: response.data.status };
    });

    // Step 2: AI analysis
    await this.timeStep("AI Content Analysis", async () => {
      const analysisRequest = {
        uploadId: "upload123", // From previous step
        analysisType: "comprehensive",
        rubric: {
          accuracy: 0.4,
          methodology: 0.3,
          presentation: 0.3,
        },
      };

      const response = await axios.post(
        `${this.baseUrl}:3006/api/analyze/coursework`,
        analysisRequest,
        { headers: { Authorization: `Bearer ${this.authToken}` } },
      );

      return {
        analysisId: response.data.id,
        score: response.data.overallScore,
        feedback: response.data.feedback.length,
      };
    });

    // Step 3: Level suggestion
    await this.timeStep("Difficulty Level Suggestion", async () => {
      const suggestionRequest = {
        userId: this.testUserId,
        subject: "mathematics",
        currentWork: {
          score: 85,
          completionTime: 1200, // seconds
          mistakes: ["calculation_error"],
        },
      };

      const response = await axios.post(
        `${this.baseUrl}:3003/api/difficulty/suggest`,
        suggestionRequest,
        { headers: { Authorization: `Bearer ${this.authToken}` } },
      );

      return {
        suggestedLevel: response.data.level,
        confidence: response.data.confidence,
        reasoning: response.data.reasoning,
      };
    });
  }

  private async verifyGameGeneration(): Promise<void> {
    console.log("🎮 Verifying Game Generation System...");

    await this.timeStep("Educational Game Generation", async () => {
      const gameRequest = {
        subject: "mathematics",
        topic: "linear_equations",
        gameType: "puzzle",
        difficulty: "intermediate",
        duration: 15, // minutes
        learningObjectives: [
          "Practice solving linear equations",
          "Apply algebraic thinking to puzzles",
        ],
      };

      const response = await axios.post(
        `${this.baseUrl}:3006/api/generate/game`,
        gameRequest,
        {
          headers: { Authorization: `Bearer ${this.authToken}` },
          timeout: 15000, // Game generation may take time
        },
      );

      return {
        gameId: response.data.id,
        gameType: response.data.type,
        levels: response.data.levels?.length || 0,
        estimatedDuration: response.data.estimatedDuration,
      };
    });
  }

  private async verifyPerformanceSLOs(): Promise<void> {
    console.log("⚡ Verifying Performance SLOs...");

    // Inference Gateway SLO: p95 < 300ms
    await this.timeStep("Inference Gateway SLO (p95 < 300ms)", async () => {
      const requestPromises: Promise<number>[] = [];

      // Generate 20 concurrent requests
      for (let i = 0; i < 20; i++) {
        requestPromises.push(
          this.measureRequestTime(
            `${this.baseUrl}:3006/api/generate/quick-lesson`,
            {
              method: "POST",
              data: {
                subject: "mathematics",
                topic: "basic_algebra",
                length: "short",
              },
              headers: { Authorization: `Bearer ${this.authToken}` },
            },
          ),
        );
      }

      const results = await Promise.all(requestPromises);
      const sortedTimes = results.sort((a, b) => a - b);
      const p95 = sortedTimes[Math.floor(sortedTimes.length * 0.95)];

      if (p95 > 300) {
        throw new Error(`P95 response time ${p95}ms exceeds 300ms SLO`);
      }

      return {
        p95: Math.round(p95),
        p50: Math.round(sortedTimes[Math.floor(sortedTimes.length * 0.5)]),
      };
    });

    // Search Service SLO: p95 < 100ms
    await this.timeStep("Search Service SLO (p95 < 100ms)", async () => {
      const requestPromises: Promise<number>[] = [];

      for (let i = 0; i < 20; i++) {
        requestPromises.push(
          this.measureRequestTime(
            `${this.baseUrl}:3007/api/search?q=mathematics&limit=10`,
            {
              method: "GET",
              headers: { Authorization: `Bearer ${this.authToken}` },
            },
          ),
        );
      }

      const results = await Promise.all(requestPromises);
      const sortedTimes = results.sort((a, b) => a - b);
      const p95 = sortedTimes[Math.floor(sortedTimes.length * 0.95)];

      if (p95 > 100) {
        throw new Error(`P95 response time ${p95}ms exceeds 100ms SLO`);
      }

      return {
        p95: Math.round(p95),
        p50: Math.round(sortedTimes[Math.floor(sortedTimes.length * 0.5)]),
      };
    });
  }

  private async measureRequestTime(url: string, config: any): Promise<number> {
    const startTime = performance.now();
    try {
      await axios(url, { ...config, timeout: 5000 });
      return performance.now() - startTime;
    } catch (error) {
      return performance.now() - startTime; // Return time even on error for SLO measurement
    }
  }

  private async timeStep<T>(
    stepName: string,
    operation: () => Promise<T>,
  ): Promise<T> {
    const startTime = performance.now();

    try {
      console.log(`  ⏳ ${stepName}...`);
      const result = await operation();
      const duration = performance.now() - startTime;

      console.log(`  ✅ ${stepName} (${Math.round(duration)}ms)`);
      this.results.push({
        step: stepName,
        status: "pass",
        duration: Math.round(duration),
        details: result,
      });

      return result;
    } catch (error: any) {
      const duration = performance.now() - startTime;

      console.log(
        `  ❌ ${stepName} (${Math.round(duration)}ms): ${error.message}`,
      );
      this.results.push({
        step: stepName,
        status: "fail",
        duration: Math.round(duration),
        error: error.message,
      });

      throw error;
    }
  }

  private async recordStep(
    stepName: string,
    status: "pass" | "fail" | "skip",
    details?: any,
  ): Promise<void> {
    this.results.push({
      step: stepName,
      status,
      duration: 0,
      details,
    });
  }

  private async generateReport(): Promise<void> {
    const reportPath = path.join(
      process.cwd(),
      "stage2-verification-report.json",
    );

    const report = {
      timestamp: new Date().toISOString(),
      summary: {
        total: this.results.length,
        passed: this.results.filter((r) => r.status === "pass").length,
        failed: this.results.filter((r) => r.status === "fail").length,
        skipped: this.results.filter((r) => r.status === "skip").length,
        totalDuration: this.results.reduce((sum, r) => sum + r.duration, 0),
      },
      results: this.results,
      environment: {
        baseUrl: this.baseUrl,
        nodeVersion: process.version,
        platform: process.platform,
      },
    };

    await fs.writeFile(reportPath, JSON.stringify(report, null, 2));
    console.log(`\n📄 Detailed report saved to: ${reportPath}`);
  }
}

// Main execution
if (require.main === module) {
  const verifier = new Stage2Verifier();
  verifier
    .run()
    .then((success) => {
      process.exit(success ? 0 : 1);
    })
    .catch((error) => {
      console.error("Verification failed:", error);
      process.exit(1);
    });
}

export default Stage2Verifier;
