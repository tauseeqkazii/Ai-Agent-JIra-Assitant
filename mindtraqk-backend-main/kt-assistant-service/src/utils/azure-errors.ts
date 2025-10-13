export class AzureOpenAIError extends Error {
  constructor(
    message: string,
    public code: string,
    public status: number,
    public isRetryable: boolean,
  ) {
    super(message)
    this.name = 'AzureOpenAIError'
  }
}

export const handleAzureError = (error: any): AzureOpenAIError => {
  // Azure OpenAI specific error codes
  if (error.response?.status === 429) {
    return new AzureOpenAIError(
      'Rate limit exceeded',
      'RATE_LIMIT_EXCEEDED',
      429,
      true,
    )
  }

  if (error.response?.status === 401) {
    return new AzureOpenAIError(
      'Invalid API key or unauthorized',
      'UNAUTHORIZED',
      401,
      false,
    )
  }

  if (error.response?.status === 404) {
    return new AzureOpenAIError(
      'Model or deployment not found',
      'RESOURCE_NOT_FOUND',
      404,
      false,
    )
  }

  if (error.response?.status === 503) {
    return new AzureOpenAIError(
      'Azure OpenAI service unavailable',
      'SERVICE_UNAVAILABLE',
      503,
      true,
    )
  }

  return new AzureOpenAIError(
    error.message || 'Unknown error',
    'INTERNAL_ERROR',
    500,
    false,
  )
}
