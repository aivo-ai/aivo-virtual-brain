import { offlineFetch } from '../utils/offlineQueue'

const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8080'

// Event Types
export interface LearningEvent {
  id?: string
  sessionId: string
  learnerId: string
  lessonId?: string
  eventType:
    | 'session_start'
    | 'session_end'
    | 'content_view'
    | 'content_interaction'
    | 'game_break_trigger'
    | 'game_break_complete'
    | 'chat_message_sent'
    | 'chat_response_received'
    | 'section_complete'
    | 'lesson_complete'
    | 'lesson_pause'
    | 'lesson_resume'
    | 'error_occurred'
    | 'performance_metric'
  timestamp: string
  data: Record<string, any>
  metadata?: {
    userAgent: string
    platform: string
    viewport: { width: number; height: number }
    connectionType?: string
    deviceType: 'mobile' | 'tablet' | 'desktop'
  }
}

export interface PerformanceMetric {
  sessionId: string
  metricType:
    | 'page_load'
    | 'content_load'
    | 'api_response'
    | 'stream_latency'
    | 'user_engagement'
  value: number
  unit: 'ms' | 'seconds' | 'bytes' | 'count' | 'percentage'
  timestamp: string
  context?: Record<string, any>
}

export interface QueuedEvent {
  event: LearningEvent
  retryCount: number
  queuedAt: string
  status: 'pending' | 'sending' | 'failed' | 'sent'
}

class EventCollectorClient {
  private eventQueue: QueuedEvent[] = []
  private isOnline = navigator.onLine
  private batchSize = 10
  private flushInterval = 5000 // 5 seconds
  private maxRetries = 3
  private flushTimer?: NodeJS.Timeout

  constructor() {
    this.startFlushTimer()
    this.setupOnlineHandlers()
    this.loadPersistedQueue()
  }

  // Send single event
  async sendEvent(
    event: Omit<LearningEvent, 'id' | 'timestamp' | 'metadata'>
  ): Promise<void> {
    const enrichedEvent: LearningEvent = {
      ...event,
      id: `evt_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
      timestamp: new Date().toISOString(),
      metadata: this.getDeviceMetadata(),
    }

    if (this.isOnline) {
      try {
        await this.sendEventToServer(enrichedEvent)
        return
      } catch (error) {
        console.warn('Failed to send event immediately, queuing:', error)
      }
    }

    // Queue the event
    this.queueEvent(enrichedEvent)
  }

  // Send batch of events
  async sendEventBatch(events: LearningEvent[]): Promise<void> {
    if (!this.isOnline) {
      events.forEach(event => this.queueEvent(event))
      return
    }

    try {
      const response = await offlineFetch(
        `${API_BASE}/event-collector-svc/events/batch`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'X-Context': 'learning',
          },
          body: JSON.stringify({ events }),
        },
        'event-collector'
      )

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`)
      }
    } catch (error) {
      console.error('Failed to send event batch:', error)
      events.forEach(event => this.queueEvent(event))
    }
  }

  // Send performance metric
  async sendPerformanceMetric(
    metric: Omit<PerformanceMetric, 'timestamp'>
  ): Promise<void> {
    const enrichedMetric: PerformanceMetric = {
      ...metric,
      timestamp: new Date().toISOString(),
    }

    await this.sendEvent({
      sessionId: metric.sessionId,
      learnerId: 'system',
      eventType: 'performance_metric',
      data: enrichedMetric,
    })
  }

  // Track page view
  async trackPageView(
    sessionId: string,
    learnerId: string,
    page: string,
    lessonId?: string
  ): Promise<void> {
    await this.sendEvent({
      sessionId,
      learnerId,
      lessonId,
      eventType: 'content_view',
      data: {
        page,
        url: window.location.href,
        referrer: document.referrer,
        loadTime: performance.now(),
      },
    })
  }

  // Track user interaction
  async trackInteraction(
    sessionId: string,
    learnerId: string,
    interactionType: string,
    element: string,
    data?: Record<string, any>
  ): Promise<void> {
    await this.sendEvent({
      sessionId,
      learnerId,
      eventType: 'content_interaction',
      data: {
        interactionType,
        element,
        timestamp: performance.now(),
        ...data,
      },
    })
  }

  // Track lesson events
  async trackLessonStart(
    sessionId: string,
    learnerId: string,
    lessonId: string
  ): Promise<void> {
    await this.sendEvent({
      sessionId,
      learnerId,
      lessonId,
      eventType: 'session_start',
      data: {
        startTime: new Date().toISOString(),
        lessonTitle: '', // Should be populated by caller
        expectedDuration: 0, // Should be populated by caller
      },
    })
  }

  async trackLessonEnd(
    sessionId: string,
    learnerId: string,
    lessonId: string,
    timeSpent: number
  ): Promise<void> {
    await this.sendEvent({
      sessionId,
      learnerId,
      lessonId,
      eventType: 'session_end',
      data: {
        endTime: new Date().toISOString(),
        totalTimeSpent: timeSpent,
        completed: true,
      },
    })
  }

  async trackGameBreak(
    sessionId: string,
    learnerId: string,
    lessonId: string,
    gameBreakData: any
  ): Promise<void> {
    await this.sendEvent({
      sessionId,
      learnerId,
      lessonId,
      eventType: 'game_break_trigger',
      data: gameBreakData,
    })
  }

  async trackChatInteraction(
    sessionId: string,
    learnerId: string,
    lessonId: string,
    messageType: 'sent' | 'received',
    messageData: any
  ): Promise<void> {
    await this.sendEvent({
      sessionId,
      learnerId,
      lessonId,
      eventType:
        messageType === 'sent' ? 'chat_message_sent' : 'chat_response_received',
      data: messageData,
    })
  }

  // Private methods
  private async sendEventToServer(event: LearningEvent): Promise<void> {
    const response = await offlineFetch(`${API_BASE}/event-collector-svc/events`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Context': 'learning',
      },
      body: JSON.stringify(event),
    }, 'event-collector')

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`)
    }
  }

  private queueEvent(event: LearningEvent): void {
    const queuedEvent: QueuedEvent = {
      event,
      retryCount: 0,
      queuedAt: new Date().toISOString(),
      status: 'pending',
    }

    this.eventQueue.push(queuedEvent)
    this.persistQueue()
  }

  private startFlushTimer(): void {
    this.flushTimer = setInterval(() => {
      this.flushQueue()
    }, this.flushInterval)
  }

  private async flushQueue(): Promise<void> {
    if (!this.isOnline || this.eventQueue.length === 0) return

    const pendingEvents = this.eventQueue.filter(qe => qe.status === 'pending')
    if (pendingEvents.length === 0) return

    const batch = pendingEvents.slice(0, this.batchSize)

    try {
      // Mark as sending
      batch.forEach(qe => (qe.status = 'sending'))

      await this.sendEventBatch(batch.map(qe => qe.event))

      // Remove sent events from queue
      this.eventQueue = this.eventQueue.filter(qe => !batch.includes(qe))
      this.persistQueue()
    } catch (error) {
      console.error('Failed to flush event queue:', error)

      // Mark as failed and increment retry count
      batch.forEach(qe => {
        qe.status = 'failed'
        qe.retryCount++

        if (qe.retryCount >= this.maxRetries) {
          // Remove events that have exceeded max retries
          this.eventQueue = this.eventQueue.filter(event => event !== qe)
        } else {
          qe.status = 'pending' // Retry
        }
      })

      this.persistQueue()
    }
  }

  private setupOnlineHandlers(): void {
    window.addEventListener('online', () => {
      this.isOnline = true
      this.flushQueue()
    })

    window.addEventListener('offline', () => {
      this.isOnline = false
    })

    // Also flush before page unload
    window.addEventListener('beforeunload', () => {
      if (this.eventQueue.length > 0 && this.isOnline) {
        // Use sendBeacon for final flush attempt
        const events = this.eventQueue.map(qe => qe.event)
        const blob = new Blob([JSON.stringify({ events })], {
          type: 'application/json',
        })
        navigator.sendBeacon(
          `${API_BASE}/event-collector-svc/events/batch`,
          blob
        )
      }
    })
  }

  private loadPersistedQueue(): void {
    try {
      const persistedQueue = localStorage.getItem('event_collector_queue')
      if (persistedQueue) {
        this.eventQueue = JSON.parse(persistedQueue)
      }
    } catch (error) {
      console.error('Failed to load persisted event queue:', error)
      this.eventQueue = []
    }
  }

  private persistQueue(): void {
    try {
      localStorage.setItem(
        'event_collector_queue',
        JSON.stringify(this.eventQueue)
      )
    } catch (error) {
      console.error('Failed to persist event queue:', error)
    }
  }

  private getDeviceMetadata() {
    return {
      userAgent: navigator.userAgent,
      platform: navigator.platform,
      viewport: {
        width: window.innerWidth,
        height: window.innerHeight,
      },
      connectionType: (navigator as any).connection?.effectiveType || 'unknown',
      deviceType: this.getDeviceType(),
    }
  }

  private getDeviceType(): 'mobile' | 'tablet' | 'desktop' {
    const width = window.innerWidth
    if (width < 768) return 'mobile'
    if (width < 1024) return 'tablet'
    return 'desktop'
  }

  // Public methods for queue management
  getQueuedEventsCount(): number {
    return this.eventQueue.filter(qe => qe.status === 'pending').length
  }

  clearQueue(): void {
    this.eventQueue = []
    localStorage.removeItem('event_collector_queue')
  }

  // Cleanup
  destroy(): void {
    if (this.flushTimer) {
      clearInterval(this.flushTimer)
    }
  }
}

export const eventCollectorClient = new EventCollectorClient()
