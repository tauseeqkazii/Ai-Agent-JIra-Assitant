import { describe, it, expect, beforeEach, jest } from '@jest/globals'
import { AIRequest } from '../types/ai.types'

jest.mock('../utils/logger', () => ({
  setupLogger: jest.fn(() => ({
    info: jest.fn(),
    warn: jest.fn(),
    error: jest.fn(),
  })),
}))

const rateMap: Record<string, number> = {}

jest.mock('../utils/redis', () => {
  const redisInstance = {
    incr: jest.fn(async (key: string) => {
      rateMap[key] = (rateMap[key] || 0) + 1
      return rateMap[key]
    }),
    expire: jest.fn(async () => 1),
    hset: jest.fn(async () => 1),
  }

  const setupRedisMock = jest.fn(() => redisInstance)
  ;(setupRedisMock as any).__instance = redisInstance
  ;(setupRedisMock as any).__rateMap = rateMap

  return {
    setupRedis: setupRedisMock,
  }
})

import { aiEngineClient } from '../utils/aiEngineClient'
import AIService from '../services/AI.service'

const processMessageSpy = jest.spyOn(aiEngineClient, 'processMessage')
const getHealthSpy = jest.spyOn(aiEngineClient, 'getHealth')

describe('AIService', () => {
  beforeEach(() => {
    jest.clearAllMocks()
    processMessageSpy.mockReset()
    getHealthSpy.mockReset()

    for (const key of Object.keys(rateMap)) {
      delete rateMap[key]
    }

    process.env.AI_ENGINE_URL = 'http://ai-engine.local/api/v1'
  })

  const buildRequest = (): AIRequest => ({
    message: 'Summarize my progress',
    context: {
      userId: 'test-user-123',
      metadata: { sessionId: 'session-1' },
    },
  })

  it('returns success when AI engine responds successfully', async () => {
    processMessageSpy.mockResolvedValueOnce({
      success: true,
      generated_content: 'Work is on track.',
      route_type: 'llm_rephrasing',
      backend_action: 'show_comment_for_approval',
      requires_user_approval: false,
      metadata: { quality_score: 0.92 },
    })

    const response = await AIService.processMessage(buildRequest())

    expect(response.success).toBe(true)
    expect(response.data?.content).toBe('Work is on track.')
    expect(response.data?.routeType).toBe('llm_rephrasing')
    expect(response.data?.metadata).toMatchObject({ quality_score: 0.92 })
  })

  it('enforces per-user rate limits', async () => {
    processMessageSpy.mockResolvedValue({
      success: true,
      generated_content: 'ok',
    })

    const request = buildRequest()
    rateMap[`rate:${request.context?.userId}`] = 100

    const result = await AIService.processMessage(request)

    expect(result.success).toBe(false)
    expect(result.error?.code).toBe('RATE_LIMIT_EXCEEDED')
    expect(processMessageSpy).not.toHaveBeenCalled()
  })

  it('returns failure when AI engine reports error', async () => {
    processMessageSpy.mockResolvedValueOnce({
      success: false,
      error: 'ENGINE_ERROR',
      error_message: 'Downstream failure',
    })

    const result = await AIService.processMessage(buildRequest())

    expect(result.success).toBe(false)
    expect(result.error?.code).toBe('ENGINE_ERROR')
    expect(result.error?.message).toBe('Downstream failure')
  })

  it('bubbles up health information from AI engine', async () => {
    getHealthSpy.mockResolvedValueOnce({
      healthy: true,
      timestamp: new Date().toISOString(),
    })

    const health = await AIService.getHealth()

    expect(health.status).toBe('healthy')
    expect(getHealthSpy).toHaveBeenCalledTimes(1)
  })
})
