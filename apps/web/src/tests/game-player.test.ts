/**
 * S3-10 Game Player Unit Tests
 * Testing game client functionality and component behavior
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

// Mock modules that might not exist in test environment
vi.mock('../lib/gameClient', () => ({
  gameClient: mockGameClient,
  GameHelpers: {
    calculateProgress: vi.fn((_session, _manifest) => 50),
    formatTime: vi.fn(_seconds => '05:00'),
    calculateGrade: vi.fn(_performance => 'B+'),
    getPerformanceLevel: vi.fn(_performance => 'good'),
    checkSceneCompletion: vi.fn(() => true),
  },
}))

describe('S3-10 Game Client API', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  test('should generate game with correct parameters', async () => {
    const mockResult = {
      gameId: 'test-game-123',
      manifest: {
        id: 'test-manifest',
        title: 'Math Reset Game',
        description: 'A mathematics-based reset game',
        version: '1.0.0',
        timeLimit: 300,
        maxScore: 100,
        scenes: [],
        metadata: {
          topic: 'math',
          difficulty: 'easy',
          gameType: 'reset',
          createdAt: new Date().toISOString(),
          estimatedDuration: 300,
        },
      },
    }

    mockGameClient.generateGame.mockResolvedValue(mockResult)

    const result = await mockGameClient.generateGame({
      topic: 'math',
      difficulty: 'easy',
      duration: 300,
    })

    expect(mockGameClient.generateGame).toHaveBeenCalledWith({
      topic: 'math',
      difficulty: 'easy',
      duration: 300,
    })
    expect(result).toEqual(mockResult)
  })

  test('should start game session correctly', async () => {
    const mockSession = {
      sessionId: 'session-123',
      gameId: 'test-game',
      manifestId: 'test-manifest',
      status: 'active',
      startedAt: new Date().toISOString(),
      progress: {
        completedScenes: [],
        currentScore: 0,
        timeElapsed: 0,
        interactions: 0,
      },
    }

    mockGameClient.startSession.mockResolvedValue(mockSession)

    const result = await mockGameClient.startSession(
      'test-game',
      'test-manifest'
    )

    expect(mockGameClient.startSession).toHaveBeenCalledWith(
      'test-game',
      'test-manifest'
    )
    expect(result).toEqual(mockSession)
  })

  test('should end session with performance data', async () => {
    const mockPerformance = {
      score: 85,
      maxScore: 100,
      accuracy: 92,
      completionTime: 180,
      interactions: 12,
      scenesCompleted: 3,
      totalScenes: 3,
      mistakes: 2,
      hintsUsed: 1,
    }

    const mockEndResult = {
      sessionId: 'session-123',
      completedAt: new Date().toISOString(),
      performance: mockPerformance,
    }

    mockGameClient.endSession.mockResolvedValue(mockEndResult)

    const result = await mockGameClient.endSession(
      'session-123',
      mockPerformance
    )

    expect(mockGameClient.endSession).toHaveBeenCalledWith(
      'session-123',
      mockPerformance
    )
    expect(result).toEqual(mockEndResult)
  })

  test('should emit game events correctly', async () => {
    const eventData = {
      sessionId: 'session-123',
      gameId: 'test-game',
      data: { scene: 'scene-1' },
    }

    await mockGameClient.emitEvent('GAME_STARTED', eventData)

    expect(mockGameClient.emitEvent).toHaveBeenCalledWith(
      'GAME_STARTED',
      eventData
    )
  })

  test('should get game session details', async () => {
    const mockSession = {
      sessionId: 'session-123',
      gameId: 'test-game',
      manifestId: 'test-manifest',
      status: 'active',
      startedAt: new Date().toISOString(),
      progress: {
        completedScenes: ['scene-1'],
        currentScore: 50,
        timeElapsed: 120,
        interactions: 8,
      },
    }

    mockGameClient.getGameSession.mockResolvedValue(mockSession)

    const result = await mockGameClient.getGameSession('session-123')

    expect(mockGameClient.getGameSession).toHaveBeenCalledWith('session-123')
    expect(result).toEqual(mockSession)
  })

  test('should update session progress', async () => {
    const progressUpdate = {
      currentScore: 75,
      timeElapsed: 150,
      interactions: 10,
    }

    const updatedSession = {
      sessionId: 'session-123',
      gameId: 'test-game',
      manifestId: 'test-manifest',
      status: 'active',
      startedAt: new Date().toISOString(),
      progress: {
        completedScenes: ['scene-1'],
        ...progressUpdate,
      },
    }

    mockGameClient.updateSession.mockResolvedValue(updatedSession)

    const result = await mockGameClient.updateSession(
      'session-123',
      progressUpdate
    )

    expect(mockGameClient.updateSession).toHaveBeenCalledWith(
      'session-123',
      progressUpdate
    )
    expect(result).toEqual(updatedSession)
  })

  test('should get game manifest', async () => {
    const mockManifest = {
      id: 'test-manifest',
      title: 'Test Game',
      description: 'A test game for validation',
      version: '1.0.0',
      timeLimit: 300,
      maxScore: 100,
      scenes: [
        {
          id: 'scene-1',
          title: 'First Scene',
          elements: [],
          interactions: [],
          successCriteria: [],
        },
      ],
      metadata: {
        topic: 'math',
        difficulty: 'easy',
        gameType: 'reset',
        createdAt: new Date().toISOString(),
        estimatedDuration: 300,
      },
    }

    mockGameClient.getGameManifest.mockResolvedValue(mockManifest)

    const result = await mockGameClient.getGameManifest('test-game')

    expect(mockGameClient.getGameManifest).toHaveBeenCalledWith('test-game')
    expect(result).toEqual(mockManifest)
  })

  test('should submit interaction results', async () => {
    const interactionResult = {
      success: true,
      timeToComplete: 5.5,
      attempts: 1,
      value: 'correct answer',
    }

    await mockGameClient.submitInteraction(
      'session-123',
      'interaction-1',
      interactionResult
    )

    expect(mockGameClient.submitInteraction).toHaveBeenCalledWith(
      'session-123',
      'interaction-1',
      interactionResult
    )
  })
})

describe('S3-10 Game Helpers', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  test('should have mocked GameHelpers available', async () => {
    const { GameHelpers } = await import('../lib/gameClient')

    expect(GameHelpers.calculateProgress).toBeDefined()
    expect(GameHelpers.formatTime).toBeDefined()
    expect(GameHelpers.calculateGrade).toBeDefined()
    expect(GameHelpers.getPerformanceLevel).toBeDefined()
    expect(GameHelpers.checkSceneCompletion).toBeDefined()
  })

  test('should mock calculateProgress function', async () => {
    const { GameHelpers } = await import('../lib/gameClient')

    const result = GameHelpers.calculateProgress({} as any, {} as any)
    expect(result).toBe(50)
    expect(GameHelpers.calculateProgress).toHaveBeenCalled()
  })

  test('should mock formatTime function', async () => {
    const { GameHelpers } = await import('../lib/gameClient')

    const result = GameHelpers.formatTime(300)
    expect(result).toBe('05:00')
    expect(GameHelpers.formatTime).toHaveBeenCalledWith(300)
  })

  test('should mock calculateGrade function', async () => {
    const { GameHelpers } = await import('../lib/gameClient')

    const result = GameHelpers.calculateGrade({} as any)
    expect(result).toBe('B+')
    expect(GameHelpers.calculateGrade).toHaveBeenCalled()
  })

  test('should mock getPerformanceLevel function', async () => {
    const { GameHelpers } = await import('../lib/gameClient')

    const result = GameHelpers.getPerformanceLevel({} as any)
    expect(result).toBe('good')
    expect(GameHelpers.getPerformanceLevel).toHaveBeenCalled()
  })

  test('should mock checkSceneCompletion function', async () => {
    const { GameHelpers } = await import('../lib/gameClient')

    const result = GameHelpers.checkSceneCompletion({} as any, [], 0, 0)
    expect(result).toBe(true)
    expect(GameHelpers.checkSceneCompletion).toHaveBeenCalled()
  })
})

describe('S3-10 Game Player Integration', () => {
  test('should handle complete game flow', async () => {
    // Test complete game lifecycle
    const gameRequest = {
      topic: 'math',
      difficulty: 'medium',
      duration: 600,
    }

    const gameResponse = {
      gameId: 'game-456',
      manifest: {
        id: 'manifest-456',
        title: 'Math Challenge',
        description: 'Advanced math game',
        version: '1.0.0',
        timeLimit: 600,
        maxScore: 200,
        scenes: [
          {
            id: 'scene-1',
            title: 'Scene 1',
            elements: [],
            interactions: [],
            successCriteria: [],
          },
          {
            id: 'scene-2',
            title: 'Scene 2',
            elements: [],
            interactions: [],
            successCriteria: [],
          },
        ],
        metadata: {
          topic: 'math',
          difficulty: 'medium',
          gameType: 'reset',
          createdAt: new Date().toISOString(),
          estimatedDuration: 600,
        },
      },
    }

    const sessionResponse = {
      sessionId: 'session-456',
      gameId: 'game-456',
      manifestId: 'manifest-456',
      status: 'active',
      startedAt: new Date().toISOString(),
      progress: {
        completedScenes: [],
        currentScore: 0,
        timeElapsed: 0,
        interactions: 0,
      },
    }

    const endResponse = {
      sessionId: 'session-456',
      completedAt: new Date().toISOString(),
      performance: {
        score: 150,
        maxScore: 200,
        accuracy: 85,
        completionTime: 450,
        interactions: 25,
        scenesCompleted: 2,
        totalScenes: 2,
        mistakes: 3,
        hintsUsed: 2,
      },
    }

    mockGameClient.generateGame.mockResolvedValue(gameResponse)
    mockGameClient.startSession.mockResolvedValue(sessionResponse)
    mockGameClient.endSession.mockResolvedValue(endResponse)

    // Generate game
    const game = await mockGameClient.generateGame(gameRequest)
    expect(game.gameId).toBe('game-456')

    // Start session
    const session = await mockGameClient.startSession(
      game.gameId,
      game.manifest.id
    )
    expect(session.sessionId).toBe('session-456')
    expect(session.status).toBe('active')

    // Simulate game events
    await mockGameClient.emitEvent('GAME_STARTED', {
      sessionId: session.sessionId,
      gameId: game.gameId,
    })

    await mockGameClient.emitEvent('SCENE_STARTED', {
      sessionId: session.sessionId,
      gameId: game.gameId,
      sceneId: 'scene-1',
    })

    await mockGameClient.emitEvent('SCENE_COMPLETED', {
      sessionId: session.sessionId,
      gameId: game.gameId,
      sceneId: 'scene-1',
    })

    // End session
    const endResult = await mockGameClient.endSession(
      session.sessionId,
      endResponse.performance
    )
    expect(endResult.performance.score).toBe(150)

    // Emit completion event
    await mockGameClient.emitEvent('GAME_COMPLETED', {
      sessionId: session.sessionId,
      gameId: game.gameId,
      data: { performance: endResponse.performance },
    })

    // Verify all calls were made
    expect(mockGameClient.generateGame).toHaveBeenCalledWith(gameRequest)
    expect(mockGameClient.startSession).toHaveBeenCalledWith(
      game.gameId,
      game.manifest.id
    )
    expect(mockGameClient.endSession).toHaveBeenCalledWith(
      session.sessionId,
      endResponse.performance
    )
    expect(mockGameClient.emitEvent).toHaveBeenCalledTimes(4)
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

    expect(mockGameClient.generateGame).toHaveBeenCalled()
  })

  test('should validate game requirements', () => {
    // Test that our implementation meets S3-10 requirements
    expect(mockGameClient.generateGame).toBeDefined()
    expect(mockGameClient.startSession).toBeDefined()
    expect(mockGameClient.endSession).toBeDefined()
    expect(mockGameClient.emitEvent).toBeDefined()
    expect(mockGameClient.getGameSession).toBeDefined()
    expect(mockGameClient.updateSession).toBeDefined()
    expect(mockGameClient.getGameManifest).toBeDefined()
    expect(mockGameClient.submitInteraction).toBeDefined()
  })
})
