import { offlineFetch } from '../utils/offlineQueue'

const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8080'

// Chat Types aligned with S5-03 Chat Service
export interface Thread {
  id: string
  tenant_id: string
  learner_id: string
  title: string
  description?: string
  metadata?: Record<string, any>
  created_by: string
  created_at: string
  updated_at: string
}

export interface ThreadWithLastMessage extends Thread {
  lastMessage?: Message
}

export interface Message {
  id: string
  thread_id: string
  content: string
  sender_id: string
  sender_type: 'teacher' | 'guardian' | 'student' | 'system' | 'assistant'
  message_type: 'text' | 'image' | 'file' | 'system' | 'alert'
  metadata?: Record<string, any>
  created_at: string
  updated_at?: string
  // Add type property for UI compatibility
  type?: 'user' | 'assistant' | 'system'
}

export interface ThreadListResponse {
  threads: ThreadWithLastMessage[]
  total: number
  limit: number
  offset: number
}

export interface MessageListResponse {
  messages: Message[]
  total: number
  limit: number
  offset: number
}

export interface CreateThreadRequest {
  learner_id?: string
  title: string
  description?: string
  metadata?: Record<string, any>
}

export interface CreateMessageRequest {
  content: string
  sender_type?: 'teacher' | 'guardian' | 'student' | 'system' | 'assistant'
  message_type?: 'text' | 'image' | 'file' | 'system' | 'alert'
  metadata?: Record<string, any>
  // Add type property for UI compatibility
  type?: 'user' | 'assistant' | 'system'
}

export interface ChatStreamRequest {
  message: string
  thread_id?: string
  learner_id: string
  context?: {
    lesson_id?: string
    session_id?: string
    previous_messages?: Message[]
  }
}

export interface ChatStreamResponse {
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

export interface AttachToIEPRequest {
  thread_id: string
  message_ids: string[]
  iep_id: string
  evidence_type: 'communication' | 'progress' | 'assessment' | 'goal_tracking'
  notes?: string
}

class ChatClient {
  private baseURL: string

  constructor() {
    this.baseURL = `${API_BASE}/chat/v1`
  }

  private async makeRequest<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const url = `${this.baseURL}${endpoint}`
    const token = localStorage.getItem('auth_token')

    const response = await offlineFetch(url, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        Authorization: token ? `Bearer ${token}` : '',
        ...options.headers,
      },
    })

    if (!response.ok) {
      const error = await response.text()
      throw new Error(`Chat API Error: ${response.status} - ${error}`)
    }

    return response.json()
  }

  // Thread Management
  async getThreads(params?: {
    learner_id?: string
    limit?: number
    offset?: number
  }): Promise<ThreadListResponse> {
    const searchParams = new URLSearchParams()
    if (params?.learner_id) searchParams.set('learner_id', params.learner_id)
    if (params?.limit) searchParams.set('limit', params.limit.toString())
    if (params?.offset) searchParams.set('offset', params.offset.toString())

    const query = searchParams.toString()
    return this.makeRequest<ThreadListResponse>(
      `/threads${query ? `?${query}` : ''}`
    )
  }

  async getThread(threadId: string): Promise<Thread> {
    return this.makeRequest<Thread>(`/threads/${threadId}`)
  }

  async createThread(request: CreateThreadRequest): Promise<Thread> {
    return this.makeRequest<Thread>('/threads', {
      method: 'POST',
      body: JSON.stringify(request),
    })
  }

  async updateThread(
    threadId: string,
    updates: Partial<Pick<Thread, 'title' | 'description' | 'metadata'>>
  ): Promise<Thread> {
    return this.makeRequest<Thread>(`/threads/${threadId}`, {
      method: 'PUT',
      body: JSON.stringify(updates),
    })
  }

  async deleteThread(threadId: string): Promise<{ message: string }> {
    return this.makeRequest<{ message: string }>(`/threads/${threadId}`, {
      method: 'DELETE',
    })
  }

  // Message Management
  async getMessages(
    threadId: string,
    params?: {
      limit?: number
      offset?: number
      before?: string
      after?: string
    }
  ): Promise<MessageListResponse> {
    const searchParams = new URLSearchParams()
    if (params?.limit) searchParams.set('limit', params.limit.toString())
    if (params?.offset) searchParams.set('offset', params.offset.toString())
    if (params?.before) searchParams.set('before', params.before)
    if (params?.after) searchParams.set('after', params.after)

    const query = searchParams.toString()
    return this.makeRequest<MessageListResponse>(
      `/threads/${threadId}/messages${query ? `?${query}` : ''}`
    )
  }

  async createMessage(
    threadId: string,
    request: CreateMessageRequest
  ): Promise<Message> {
    return this.makeRequest<Message>(`/threads/${threadId}/messages`, {
      method: 'POST',
      body: JSON.stringify(request),
    })
  }

  async updateMessage(
    threadId: string,
    messageId: string,
    updates: Partial<Pick<Message, 'content' | 'metadata'>>
  ): Promise<Message> {
    return this.makeRequest<Message>(
      `/threads/${threadId}/messages/${messageId}`,
      {
        method: 'PUT',
        body: JSON.stringify(updates),
      }
    )
  }

  async deleteMessage(
    threadId: string,
    messageId: string
  ): Promise<{ message: string }> {
    return this.makeRequest<{ message: string }>(
      `/threads/${threadId}/messages/${messageId}`,
      {
        method: 'DELETE',
      }
    )
  }

  // Inference Gateway Integration
  async sendChatMessage(
    request: ChatStreamRequest
  ): Promise<AsyncIterable<ChatStreamResponse>> {
    const url = `${API_BASE}/inference/v1/chat/stream`
    const token = localStorage.getItem('auth_token')

    const response = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: token ? `Bearer ${token}` : '',
      },
      body: JSON.stringify(request),
    })

    if (!response.ok) {
      const error = await response.text()
      throw new Error(`Inference API Error: ${response.status} - ${error}`)
    }

    return this.parseStreamResponse(response)
  }

  private async *parseStreamResponse(
    response: Response
  ): AsyncIterable<ChatStreamResponse> {
    const reader = response.body?.getReader()
    if (!reader) {
      throw new Error('No response body')
    }

    const decoder = new TextDecoder()
    let buffer = ''

    try {
      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() || ''

        for (const line of lines) {
          if (line.trim() === '' || line.startsWith(':')) continue

          if (line.startsWith('data: ')) {
            const data = line.slice(6)
            if (data === '[DONE]') return

            try {
              const parsed = JSON.parse(data) as ChatStreamResponse
              yield parsed
            } catch (error) {
              console.warn('Failed to parse SSE data:', data, error)
            }
          }
        }
      }
    } finally {
      reader.releaseLock()
    }
  }

  // IEP Evidence Integration
  async attachToIEP(
    request: AttachToIEPRequest
  ): Promise<{ message: string; evidence_id: string }> {
    const url = `${API_BASE}/iep/v1/evidence/attach`
    const token = localStorage.getItem('auth_token')

    const response = await offlineFetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: token ? `Bearer ${token}` : '',
      },
      body: JSON.stringify(request),
    })

    if (!response.ok) {
      const error = await response.text()
      throw new Error(`IEP API Error: ${response.status} - ${error}`)
    }

    return response.json()
  }

  // Privacy & Compliance
  async exportChatData(
    learnerId: string,
    exportType: 'full' | 'metadata_only' = 'full'
  ): Promise<{
    export_id: string
    status: string
    requested_at: string
  }> {
    return this.makeRequest('/privacy/export', {
      method: 'POST',
      body: JSON.stringify({
        learner_id: learnerId,
        export_type: exportType,
      }),
    })
  }

  async deleteChatData(
    learnerId: string,
    deletionType: 'full' | 'messages_only' | 'threads_only' = 'full'
  ): Promise<{
    deletion_id: string
    status: string
    requested_at: string
  }> {
    return this.makeRequest('/privacy/delete', {
      method: 'POST',
      body: JSON.stringify({
        learner_id: learnerId,
        deletion_type: deletionType,
      }),
    })
  }

  // Utility Methods
  async resumeChat(threadId: string): Promise<{
    thread: Thread
    messages: Message[]
    can_continue: boolean
  }> {
    const [thread, messagesResponse] = await Promise.all([
      this.getThread(threadId),
      this.getMessages(threadId, { limit: 50 }),
    ])

    return {
      thread,
      messages: messagesResponse.messages,
      can_continue: true, // TODO: Check consent and other conditions
    }
  }

  // AI Response Generation for UI
  async generateAIResponse(
    threadId: string,
    options: {
      onProgress?: (chunk: any) => void
      onComplete?: () => void
      onError?: (error: any) => void
    }
  ): Promise<void> {
    try {
      // Get the latest messages for context
      const messagesResponse = await this.getMessages(threadId, { limit: 10 })
      const lastMessage =
        messagesResponse.messages[messagesResponse.messages.length - 1]

      if (!lastMessage) {
        throw new Error('No messages found in thread')
      }

      // Generate AI response via inference gateway
      const streamResponse = await this.sendChatMessage({
        message: lastMessage.content,
        thread_id: threadId,
        learner_id: 'current-user', // TODO: Get from context
        context: {
          session_id: `chat-${threadId}`,
          previous_messages: messagesResponse.messages.slice(-5), // Last 5 messages for context
        },
      })

      // Stream the response and collect it
      let fullResponse = ''
      for await (const chunk of streamResponse) {
        if (chunk.choices?.[0]?.delta?.content) {
          fullResponse += chunk.choices[0].delta.content
          options.onProgress?.(chunk)
        }
      }

      // Save the AI response as a message
      if (fullResponse.trim()) {
        await this.createMessage(threadId, {
          content: fullResponse,
          sender_type: 'assistant',
          message_type: 'text',
          type: 'assistant',
        })
      }

      options.onComplete?.()
    } catch (error) {
      console.error('AI response generation failed:', error)
      options.onError?.(error)
    }
  }

  // IEP attachment consent check
  async checkIEPAttachmentConsent(): Promise<boolean> {
    try {
      const response = await this.makeRequest<{ hasConsent: boolean }>(
        '/consent/iep-attachment'
      )
      return response.hasConsent
    } catch (error) {
      console.error('Failed to check IEP attachment consent:', error)
      return false
    }
  }

  // Attach message to IEP evidence
  async attachMessageToIEP(
    messageId: string,
    request: {
      title: string
      type:
        | 'observation'
        | 'assessment'
        | 'goal_progress'
        | 'intervention'
        | 'other'
      notes?: string
    }
  ): Promise<{ success: boolean; evidence_id?: string }> {
    try {
      const url = `${API_BASE}/iep/v1/evidence/attach-message`
      const token = localStorage.getItem('auth_token')

      const response = await offlineFetch(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: token ? `Bearer ${token}` : '',
        },
        body: JSON.stringify({
          message_id: messageId,
          evidence_title: request.title,
          evidence_type: request.type,
          notes: request.notes,
        }),
      })

      if (!response.ok) {
        throw new Error(`IEP attachment failed: ${response.status}`)
      }

      const result = await response.json()
      return { success: true, evidence_id: result.evidence_id }
    } catch (error) {
      console.error('Failed to attach message to IEP:', error)
      throw error
    }
  }

  async createThreadAndSendMessage(
    learnerId: string,
    title: string,
    initialMessage: string
  ): Promise<{
    thread: Thread
    message: Message
    ai_response?: AsyncIterable<ChatStreamResponse>
  }> {
    // Create thread
    const thread = await this.createThread({
      learner_id: learnerId,
      title,
      description: `Chat conversation started with: ${initialMessage.substring(0, 100)}...`,
    })

    // Send initial message
    const message = await this.createMessage(thread.id, {
      content: initialMessage,
      sender_type: 'teacher', // TODO: Detect from user context
      message_type: 'text',
    })

    // Get AI response
    const ai_response = await this.sendChatMessage({
      message: initialMessage,
      thread_id: thread.id,
      learner_id: learnerId,
      context: {
        session_id: `chat-${thread.id}`,
        previous_messages: [message],
      },
    })

    return {
      thread,
      message,
      ai_response,
    }
  }
}

// Export singleton instance
export const chatClient = new ChatClient()
export default chatClient
