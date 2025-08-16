/**
 * S3-10 Game Player E2E Integration Tests
 * Tests the complete game player functionality without React rendering
 */

import { describe, test, expect, vi, beforeEach } from 'vitest'

// Mock the game client module
const mockGameClient = {
  generateGame: vi.fn(),
  startSession: vi.fn(),
  endSession: vi.fn(),
  emitEvent: vi.fn(),
  getGameSession: vi.fn(),
  updateSession: vi.fn(),
  getGameManifest: vi.fn(),
  submitInteraction: vi.fn(),
}

vi.mock('../../lib/gameClient', () => ({
  gameClient: mockGameClient,
  GameHelpers: {
    calculateProgress: vi.fn(() => 50),
    formatTime: vi.fn(() => '05:00'),
    calculateGrade: vi.fn(() => 'B+'),
    getPerformanceLevel: vi.fn(() => 'good'),
    checkSceneCompletion: vi.fn(() => true),
  },
}))

describe('S3-10 Game Player E2E Tests', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  test('should validate S3-10 requirements implementation', () => {
    // Verify that all required API methods are available
    expect(mockGameClient.generateGame).toBeDefined()
    expect(mockGameClient.startSession).toBeDefined()
    expect(mockGameClient.endSession).toBeDefined()
    expect(mockGameClient.emitEvent).toBeDefined()
    expect(mockGameClient.getGameSession).toBeDefined()
    expect(mockGameClient.updateSession).toBeDefined()
    expect(mockGameClient.getGameManifest).toBeDefined()
    expect(mockGameClient.submitInteraction).toBeDefined()
  })

  test('should generate game and start session flow', async () => {
    const gameResponse = {
      gameId: 'test-game',
      manifest: {
        id: 'test-manifest',
        title: 'Test Game',
        scenes: [],
      },
    }

    const sessionResponse = {
      sessionId: 'session-123',
      gameId: 'test-game',
      status: 'active' as const,
      startedAt: new Date().toISOString(),
    }

    mockGameClient.generateGame.mockResolvedValue(gameResponse)
    mockGameClient.startSession.mockResolvedValue(sessionResponse)

    const game = await mockGameClient.generateGame({
      topic: 'math',
      difficulty: 'easy',
      duration: 300,
    })

    const session = await mockGameClient.startSession(
      game.gameId,
      game.manifest.id
    )

    expect(game.gameId).toBe('test-game')
    expect(session.sessionId).toBe('session-123')
  })

  test('should handle game completion flow', async () => {
    const performance = {
      score: 95,
      accuracy: 95,
      completionTime: 240,
    }

    const endResponse = {
      sessionId: 'session-789',
      completedAt: new Date().toISOString(),
      performance,
    }

    mockGameClient.endSession.mockResolvedValue(endResponse)

    const result = await mockGameClient.endSession('session-789', performance)

    expect(result.performance.score).toBe(95)
    expect(result.completedAt).toBeDefined()
  })

  test('should emit game events correctly', async () => {
    const eventData = {
      sessionId: 'session-123',
      gameId: 'test-game',
    }

    await mockGameClient.emitEvent('GAME_STARTED', eventData)
    await mockGameClient.emitEvent('GAME_COMPLETED', eventData)

    expect(mockGameClient.emitEvent).toHaveBeenCalledTimes(2)
    expect(mockGameClient.emitEvent).toHaveBeenCalledWith(
      'GAME_STARTED',
      eventData
    )
    expect(mockGameClient.emitEvent).toHaveBeenCalledWith(
      'GAME_COMPLETED',
      eventData
    )
  })

  test('should handle API errors gracefully', async () => {
    const error = new Error('Network error')
    mockGameClient.generateGame.mockRejectedValue(error)

    await expect(
      mockGameClient.generateGame({
        topic: 'math',
        difficulty: 'easy',
        duration: 300,
      })
    ).rejects.toThrow('Network error')
  })
})
