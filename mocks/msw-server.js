// AIVO MSW Mock Server
// S1-15 Contract & SDK Integration

import express from "express";
import cors from "cors";
import { handlers } from "./msw-handlers.js";

const app = express();
const PORT = 4020;

// Middleware
app.use(cors());
app.use(express.json());

// Health check endpoint
app.get("/health", (req, res) => {
  res.json({
    status: "healthy",
    timestamp: new Date().toISOString(),
    services: [
      "auth-svc",
      "user-svc",
      "assessment-svc",
      "learner-svc",
      "notification-svc",
      "search-svc",
      "orchestrator-svc",
    ],
  });
});

// Apply MSW handlers to Express routes
handlers.forEach((handler) => {
  const { method, path } = handler.info;
  const route = path.pathname.replace(/:\w+/g, (match) => match.slice(1));

  app[method.toLowerCase()](route, (req, res) => {
    // Create MSW-compatible request object
    const mswReq = {
      method: method.toUpperCase(),
      url: new URL(req.originalUrl, `http://localhost:${PORT}`),
      params: req.params,
      body: req.body,
      headers: req.headers,
    };

    // Create MSW-compatible response helpers
    const ctx = {
      status: (code) => ({ status: code }),
      json: (data) => ({ json: data }),
      text: (data) => ({ text: data }),
    };

    const mswRes = {
      status: (code) => {
        res.status(code);
        return mswRes;
      },
      json: (data) => {
        res.json(data);
        return mswRes;
      },
    };

    // Execute handler
    try {
      const result = handler.resolver(mswReq, mswRes, ctx);
      if (result && typeof result.then === "function") {
        result.catch((err) => {
          console.error("Handler error:", err);
          res.status(500).json({ error: "Internal server error" });
        });
      }
    } catch (error) {
      console.error("Handler execution error:", error);
      res.status(500).json({ error: "Internal server error" });
    }
  });
});

// Start server
app.listen(PORT, () => {
  console.log(`🔧 AIVO MSW Mock Server running on http://localhost:${PORT}`);
  console.log(
    `📋 Available services: auth, user, assessment, learner, notification, search, orchestrator`,
  );
  console.log(`🏥 Health check: http://localhost:${PORT}/health`);
});

export default app;
