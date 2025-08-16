import React, { useState, useEffect, useRef } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  inferenceClient,
  type ChatSession,
  type ChatMessage,
} from '../../api/inferenceClient'
import {
  type Lesson,
  type LearningSession,
} from '../../api/lessonRegistryClient'

interface ChatPaneProps {
  chatSession: ChatSession
  lesson: Lesson
  learningSession: LearningSession
  currentSectionId: string | null
  currentContentId: string | null
  onChatInteraction: (messageType: 'sent' | 'received', data: any) => void
}

export const ChatPane: React.FC<ChatPaneProps> = ({
  chatSession,
  lesson,
  learningSession,
  currentSectionId,
  currentContentId,
  onChatInteraction,
}) => {
  const [messages, setMessages] = useState<ChatMessage[]>(
    chatSession.messages || []
  )
  const [inputMessage, setInputMessage] = useState('')
  const [isStreaming, setIsStreaming] = useState(false)
  const [streamingMessage, setStreamingMessage] = useState('')
  const [error, setError] = useState<string | null>(null)

  const messagesEndRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, streamingMessage])

  // Load chat history on mount
  useEffect(() => {
    loadChatHistory()
  }, [chatSession.id])

  const loadChatHistory = async () => {
    try {
      const history = await inferenceClient.getChatHistory(chatSession.id)
      setMessages(history)
    } catch (err) {
      console.error('Failed to load chat history:', err)
    }
  }

  const sendMessage = async () => {
    if (!inputMessage.trim() || isStreaming) return

    const userMessage = inputMessage.trim()
    setInputMessage('')
    setError(null)

    // Add user message to UI immediately
    const newUserMessage: ChatMessage = {
      id: `user_${Date.now()}`,
      role: 'user',
      content: userMessage,
      timestamp: new Date().toISOString(),
      metadata: {
        lessonId: lesson.id,
        sessionId: learningSession.id,
      },
    }

    setMessages(prev => [...prev, newUserMessage])

    // Track user message
    onChatInteraction('sent', {
      messageId: newUserMessage.id,
      content: userMessage,
      contentLength: userMessage.length,
      currentSection: currentSectionId,
      currentContent: currentContentId,
    })

    // Prepare assistant message placeholder
    const assistantMessageId = `assistant_${Date.now()}`
    const assistantMessage: ChatMessage = {
      id: assistantMessageId,
      role: 'assistant',
      content: '',
      timestamp: new Date().toISOString(),
      metadata: {
        lessonId: lesson.id,
        sessionId: learningSession.id,
      },
    }

    setMessages(prev => [...prev, assistantMessage])
    setIsStreaming(true)
    setStreamingMessage('')

    try {
      // Send message with streaming
      await inferenceClient.sendMessage(
        {
          sessionId: chatSession.id,
          message: userMessage,
          context: {
            lessonId: lesson.id,
            currentContent: currentContentId || undefined,
            learnerPreferences: {
              gradeLevel: lesson.gradeLevel,
              subject: lesson.subject,
            },
          },
        },
        // onChunk
        (chunk: string) => {
          setStreamingMessage(prev => prev + chunk)
        },
        // onComplete
        (fullResponse: string) => {
          setIsStreaming(false)
          setStreamingMessage('')

          // Update the assistant message with final content
          setMessages(prev =>
            prev.map(msg =>
              msg.id === assistantMessageId
                ? { ...msg, content: fullResponse }
                : msg
            )
          )

          // Track assistant response
          onChatInteraction('received', {
            messageId: assistantMessageId,
            content: fullResponse,
            contentLength: fullResponse.length,
            responseTime:
              Date.now() - parseInt(assistantMessageId.split('_')[1]),
            currentSection: currentSectionId,
            currentContent: currentContentId,
          })
        },
        // onError
        (err: Error) => {
          setIsStreaming(false)
          setStreamingMessage('')
          setError(err.message)

          // Remove the placeholder assistant message
          setMessages(prev => prev.filter(msg => msg.id !== assistantMessageId))
        }
      )
    } catch (err) {
      setIsStreaming(false)
      setStreamingMessage('')
      setError(err instanceof Error ? err.message : 'Failed to send message')

      // Remove the placeholder assistant message
      setMessages(prev => prev.filter(msg => msg.id !== assistantMessageId))
    }
  }

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage()
    }
  }

  const formatTimestamp = (timestamp: string) => {
    return new Date(timestamp).toLocaleTimeString([], {
      hour: '2-digit',
      minute: '2-digit',
    })
  }

  const getOfflineQueueCount = () => {
    return inferenceClient.getQueuedMessagesCount()
  }

  return (
    <div className="h-full flex flex-col bg-white">
      {/* Header */}
      <div className="flex-shrink-0 border-b border-gray-200 p-4">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-lg font-semibold text-gray-900">
              AI Learning Copilot
            </h3>
            <p className="text-sm text-gray-600">
              Ask questions about the lesson
            </p>
          </div>
          <div className="flex items-center space-x-2">
            {getOfflineQueueCount() > 0 && (
              <div className="bg-yellow-100 text-yellow-800 text-xs px-2 py-1 rounded-full">
                {getOfflineQueueCount()} queued
              </div>
            )}
            <div
              className={`w-3 h-3 rounded-full ${
                navigator.onLine ? 'bg-green-500' : 'bg-red-500'
              }`}
              title={navigator.onLine ? 'Online' : 'Offline'}
            />
          </div>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.length === 0 && (
          <div className="text-center text-gray-500 mt-8">
            <div className="text-4xl mb-4">🤖</div>
            <p className="text-lg font-medium mb-2">
              Hi! I'm your AI Learning Copilot
            </p>
            <p className="text-sm">
              Ask me questions about the lesson, request explanations, or get
              help with concepts.
            </p>
          </div>
        )}

        {messages.map(message => (
          <motion.div
            key={message.id}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
          >
            <div
              className={`max-w-xs lg:max-w-md px-4 py-2 rounded-lg ${
                message.role === 'user'
                  ? 'bg-blue-600 text-white'
                  : 'bg-gray-100 text-gray-900'
              }`}
            >
              <div className="whitespace-pre-wrap">{message.content}</div>
              <div
                className={`text-xs mt-1 ${
                  message.role === 'user' ? 'text-blue-100' : 'text-gray-500'
                }`}
              >
                {formatTimestamp(message.timestamp)}
              </div>
            </div>
          </motion.div>
        ))}

        {/* Streaming message */}
        {isStreaming && (
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            className="flex justify-start"
          >
            <div className="max-w-xs lg:max-w-md px-4 py-2 rounded-lg bg-gray-100 text-gray-900">
              <div className="whitespace-pre-wrap">
                {streamingMessage}
                <span className="animate-pulse">▋</span>
              </div>
              <div className="text-xs text-gray-500 mt-1">Typing...</div>
            </div>
          </motion.div>
        )}

        {/* Error message */}
        <AnimatePresence>
          {error && (
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.95 }}
              className="bg-red-50 border border-red-200 rounded-lg p-3"
            >
              <div className="flex items-center space-x-2">
                <svg
                  className="w-5 h-5 text-red-500"
                  fill="currentColor"
                  viewBox="0 0 20 20"
                >
                  <path
                    fillRule="evenodd"
                    d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z"
                    clipRule="evenodd"
                  />
                </svg>
                <span className="text-red-700 text-sm">{error}</span>
                <button
                  onClick={() => setError(null)}
                  className="ml-auto text-red-500 hover:text-red-700"
                >
                  <svg
                    className="w-4 h-4"
                    fill="currentColor"
                    viewBox="0 0 20 20"
                  >
                    <path
                      fillRule="evenodd"
                      d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z"
                      clipRule="evenodd"
                    />
                  </svg>
                </button>
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div className="flex-shrink-0 border-t border-gray-200 p-4">
        <div className="flex space-x-2">
          <input
            ref={inputRef}
            type="text"
            value={inputMessage}
            onChange={e => setInputMessage(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder="Ask a question about the lesson..."
            className="flex-1 border border-gray-300 rounded-lg px-3 py-2 focus:ring-blue-500 focus:border-blue-500"
            disabled={isStreaming}
          />
          <button
            onClick={sendMessage}
            disabled={!inputMessage.trim() || isStreaming}
            className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {isStreaming ? (
              <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
            ) : (
              <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                <path d="M10.894 2.553a1 1 0 00-1.788 0l-7 14a1 1 0 001.169 1.409l5-1.429A1 1 0 009 15.571V11a1 1 0 112 0v4.571a1 1 0 00.725.962l5 1.428a1 1 0 001.17-1.408l-7-14z" />
              </svg>
            )}
          </button>
        </div>

        {!navigator.onLine && (
          <div className="mt-2 text-xs text-yellow-600 bg-yellow-50 px-2 py-1 rounded">
            You're offline. Messages will be sent when connection is restored.
          </div>
        )}
      </div>
    </div>
  )
}
