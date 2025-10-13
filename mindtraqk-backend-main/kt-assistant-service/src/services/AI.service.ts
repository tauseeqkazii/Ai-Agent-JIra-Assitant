import { Redis } from 'ioredis'
import { Logger } from 'winston'
import crypto from 'crypto'
import { AIRequest, AIResponse } from '../types/ai.types'
import { setupLogger } from '../utils/logger'
import { setupRedis } from '../utils/redis'
import {
  AIEngineProcessResponse,
  aiEngineClient,
} from '../utils/aiEngineClient'

class AIService {
  private redis: Redis
  private logger: Logger
  private retryAttempts = 3

  constructor() {
    this.redis = setupRedis()
    this.logger = setupLogger()
    this.validateConfig()
  }

  private validateConfig(): void {
    if (!process.env.AI_ENGINE_URL) {
      this.logger.warn(
        'AI_ENGINE_URL not set; defaulting to http://localhost:8300/api/v1',
      )
    }
  }

  async processMessage(request: AIRequest): Promise<AIResponse> {
    const startTime = Date.now()
    const requestId = crypto.randomUUID()

    try {
      await this.enforceRateLimits(request)

      const payload = {
        user_input: request.message,
        user_context: this.buildUserContext(request),
      }

      let lastError: unknown = null

      for (let attempt = 0; attempt < this.retryAttempts; attempt++) {
        try {
          const engineResponse =
            await aiEngineClient.processMessage(payload)
          const duration = Date.now() - startTime

          await this.recordMetrics(engineResponse, duration, requestId)

          if (engineResponse.success) {
            return this.mapSuccess(engineResponse)
          }

          return {
            success: false,
            error: {
              code: engineResponse.error || 'ENGINE_ERROR',
              message:
                engineResponse.error_message ||
                'AI engine returned an error',
              details: engineResponse.metadata,
            },
          }
        } catch (error) {
          lastError = error

          if (!this.isRetryable(error)) {
            throw error
          }

          const backoff = 1000 * (attempt + 1)
          await new Promise((resolve) => setTimeout(resolve, backoff))
        }
      }

      throw lastError
    } catch (error: any) {
      this.logger.error('AI processing error', {
        error: error?.message || error,
        userId: request.context?.userId,
        stack: process.env.NODE_ENV === 'development' ? error?.stack : undefined,
      })

      return {
        success: false,
        error: {
          code: this.getErrorCode(error),
          message: error?.message || 'Failed to process AI request',
          details:
            process.env.NODE_ENV === 'development' ? error?.stack : undefined,
        },
      }
    }
  }

  private async enforceRateLimits(request: AIRequest): Promise<void> {
    const userId = request.context?.userId
    if (!userId) {
      return
    }

    const rateLimitKey = `rate:${userId}`
    const requests = await this.redis.incr(rateLimitKey)
    await this.redis.expire(rateLimitKey, 3600)

    if (requests > 100) {
      throw new Error('Rate limit exceeded')
    }
  }

  private buildUserContext(request: AIRequest): Record<string, any> {
    const context = request.context
    const userContext: Record<string, any> = {}

    if (context?.userId) userContext.user_id = context.userId
    if (context?.teamId) userContext.team_id = context.teamId
    if (context?.projectId) userContext.project_id = context.projectId
    if (context?.metadata) userContext.metadata = context.metadata

    return userContext
  }

  private async recordMetrics(
    response: AIEngineProcessResponse,
    duration: number,
    requestId: string,
  ): Promise<void> {
    try {
      const metricsKey = `metrics:${new Date()
        .toISOString()
        .slice(0, 10)}`

      await this.redis.hset(
        metricsKey,
        requestId,
        JSON.stringify({
          timestamp: new Date().toISOString(),
          duration,
          routeType: response.route_type,
          backendAction: response.backend_action,
          rawMetadata: response.metadata,
        }),
      )
    } catch (error) {
      this.logger.warn('Failed to record AI metrics', { error })
    }
  }

  private mapSuccess(response: AIEngineProcessResponse): AIResponse {
    return {
      success: true,
      data: {
        content: response.generated_content || '',
        routeType: response.route_type,
        backendAction: response.backend_action,
        requiresApproval: response.requires_user_approval ?? false,
        metadata: response.metadata || {},
        raw: response,
      },
    }
  }

  private isRetryable(error: any): boolean {
    if (!error) return false
    const status = error?.response?.status
    if (!status && error?.code === 'ECONNABORTED') {
      return true
    }
    return [408, 425, 429, 500, 502, 503, 504].includes(status)
  }

  private getErrorCode(error: any): string {
    const message = typeof error?.message === 'string' ? error.message : ''
    if (message.includes('Rate limit')) return 'RATE_LIMIT_EXCEEDED'
    if (message.includes('cost limit')) return 'COST_LIMIT_EXCEEDED'
    if (error?.response?.status === 401) return 'UNAUTHORIZED'
    if (error?.response?.status === 404) return 'NOT_FOUND'
    return 'INTERNAL_ERROR'
  }

  async getHealth(): Promise<any> {
    try {
      const health = await aiEngineClient.getHealth()
      return {
        status: health.healthy ? 'healthy' : 'unhealthy',
        provider: 'ai_engine',
        ...health,
      }
    } catch (error: any) {
      this.logger.error('Health check failed', { error })
      return {
        status: 'unhealthy',
        error: error?.message || 'Health check failed',
        timestamp: new Date().toISOString(),
      }
    }
  }

  async getServiceMetrics(): Promise<Record<string, any>> {
    try {
      const [metrics, costs] = await Promise.all([
        aiEngineClient.getMetrics(),
        aiEngineClient.getCosts(),
      ])

      return {
        metrics,
        costs,
      }
    } catch (error: any) {
      this.logger.warn('Failed to fetch service metrics', { error })
      return {}
    }
  }
}

export default new AIService()
