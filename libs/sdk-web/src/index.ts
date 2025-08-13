// AIVO SDK Web - Main Entry Point
// S1-15 Contract & SDK Integration

// REST API Clients - export individual service APIs
export * from "./api/notifications/notifications";
export * from "./api/default/default";
export * from "./api/system/system";
export * from "./api/statistics/statistics";
export * from "./api/daily-digest/daily-digest";
export * from "./api/push-subscriptions/push-subscriptions";
export * from "./api/web-socket/web-socket";

// Skip type exports for now to avoid conflicts
// export * from './types';

// SDK Configuration
export interface AivoSDKConfig {
  baseURL?: string;
  apiKey?: string;
  timeout?: number;
  retries?: number;
}

// SDK Client Factory
export class AivoSDK {
  private config: AivoSDKConfig;

  constructor(config: AivoSDKConfig = {}) {
    this.config = {
      baseURL: "http://localhost:8000",
      timeout: 30000,
      retries: 3,
      ...config,
    };
  }
}

export default AivoSDK;
