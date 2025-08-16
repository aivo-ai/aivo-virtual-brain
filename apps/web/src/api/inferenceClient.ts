const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8080'

// Inference Types
export interface ChatMessage {
  id: string
  role: 'user' | 'assistant' | 'system'
  content: string
  timestamp: string
  metadata?: {
    lessonId?: string
    sessionId?: string
    confidence?: number
    modelUsed?: string
  }
}

export interface ChatSession {
  id: string
  learnerId: string
  lessonId: string
  messages: ChatMessage[]
  status: 'active' | 'paused' | 'completed'
  createdAt: string
  updatedAt: string
  context: {
    learnerLevel: string
    currentTopic: string
    learningObjectives: string[]
    previousConcepts: string[]
  }
}

export interface StreamResponse {
  id: string
  object: 'chat.completion.chunk'
  choices: Array<{
    delta: {
      content?: string
      role?: string
    }
    finish_reason?: 'stop' | 'length' | 'content_filter'
    index: number
  }>
  usage?: {
    prompt_tokens: number
    completion_tokens: number
    total_tokens: number
  }
}

export interface InferenceRequest {
  sessionId: string
  message: string
  context?: {
    lessonId: string
    currentContent?: string
    learnerPreferences?: Record<string, any>
  }
  stream?: boolean
}

export interface QueuedPrompt {
  id: string
  sessionId: string
  message: string
  context?: any
  timestamp: string
  retryCount: number
  status: 'pending' | 'sending' | 'failed' | 'completed'
}

class InferenceClient {
  private offlineQueue: QueuedPrompt[] = []
  private isOnline = navigator.onLine
  private maxRetries = 3

  constructor() {
    // Listen for online/offline events
    window.addEventListener('online', this.handleOnline.bind(this))
    window.addEventListener('offline', this.handleOffline.bind(this))
  }

  // Start new chat session
  async startChatSession(
    learnerId: string,
    lessonId: string
  ): Promise<ChatSession> {
    const response = await fetch(
      `${API_BASE}/inference-gateway-svc/chat/sessions`,
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Context': 'learning',
        },
        body: JSON.stringify({
          learnerId,
          lessonId,
          context: {
            learnerLevel: 'auto-detect',
            currentTopic: 'lesson-content',
            learningObjectives: [],
            previousConcepts: [],
          },
        }),
      }
    )

    if (!response.ok) throw new Error('Failed to start chat session')
    return response.json()
  }

  // Get existing chat session
  async getChatSession(sessionId: string): Promise<ChatSession> {
    const response = await fetch(
      `${API_BASE}/inference-gateway-svc/chat/sessions/${sessionId}`,
      {
        headers: {
          'Content-Type': 'application/json',
          'X-Context': 'learning',
        },
      }
    )

    if (!response.ok) throw new Error('Failed to get chat session')
    return response.json()
  }

  // Send message with streaming response
  async sendMessage(
    request: InferenceRequest,
    onChunk?: (chunk: string) => void,
    onComplete?: (fullResponse: string) => void,
    onError?: (error: Error) => void
  ): Promise<void> {
    // Check if online, if not queue the message
    if (!this.isOnline) {
      this.queueMessage(request)
      return
    }

    try {
      const response = await fetch(
        `${API_BASE}/inference-gateway-svc/chat/stream`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            Accept: 'text/event-stream',
            'X-Context': 'learning',
          },
          body: JSON.stringify({
            ...request,
            stream: true,
          }),
        }
      )

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`)
      }

      const reader = response.body?.getReader()
      if (!reader) throw new Error('No response body reader available')

      const decoder = new TextDecoder()
      let fullResponse = ''

      try {
        while (true) {
          const { done, value } = await reader.read()
          if (done) break

          const chunk = decoder.decode(value, { stream: true })
          const lines = chunk.split('\n')

          for (const line of lines) {
            if (line.startsWith('data: ')) {
              const data = line.slice(6).trim()

              if (data === '[DONE]') {
                onComplete?.(fullResponse)
                return
              }

              try {
                const parsed: StreamResponse = JSON.parse(data)
                const content = parsed.choices[0]?.delta?.content || ''

                if (content) {
                  fullResponse += content
                  onChunk?.(content)
                }

                if (parsed.choices[0]?.finish_reason === 'stop') {
                  onComplete?.(fullResponse)
                  return
                }
              } catch (parseError) {
                // Skip invalid JSON chunks
                continue
              }
            }
          }
        }
      } finally {
        reader.releaseLock()
      }
    } catch (error) {
      onError?.(error as Error)

      // Queue the message for retry if it's a network error
      if (
        !this.isOnline ||
        (error as Error).message.includes('Failed to fetch')
      ) {
        this.queueMessage(request)
      }
    }
  }

  // Send regular non-streaming message
  async sendMessageSync(request: InferenceRequest): Promise<ChatMessage> {
    if (!this.isOnline) {
      this.queueMessage(request)
      throw new Error('Currently offline. Message queued for retry.')
    }

    const response = await fetch(
      `${API_BASE}/inference-gateway-svc/chat/message`,
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Context': 'learning',
        },
        body: JSON.stringify({
          ...request,
          stream: false,
        }),
      }
    )

    if (!response.ok) {
      this.queueMessage(request)
      throw new Error('Failed to send message')
    }

    return response.json()
  }

  // Queue message for offline retry
  private queueMessage(request: InferenceRequest): void {
    const queuedPrompt: QueuedPrompt = {
      id: `queued_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
      sessionId: request.sessionId,
      message: request.message,
      context: request.context,
      timestamp: new Date().toISOString(),
      retryCount: 0,
      status: 'pending',
    }

    this.offlineQueue.push(queuedPrompt)

    // Persist to localStorage
    localStorage.setItem(
      'inference_offline_queue',
      JSON.stringify(this.offlineQueue)
    )
  }

  // Handle coming back online
  private async handleOnline(): Promise<void> {
    this.isOnline = true

    // Load any persisted queue
    const persistedQueue = localStorage.getItem('inference_offline_queue')
    if (persistedQueue) {
      try {
        this.offlineQueue = JSON.parse(persistedQueue)
      } catch (error) {
        console.error('Failed to parse persisted offline queue:', error)
      }
    }

    // Process offline queue
    await this.processOfflineQueue()
  }

  // Handle going offline
  private handleOffline(): void {
    this.isOnline = false
  }

  // Process queued messages when back online
  private async processOfflineQueue(): Promise<void> {
    const queue = [...this.offlineQueue]
    this.offlineQueue = []

    for (const queuedPrompt of queue) {
      if (queuedPrompt.retryCount >= this.maxRetries) {
        console.warn('Max retries reached for queued message:', queuedPrompt.id)
        continue
      }

      try {
        queuedPrompt.status = 'sending'
        queuedPrompt.retryCount++

        await this.sendMessageSync({
          sessionId: queuedPrompt.sessionId,
          message: queuedPrompt.message,
          context: queuedPrompt.context,
        })

        queuedPrompt.status = 'completed'
      } catch (error) {
        queuedPrompt.status = 'failed'

        if (queuedPrompt.retryCount < this.maxRetries) {
          // Re-queue for another retry
          this.offlineQueue.push(queuedPrompt)
        }
      }
    }

    // Update persisted queue
    localStorage.setItem(
      'inference_offline_queue',
      JSON.stringify(this.offlineQueue)
    )
  }

  // Get queued messages count
  getQueuedMessagesCount(): number {
    return this.offlineQueue.filter(msg => msg.status === 'pending').length
  }

  // Clear offline queue
  clearOfflineQueue(): void {
    this.offlineQueue = []
    localStorage.removeItem('inference_offline_queue')
  }

  // Update chat context
  async updateChatContext(
    sessionId: string,
    context: Partial<ChatSession['context']>
  ): Promise<void> {
    const response = await fetch(
      `${API_BASE}/inference-gateway-svc/chat/sessions/${sessionId}/context`,
      {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
          'X-Context': 'learning',
        },
        body: JSON.stringify(context),
      }
    )

    if (!response.ok) throw new Error('Failed to update chat context')
  }

  // Get chat history
  async getChatHistory(sessionId: string, limit = 50): Promise<ChatMessage[]> {
    const response = await fetch(
      `${API_BASE}/inference-gateway-svc/chat/sessions/${sessionId}/messages?limit=${limit}`,
      {
        headers: {
          'Content-Type': 'application/json',
          'X-Context': 'learning',
        },
      }
    )

    if (!response.ok) throw new Error('Failed to get chat history')
    return response.json()
  }

  // End chat session
  async endChatSession(sessionId: string): Promise<void> {
    const response = await fetch(
      `${API_BASE}/inference-gateway-svc/chat/sessions/${sessionId}/end`,
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Context': 'learning',
        },
      }
    )

    if (!response.ok) throw new Error('Failed to end chat session')
  }
}

export const inferenceClient = new InferenceClient()
