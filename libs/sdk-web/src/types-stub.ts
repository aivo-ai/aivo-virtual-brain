// Temporary type stubs to resolve compilation issues
// S1-15 Contract & SDK Integration

// Health response types (used by multiple services)
export interface HealthResponse {
  status: string;
  timestamp: string;
  components?: Record<string, string>;
}

// Notification types stub
export type NotificationPriority = "high" | "medium" | "low";
export type NotificationChannel = "email" | "sms" | "push" | "in_app";
export type NotificationStatus = "sent" | "delivered" | "read" | "failed";

export interface NotificationStats {
  total_sent: number;
  total_delivered: number;
  total_read: number;
  total_failed: number;
}

export interface DigestSubscription {
  id: string;
  user_id: string;
  frequency: "daily" | "weekly";
  enabled: boolean;
}

export interface DigestSubscriptionUpdate {
  frequency?: "daily" | "weekly";
  enabled?: boolean;
}

export interface PushSubscriptionResponse {
  id: string;
  endpoint: string;
  enabled: boolean;
}

export interface PushSubscriptionCreate {
  endpoint: string;
  keys: Record<string, string>;
}

// Orchestrator types stub
export interface OrchestrationStats {
  active_learners: number;
  events_processed_today: number;
  avg_response_time_ms: number;
}

export interface LearnerOrchestrationState {
  learner_id: string;
  current_level: number;
  assessment_due: boolean;
  last_activity: string;
}

export interface TriggerEventRequest {
  event_type: string;
  learner_id: string;
  data?: Record<string, any>;
}

export interface TriggerEventResponse {
  success: boolean;
  message: string;
}

export interface OrchestrationEvent {
  id: string;
  event_type: string;
  timestamp: string;
}

export interface OrchestrationAction {
  id: string;
  action_type: string;
  status: string;
}

export interface ActionList {
  actions: OrchestrationAction[];
  total: number;
}

export interface EventList {
  events: OrchestrationEvent[];
  total: number;
}

export interface ListActionsParams {
  limit?: number;
  offset?: number;
}

export interface ListEventsParams {
  limit?: number;
  offset?: number;
}

// Notification API types stub
export interface NotificationCreate {
  recipient_id: string;
  title: string;
  message: string;
  priority?: NotificationPriority;
  channel?: NotificationChannel;
}

export interface NotificationResponse {
  id: string;
  recipient_id: string;
  title: string;
  message: string;
  status: NotificationStatus;
  created_at: string;
}

export interface NotificationListResponse {
  notifications: NotificationResponse[];
  total: number;
}

export interface GetApiV1NotificationsParams {
  limit?: number;
  offset?: number;
  status?: NotificationStatus;
}

export interface PostApiV1NotificationsReadAll200 {
  marked_read: number;
}

export interface GetApiV1NotificationsStatsParams {
  from_date?: string;
  to_date?: string;
}

// System types stub
export interface GetHealth200 {
  status: string;
  timestamp: string;
}

// WebSocket types stub
export interface GetWsStatus200 {
  connected_clients: number;
  status: string;
}

export interface GetWsNotifyParams {
  user_id: string;
  message: string;
}
