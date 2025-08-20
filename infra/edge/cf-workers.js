// Cloudflare Worker for Enhanced Edge Security and Bot Management
// Deploys to: aivo.dev edge locations

// Environment variables configuration
const CONFIG = {
  // Rate limiting configuration
  RATE_LIMITS: {
    login: { requests: 5, window: 60, block: 600 }, // 5 requests per minute, block for 10 min
    generate: { requests: 10, window: 60, block: 300 }, // 10 requests per minute, block for 5 min
    api: { requests: 100, window: 60, block: 60 }, // 100 requests per minute, block for 1 min
    global: { requests: 1000, window: 300, block: 300 }, // 1000 requests per 5 min, block for 5 min
  },

  // Geographic restrictions
  BLOCKED_COUNTRIES: ["CN", "RU", "KP", "IR"],
  ALLOWED_COUNTRIES: ["US", "CA", "GB", "DE", "FR", "AU", "JP", "SG"],

  // Sensitive routes requiring geo-fencing
  SENSITIVE_ROUTES: [
    "/admin",
    "/api/auth",
    "/api/payment",
    "/api/inference/generate",
  ],

  // Bot score thresholds
  BOT_SCORES: {
    block: 10, // Block requests with bot score < 10
    challenge: 30, // Challenge requests with bot score < 30
    allow: 80, // Allow requests with bot score > 80
  },

  // Security headers
  SECURITY_HEADERS: {
    "X-Frame-Options": "DENY",
    "X-Content-Type-Options": "nosniff",
    "X-XSS-Protection": "1; mode=block",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Content-Security-Policy":
      "default-src 'self'; script-src 'self' 'unsafe-inline' https://cdn.aivo.dev; style-src 'self' 'unsafe-inline'; img-src 'self' data: https:; font-src 'self' https://fonts.gstatic.com;",
    "Strict-Transport-Security": "max-age=31536000; includeSubDomains; preload",
    "Permissions-Policy": "geolocation=(), microphone=(), camera=()",
  },
};

// Main request handler
addEventListener("fetch", (event) => {
  event.respondWith(handleRequest(event.request));
});

async function handleRequest(request) {
  try {
    // Get request information
    const url = new URL(request.url);
    const clientIP = request.headers.get("CF-Connecting-IP");
    const country = request.cf.country;
    const userAgent = request.headers.get("User-Agent") || "";
    const method = request.method;
    const path = url.pathname;

    // Security checks
    const securityCheck = await performSecurityChecks(request, {
      clientIP,
      country,
      userAgent,
      method,
      path,
    });

    if (securityCheck.action === "block") {
      return createBlockResponse(securityCheck.reason);
    }

    if (securityCheck.action === "challenge") {
      return createChallengeResponse(securityCheck.reason);
    }

    // Rate limiting checks
    const rateLimitCheck = await checkRateLimits(request, clientIP, path);
    if (rateLimitCheck.exceeded) {
      return createRateLimitResponse(rateLimitCheck.reason);
    }

    // Bot management
    const botCheck = await performBotManagement(request);
    if (botCheck.action === "block") {
      return createBotBlockResponse(botCheck.reason);
    }

    // Fetch response from origin
    const response = await fetch(request);

    // Add security headers
    return addSecurityHeaders(response);
  } catch (error) {
    console.error("Worker error:", error);
    return new Response("Internal Server Error", { status: 500 });
  }
}

// Perform comprehensive security checks
async function performSecurityChecks(request, info) {
  const { clientIP, country, userAgent, method, path } = info;

  // Check for malicious user agents
  const maliciousUAs = [
    "sqlmap",
    "nikto",
    "nessus",
    "openvas",
    "masscan",
    "zmap",
    "w3af",
  ];
  if (maliciousUAs.some((ua) => userAgent.toLowerCase().includes(ua))) {
    await logSecurityEvent("malicious_user_agent", {
      clientIP,
      userAgent,
      path,
    });
    return { action: "block", reason: "Malicious user agent detected" };
  }

  // Check for common attack patterns in URL
  const attackPatterns = [
    /union\s+select/i,
    /drop\s+table/i,
    /insert\s+into/i,
    /delete\s+from/i,
    /'.*or.*1=1/i,
    /<script/i,
    /javascript:/i,
    /\.\.\/\.\.\//,
    /\/etc\/passwd/,
    /cmd\.exe/i,
    /\/bin\/bash/,
  ];

  const urlToCheck = request.url + (await request.clone().text());
  if (attackPatterns.some((pattern) => pattern.test(urlToCheck))) {
    await logSecurityEvent("attack_pattern_detected", {
      clientIP,
      path,
      pattern: "various",
    });
    return { action: "block", reason: "Attack pattern detected" };
  }

  // Geographic restrictions for sensitive routes
  if (CONFIG.SENSITIVE_ROUTES.some((route) => path.startsWith(route))) {
    if (CONFIG.BLOCKED_COUNTRIES.includes(country)) {
      await logSecurityEvent("geo_block", { clientIP, country, path });
      return { action: "block", reason: `Access blocked from ${country}` };
    }

    if (!CONFIG.ALLOWED_COUNTRIES.includes(country)) {
      await logSecurityEvent("geo_challenge", { clientIP, country, path });
      return {
        action: "challenge",
        reason: `Access challenged from ${country}`,
      };
    }
  }

  // Check for rapid authentication attempts
  if (path === "/api/auth/login" && method === "POST") {
    const recentAttempts = await getRecentAuthAttempts(clientIP);
    if (recentAttempts > 10) {
      await logSecurityEvent("auth_spray", {
        clientIP,
        attempts: recentAttempts,
      });
      return {
        action: "challenge",
        reason: "Rapid authentication attempts detected",
      };
    }
  }

  // Admin route protection
  if (path.startsWith("/admin") && method === "POST") {
    const recentAdminAttempts = await getRecentAdminAttempts(clientIP);
    if (recentAdminAttempts > 5) {
      await logSecurityEvent("admin_brute_force", {
        clientIP,
        attempts: recentAdminAttempts,
      });
      return { action: "block", reason: "Admin brute force detected" };
    }
  }

  return { action: "allow", reason: "Security checks passed" };
}

// Rate limiting implementation
async function checkRateLimits(request, clientIP, path) {
  const now = Math.floor(Date.now() / 1000);

  // Determine rate limit configuration based on path
  let rateLimitConfig = CONFIG.RATE_LIMITS.global;

  if (path === "/api/auth/login") {
    rateLimitConfig = CONFIG.RATE_LIMITS.login;
  } else if (path.includes("/api/inference/generate")) {
    rateLimitConfig = CONFIG.RATE_LIMITS.generate;
  } else if (path.startsWith("/api/")) {
    rateLimitConfig = CONFIG.RATE_LIMITS.api;
  }

  // Check IP-based rate limiting
  const ipKey = `rate_limit:ip:${clientIP}:${path}`;
  const ipCount = await incrementCounter(ipKey, rateLimitConfig.window);

  if (ipCount > rateLimitConfig.requests) {
    await logSecurityEvent("rate_limit_exceeded", {
      clientIP,
      path,
      count: ipCount,
      limit: rateLimitConfig.requests,
    });
    return {
      exceeded: true,
      reason: `Rate limit exceeded: ${ipCount}/${rateLimitConfig.requests} requests`,
    };
  }

  // Check user-based rate limiting for authenticated requests
  const authHeader = request.headers.get("Authorization");
  if (authHeader && authHeader.startsWith("Bearer ")) {
    const userId = await extractUserIdFromToken(authHeader);
    if (userId) {
      const userKey = `rate_limit:user:${userId}:${path}`;
      const userCount = await incrementCounter(userKey, 300); // 5-minute window

      if (userCount > 200) {
        // 200 requests per 5 minutes per user
        await logSecurityEvent("user_rate_limit_exceeded", {
          userId,
          path,
          count: userCount,
        });
        return {
          exceeded: true,
          reason: `User rate limit exceeded: ${userCount}/200 requests`,
        };
      }
    }
  }

  return { exceeded: false };
}

// Bot management implementation
async function performBotManagement(request) {
  const botScore = request.cf.botManagement?.score || 100;
  const verifiedBot = request.cf.botManagement?.verifiedBot || false;
  const clientIP = request.headers.get("CF-Connecting-IP");
  const path = new URL(request.url).pathname;

  // Allow verified bots (like Google, Bing)
  if (verifiedBot) {
    return { action: "allow", reason: "Verified bot" };
  }

  // Block very low bot scores
  if (botScore < CONFIG.BOT_SCORES.block) {
    await logSecurityEvent("bot_block", { clientIP, botScore, path });
    return { action: "block", reason: `Low bot score: ${botScore}` };
  }

  // Challenge medium bot scores
  if (botScore < CONFIG.BOT_SCORES.challenge) {
    await logSecurityEvent("bot_challenge", { clientIP, botScore, path });
    return { action: "challenge", reason: `Medium bot score: ${botScore}` };
  }

  return { action: "allow", reason: `Good bot score: ${botScore}` };
}

// Helper functions
async function incrementCounter(key, windowSeconds) {
  const now = Math.floor(Date.now() / 1000);
  const windowStart = now - windowSeconds;

  // Use Cloudflare KV for rate limiting storage
  const existingData = (await RATE_LIMIT_KV.get(key, "json")) || {
    timestamps: [],
  };

  // Filter out old timestamps
  const validTimestamps = existingData.timestamps.filter(
    (ts) => ts > windowStart,
  );
  validTimestamps.push(now);

  // Store updated data
  await RATE_LIMIT_KV.put(
    key,
    JSON.stringify({ timestamps: validTimestamps }),
    {
      expirationTtl: windowSeconds + 60, // Add buffer for cleanup
    },
  );

  return validTimestamps.length;
}

async function getRecentAuthAttempts(clientIP) {
  const key = `auth_attempts:${clientIP}`;
  const data = (await RATE_LIMIT_KV.get(key, "json")) || { count: 0 };
  return data.count || 0;
}

async function getRecentAdminAttempts(clientIP) {
  const key = `admin_attempts:${clientIP}`;
  const data = (await RATE_LIMIT_KV.get(key, "json")) || { count: 0 };
  return data.count || 0;
}

async function extractUserIdFromToken(authHeader) {
  try {
    const token = authHeader.replace("Bearer ", "");
    // This would normally validate and decode the JWT
    // For demo purposes, we'll extract from a simple format
    const payload = JSON.parse(atob(token.split(".")[1]));
    return payload.sub || payload.user_id;
  } catch (error) {
    return null;
  }
}

async function logSecurityEvent(eventType, data) {
  const logData = {
    timestamp: new Date().toISOString(),
    eventType,
    ...data,
  };

  console.log("Security Event:", JSON.stringify(logData));

  // Store in KV for analytics
  const logKey = `security_log:${Date.now()}:${Math.random()}`;
  await SECURITY_LOGS_KV.put(logKey, JSON.stringify(logData), {
    expirationTtl: 86400 * 30, // Keep for 30 days
  });
}

// Response creators
function createBlockResponse(reason) {
  return new Response(
    JSON.stringify({
      error: "Access Blocked",
      reason: reason,
      timestamp: new Date().toISOString(),
    }),
    {
      status: 403,
      headers: {
        "Content-Type": "application/json",
        ...CONFIG.SECURITY_HEADERS,
      },
    },
  );
}

function createChallengeResponse(reason) {
  // In a real implementation, this would trigger a CAPTCHA or similar challenge
  return new Response(
    JSON.stringify({
      error: "Challenge Required",
      reason: reason,
      challenge_url: "/challenge",
      timestamp: new Date().toISOString(),
    }),
    {
      status: 429,
      headers: {
        "Content-Type": "application/json",
        "Retry-After": "60",
        ...CONFIG.SECURITY_HEADERS,
      },
    },
  );
}

function createRateLimitResponse(reason) {
  return new Response(
    JSON.stringify({
      error: "Rate Limited",
      reason: reason,
      timestamp: new Date().toISOString(),
    }),
    {
      status: 429,
      headers: {
        "Content-Type": "application/json",
        "Retry-After": "60",
        ...CONFIG.SECURITY_HEADERS,
      },
    },
  );
}

function createBotBlockResponse(reason) {
  return new Response(
    JSON.stringify({
      error: "Bot Blocked",
      reason: reason,
      timestamp: new Date().toISOString(),
    }),
    {
      status: 403,
      headers: {
        "Content-Type": "application/json",
        ...CONFIG.SECURITY_HEADERS,
      },
    },
  );
}

function addSecurityHeaders(response) {
  const newResponse = new Response(response.body, response);

  // Add security headers
  Object.entries(CONFIG.SECURITY_HEADERS).forEach(([key, value]) => {
    newResponse.headers.set(key, value);
  });

  return newResponse;
}

// Analytics and monitoring endpoint
async function handleAnalyticsRequest(request) {
  const url = new URL(request.url);

  if (url.pathname === "/worker/analytics") {
    const analytics = await getSecurityAnalytics();
    return new Response(JSON.stringify(analytics), {
      headers: { "Content-Type": "application/json" },
    });
  }

  return new Response("Not Found", { status: 404 });
}

async function getSecurityAnalytics() {
  // This would aggregate security events from KV storage
  return {
    timestamp: new Date().toISOString(),
    summary: {
      blocks: "tracked_in_kv",
      challenges: "tracked_in_kv",
      rate_limits: "tracked_in_kv",
      bot_blocks: "tracked_in_kv",
    },
  };
}
