import axios, { AxiosError, AxiosInstance } from 'axios'
import { Logger } from 'winston'
import { setupLogger } from './logger'

export interface AIEngineProcessRequest {
  user_input: string
  user_context: Record<string, any>
}

export interface AIEngineProcessResponse {
  success: boolean
  route_type?: string
  backend_action?: string
  generated_content?: string
  requires_user_approval?: boolean
  error?: string
  error_message?: string
  metadata?: Record<string, any>
  [key: string]: any
}

export interface AIEngineHealthResponse {
  healthy: boolean
  timestamp: string
  components?: Record<string, any>
}

class AIEngineClient {
  private client: AxiosInstance
  private logger: Logger

  constructor() {
    const baseURL = process.env.AI_ENGINE_URL || 'http://localhost:8300/api/v1'
    const timeout =
      Number.parseInt(process.env.AI_ENGINE_TIMEOUT || '15000', 10) || 15000

    this.logger = setupLogger()

    this.client = axios.create({
      baseURL,
      timeout,
    })

    this.client.interceptors.request.use((config) => {
      const token = process.env.AI_ENGINE_TOKEN
      if (token) {
        const headers = (config.headers ?? {}) as Record<string, string>
        headers.Authorization = `Bearer ${token}`
        config.headers = headers as any
      }
      return config
    })
  }

  async processMessage(
    payload: AIEngineProcessRequest,
  ): Promise<AIEngineProcessResponse> {
    try {
      const { data } = await this.client.post<AIEngineProcessResponse>(
        '/process',
        payload,
      )
      return data
    } catch (error) {
      this.logAxiosError('processMessage', error)
      throw error
    }
  }

  async getHealth(): Promise<AIEngineHealthResponse> {
    try {
      const { data } = await this.client.get<AIEngineHealthResponse>('/health')
      return data
    } catch (error) {
      this.logAxiosError('getHealth', error)
      throw error
    }
  }

  async getMetrics(): Promise<Record<string, any>> {
    try {
      const { data } = await this.client.get<Record<string, any>>('/metrics')
      return data
    } catch (error) {
      this.logAxiosError('getMetrics', error)
      throw error
    }
  }

  async getCosts(): Promise<Record<string, any>> {
    try {
      const { data } = await this.client.get<Record<string, any>>('/costs')
      return data
    } catch (error) {
      this.logAxiosError('getCosts', error)
      throw error
    }
  }

  private logAxiosError(method: string, error: unknown) {
    if (this.isAxiosError(error)) {
      const axiosError = error as AxiosError
      this.logger.error(`AIEngineClient.${method} failed`, {
        message: axiosError.message,
        status: axiosError.response?.status,
        data: axiosError.response?.data,
      })
    } else if (error instanceof Error) {
      this.logger.error(`AIEngineClient.${method} failed`, {
        message: error.message,
      })
    } else {
      this.logger.error(`AIEngineClient.${method} failed`, {
        error,
      })
    }
  }

  private isAxiosError(error: unknown): error is AxiosError {
    return !!error && typeof error === 'object' && 'isAxiosError' in error
  }
}

export const aiEngineClient = new AIEngineClient()
