export interface AIRequest {
  message: string
  context?: {
    userId: string
    teamId?: string
    projectId?: string
    metadata?: Record<string, any>
  }
}

export interface AIResponse {
  success: boolean
  data?: {
    content: string
    routeType?: string
    backendAction?: string
    requiresApproval: boolean
    metadata: Record<string, any>
    raw?: Record<string, any>
  }
  error?: {
    code: string
    message: string
    details?: any
  }
}

export interface AIMetrics {
  totalRequests: number
  successfulRequests: number
  failedRequests: number
  averageResponseTime: number
  tokenUsage: {
    total: number
    prompt: number
    completion: number
  }
}
