import { LoginToken } from '../types/types'
import {
  AIEngineProcessResponse,
  aiEngineClient,
} from './aiEngineClient'

const ensureSuccess = (
  response: AIEngineProcessResponse,
  fallbackMessage: string,
) => {
  if (!response.success || !response.generated_content) {
    throw new Error(
      response.error_message || response.error || fallbackMessage,
    )
  }
}

export const llmService = {
  async generateSummary(
    userUpdate: string,
    taskTitle: string,
    user: LoginToken,
  ): Promise<string> {
    const response = await aiEngineClient.processMessage({
      user_input: userUpdate,
      user_context: {
        user_id: user.id,
        agent_operation: 'draft_summary',
        task_title: taskTitle,
      },
    })

    ensureSuccess(response, 'Failed to generate task summary')
    return response.generated_content!.trim()
  },

  async applyEdits(
    draftSummary: string,
    userEdits: string,
    user: LoginToken,
  ): Promise<string> {
    const response = await aiEngineClient.processMessage({
      user_input: userEdits,
      user_context: {
        user_id: user.id,
        agent_operation: 'apply_edits',
        current_summary: draftSummary,
      },
    })

    ensureSuccess(response, 'Failed to apply edits to summary')
    return response.generated_content!.trim()
  },

  async analyzeUpdateType(
    summary: string,
    user: LoginToken,
  ): Promise<'status_only' | 'comment_only' | 'comment_and_status'> {
    const response = await aiEngineClient.processMessage({
      user_input: summary,
      user_context: {
        user_id: user.id,
        agent_operation: 'analyze_update',
      },
    })

    if (!response.success || !response.generated_content) {
      return 'comment_only'
    }

    const normalized = response.generated_content.trim().toLowerCase()
    if (
      normalized === 'status_only' ||
      normalized === 'comment_only' ||
      normalized === 'comment_and_status'
    ) {
      return normalized
    }
    return 'comment_only'
  },
}
