/**
 * TypeScript SDK for Feature Flag Service
 */

interface EvaluationContext {
  userId?: string;
  sessionId?: string;
  tenantId?: string;
  role?: string;
  gradeBand?: "k-5" | "6-8" | "9-12" | "adult";
  tenantTier?: string;
  variation?: string;
  customAttributes?: Record<string, any>;
}

interface FlagEvaluationRequest {
  flags: string[];
  context: EvaluationContext;
}

interface FlagEvaluationResponse {
  flags: Record<string, any>;
  evaluatedAt: string;
  cacheHit: boolean;
}

interface FlagDefinition {
  key: string;
  name: string;
  description: string;
  flagType: "boolean" | "string" | "number" | "json";
  enabled: boolean;
  defaultValue: any;
  tags: string[];
  createdAt: string;
  updatedAt: string;
}

interface ConfigClientOptions {
  baseUrl: string;
  apiKey?: string;
  timeout?: number;
  retryAttempts?: number;
  cacheTtl?: number;
}

class ConfigClient {
  private baseUrl: string;
  private apiKey?: string;
  private timeout: number;
  private retryAttempts: number;
  private cache: Map<string, { value: any; expiry: number }>;
  private cacheTtl: number;

  constructor(options: ConfigClientOptions) {
    this.baseUrl = options.baseUrl.replace(/\/$/, ""); // Remove trailing slash
    this.apiKey = options.apiKey;
    this.timeout = options.timeout || 5000;
    this.retryAttempts = options.retryAttempts || 3;
    this.cacheTtl = options.cacheTtl || 60000; // 1 minute default
    this.cache = new Map();
  }

  private getHeaders(): Record<string, string> {
    const headers: Record<string, string> = {
      "Content-Type": "application/json",
    };

    if (this.apiKey) {
      headers["Authorization"] = `Bearer ${this.apiKey}`;
    }

    return headers;
  }

  private addContextHeaders(
    headers: Record<string, string>,
    context: EvaluationContext,
  ): void {
    if (context.userId) headers["x-user-id"] = context.userId;
    if (context.sessionId) headers["x-session-id"] = context.sessionId;
    if (context.tenantId) headers["x-tenant-id"] = context.tenantId;
    if (context.role) headers["x-user-role"] = context.role;
    if (context.gradeBand) headers["x-grade-band"] = context.gradeBand;
    if (context.tenantTier) headers["x-tenant-tier"] = context.tenantTier;
    if (context.variation) headers["x-variation"] = context.variation;
  }

  private getCacheKey(key: string, context: EvaluationContext): string {
    const contextStr = JSON.stringify(context);
    return `${key}:${contextStr}`;
  }

  private isCacheValid(expiry: number): boolean {
    return Date.now() < expiry;
  }

  private async fetchWithRetry(
    url: string,
    options: RequestInit,
  ): Promise<Response> {
    let lastError: Error;

    for (let attempt = 1; attempt <= this.retryAttempts; attempt++) {
      try {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), this.timeout);

        const response = await fetch(url, {
          ...options,
          signal: controller.signal,
        });

        clearTimeout(timeoutId);

        if (!response.ok) {
          throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        return response;
      } catch (error) {
        lastError = error as Error;

        if (attempt === this.retryAttempts) {
          break;
        }

        // Exponential backoff
        const delay = Math.min(1000 * Math.pow(2, attempt - 1), 5000);
        await new Promise((resolve) => setTimeout(resolve, delay));
      }
    }

    throw lastError!;
  }

  /**
   * Evaluate a single feature flag
   */
  async evaluateFlag(
    flagKey: string,
    context: EvaluationContext = {},
  ): Promise<any> {
    const cacheKey = this.getCacheKey(flagKey, context);
    const cached = this.cache.get(cacheKey);

    if (cached && this.isCacheValid(cached.expiry)) {
      return cached.value;
    }

    try {
      const headers = this.getHeaders();
      this.addContextHeaders(headers, context);

      const response = await this.fetchWithRetry(
        `${this.baseUrl}/flags/${flagKey}/evaluate`,
        {
          method: "GET",
          headers,
        },
      );

      const data = await response.json();
      const value = data.value;

      // Cache the result
      this.cache.set(cacheKey, {
        value,
        expiry: Date.now() + this.cacheTtl,
      });

      return value;
    } catch (error) {
      console.error(`Failed to evaluate flag ${flagKey}:`, error);
      return null;
    }
  }

  /**
   * Evaluate multiple feature flags
   */
  async evaluateFlags(
    flagKeys: string[],
    context: EvaluationContext = {},
  ): Promise<Record<string, any>> {
    try {
      const payload: FlagEvaluationRequest = {
        flags: flagKeys,
        context,
      };

      const response = await this.fetchWithRetry(
        `${this.baseUrl}/flags/evaluate`,
        {
          method: "POST",
          headers: this.getHeaders(),
          body: JSON.stringify(payload),
        },
      );

      const data: FlagEvaluationResponse = await response.json();

      // Cache individual flag results
      for (const [flagKey, value] of Object.entries(data.flags)) {
        const cacheKey = this.getCacheKey(flagKey, context);
        this.cache.set(cacheKey, {
          value,
          expiry: Date.now() + this.cacheTtl,
        });
      }

      return data.flags;
    } catch (error) {
      console.error("Failed to evaluate flags:", error);
      return {};
    }
  }

  /**
   * Get all applicable flags for user context
   */
  async getUserFlags(
    context: EvaluationContext = {},
  ): Promise<Record<string, any>> {
    try {
      const headers = this.getHeaders();
      this.addContextHeaders(headers, context);

      const response = await this.fetchWithRetry(`${this.baseUrl}/flags/user`, {
        method: "GET",
        headers,
      });

      const data: FlagEvaluationResponse = await response.json();
      return data.flags;
    } catch (error) {
      console.error("Failed to get user flags:", error);
      return {};
    }
  }

  /**
   * List all feature flags
   */
  async listFlags(filters?: {
    tags?: string;
    enabled?: boolean;
  }): Promise<FlagDefinition[]> {
    try {
      const params = new URLSearchParams();
      if (filters?.tags) params.append("tags", filters.tags);
      if (filters?.enabled !== undefined)
        params.append("enabled", filters.enabled.toString());

      const url = `${this.baseUrl}/flags${params.toString() ? `?${params.toString()}` : ""}`;

      const response = await this.fetchWithRetry(url, {
        method: "GET",
        headers: this.getHeaders(),
      });

      return await response.json();
    } catch (error) {
      console.error("Failed to list flags:", error);
      return [];
    }
  }

  /**
   * Get specific flag definition
   */
  async getFlagDefinition(flagKey: string): Promise<FlagDefinition | null> {
    try {
      const response = await this.fetchWithRetry(
        `${this.baseUrl}/flags/${flagKey}`,
        {
          method: "GET",
          headers: this.getHeaders(),
        },
      );

      return await response.json();
    } catch (error) {
      console.error(`Failed to get flag definition for ${flagKey}:`, error);
      return null;
    }
  }

  /**
   * Get chat configuration
   */
  async getChatConfig(context: EvaluationContext = {}): Promise<{
    streamingEnabled: boolean;
    providerOrder: string[];
    context: EvaluationContext;
  }> {
    try {
      const headers = this.getHeaders();
      this.addContextHeaders(headers, context);

      const response = await this.fetchWithRetry(
        `${this.baseUrl}/config/chat`,
        {
          method: "GET",
          headers,
        },
      );

      return await response.json();
    } catch (error) {
      console.error("Failed to get chat config:", error);
      return {
        streamingEnabled: false,
        providerOrder: ["openai", "anthropic"],
        context,
      };
    }
  }

  /**
   * Get games configuration
   */
  async getGamesConfig(context: EvaluationContext = {}): Promise<{
    gamesEnabled: boolean;
    context: EvaluationContext;
  }> {
    try {
      const headers = this.getHeaders();
      this.addContextHeaders(headers, context);

      const response = await this.fetchWithRetry(
        `${this.baseUrl}/config/games`,
        {
          method: "GET",
          headers,
        },
      );

      return await response.json();
    } catch (error) {
      console.error("Failed to get games config:", error);
      return {
        gamesEnabled: false,
        context,
      };
    }
  }

  /**
   * Get SLP configuration
   */
  async getSLPConfig(context: EvaluationContext = {}): Promise<{
    asrProvider: string;
    context: EvaluationContext;
  }> {
    try {
      const headers = this.getHeaders();
      this.addContextHeaders(headers, context);

      const response = await this.fetchWithRetry(`${this.baseUrl}/config/slp`, {
        method: "GET",
        headers,
      });

      return await response.json();
    } catch (error) {
      console.error("Failed to get SLP config:", error);
      return {
        asrProvider: "whisper",
        context,
      };
    }
  }

  /**
   * Get SEL configuration
   */
  async getSELConfig(context: EvaluationContext = {}): Promise<{
    selEnabled: boolean;
    context: EvaluationContext;
  }> {
    try {
      const headers = this.getHeaders();
      this.addContextHeaders(headers, context);

      const response = await this.fetchWithRetry(`${this.baseUrl}/config/sel`, {
        method: "GET",
        headers,
      });

      return await response.json();
    } catch (error) {
      console.error("Failed to get SEL config:", error);
      return {
        selEnabled: false,
        context,
      };
    }
  }

  /**
   * Refresh flags cache on server
   */
  async refreshCache(): Promise<boolean> {
    try {
      await this.fetchWithRetry(`${this.baseUrl}/flags/refresh`, {
        method: "POST",
        headers: this.getHeaders(),
      });

      return true;
    } catch (error) {
      console.error("Failed to refresh cache:", error);
      return false;
    }
  }

  /**
   * Clear local cache
   */
  clearCache(): void {
    this.cache.clear();
  }

  /**
   * Health check
   */
  async healthCheck(): Promise<boolean> {
    try {
      const response = await this.fetchWithRetry(`${this.baseUrl}/health`, {
        method: "GET",
        headers: this.getHeaders(),
      });

      const data = await response.json();
      return data.status === "healthy";
    } catch (error) {
      return false;
    }
  }
}

// Default client instance
let defaultClient: ConfigClient | null = null;

/**
 * Initialize the default config client
 */
export function initializeConfigClient(
  options: ConfigClientOptions,
): ConfigClient {
  defaultClient = new ConfigClient(options);
  return defaultClient;
}

/**
 * Get the default config client
 */
export function getConfigClient(): ConfigClient {
  if (!defaultClient) {
    throw new Error(
      "Config client not initialized. Call initializeConfigClient() first.",
    );
  }
  return defaultClient;
}

/**
 * Convenience functions using default client
 */
export async function evaluateFlag(
  flagKey: string,
  context?: EvaluationContext,
): Promise<any> {
  return getConfigClient().evaluateFlag(flagKey, context);
}

export async function evaluateFlags(
  flagKeys: string[],
  context?: EvaluationContext,
): Promise<Record<string, any>> {
  return getConfigClient().evaluateFlags(flagKeys, context);
}

export async function getUserFlags(
  context?: EvaluationContext,
): Promise<Record<string, any>> {
  return getConfigClient().getUserFlags(context);
}

export {
  ConfigClient,
  type EvaluationContext,
  type FlagEvaluationRequest,
  type FlagEvaluationResponse,
  type FlagDefinition,
  type ConfigClientOptions,
};
