import { AgentSession, IAgentSession } from "../models/AgentSession";
import { LoginToken } from "../types/types";
import { AgentTaskState } from "../utils/enum";
import jiraService from "../utils/jiraService";
import { llmService } from "../utils/llmService";

export const agentConversationService = {
  /**
   * Create a new session with Jira tasks
   */
  async startSession(userId: string): Promise<IAgentSession> {
    const pendingTasks = await jiraService.getPendingTasks(userId);
    // [{ taskId, title, status, createdAt, updatedAt }]

    const session = await AgentSession.create({
      userId,
      currentIndex: 0,
      tasks: pendingTasks.map((t) => ({
        taskId: t.taskId,
        title: t.title,
        status: t.status,
        createdAt: t.createdAt,
        updatedAt: t.updatedAt,
        state: AgentTaskState.AWAITING_UPDATE,
      })),
    });

    return session;
  },

  /**
   * Handle a new user message and advance the conversation
   */
  async handleMessage(
    sessionId: string,
    userMessage: string,
    userData: LoginToken
  ): Promise<{ reply: string; session: IAgentSession }> {
    const isAffirmative = (s: string) =>
      /\b(yes|yep|yeah|y|ok|okay|sure|go ahead|confirm|proceed)\b/i.test(s);
    const saidDone = (s: string) =>
      /\b(done|completed|complete|finished|resolved|closed)\b/i.test(s);

    const session = await AgentSession.findById(sessionId);
    if (!session) throw new Error("Session not found");

    // Guard: no tasks
    if (!session.tasks?.length) {
      return {
        session,
        reply:
          "I couldn’t find any pending Jira tasks for you. If that seems wrong, try refreshing or reconnecting Jira.",
      };
    }

    // Guard: index drift
    if (
      session.currentIndex < 0 ||
      session.currentIndex >= session.tasks.length
    ) {
      session.currentIndex = 0;
      await session.save();
    }

    const task = session.tasks[session.currentIndex];

    switch (task.state) {
      case AgentTaskState.AWAITING_UPDATE: {
        const draftRaw = await llmService.generateSummary(
          userMessage,
          task.title,
          userData
        );
        const draft = (draftRaw || "").trim() || "Update noted.";
        task.draftSummary = draft;

        if (saidDone(userMessage)) {
          task.pendingStatusDone = true;
        }

        task.state = AgentTaskState.AWAITING_EDIT_DECISION;
        await session.save();
        return {
          session,
          reply: `Here's the summary I generated: "${draft}"\nDo you want to update anything in it?`,
        };
      }

      case AgentTaskState.AWAITING_EDIT_DECISION: {
        if (isAffirmative(userMessage)) {
          task.state = AgentTaskState.AWAITING_EDIT_INPUT;
          await session.save();
          return {
            session,
            reply: "Okay, please tell me what changes you'd like to make.",
          };
        } else {
          task.state = AgentTaskState.AWAITING_CONFIRM;
          await session.save();
          return {
            session,
            reply: `I'm about to update the ticket with: "${task.draftSummary}". Should I go ahead?`,
          };
        }
      }

      case AgentTaskState.AWAITING_EDIT_INPUT: {
        const updatedRaw = await llmService.applyEdits(
          task.draftSummary!,
          userMessage,
          userData
        );
        const updatedSummary = (updatedRaw || "").trim() || task.draftSummary!;
        task.draftSummary = updatedSummary;
        task.state = AgentTaskState.AWAITING_CONFIRM;
        await session.save();
        return {
          session,
          reply: `Here's the updated summary: "${updatedSummary}"\nShould I go ahead and update Jira?`,
        };
      }

      case AgentTaskState.AWAITING_CONFIRM: {
        if (!isAffirmative(userMessage)) {
          return {
            session,
            reply:
              "Okay, I won't update it yet. What would you like to change?",
          };
        }

        let updateType = await llmService.analyzeUpdateType(
          task.draftSummary!,
          userData
        );

        // If user implied completion earlier, force status update too
        if (task.pendingStatusDone && updateType === "comment_only") {
          updateType = "comment_and_status";
        }

        if (updateType === "comment_only") {
          await jiraService.addComment(
            task.taskId,
            task.draftSummary!,
            userData
          );
        } else if (updateType === "status_only") {
          if (task.status !== "Done") {
            const transitionId = await jiraService.getTransitionId(
              task.taskId,
              "Done",
              userData
            );
            await jiraService.updateTask(
              task.taskId,
              { type: "status", value: transitionId },
              userData
            );
            task.status = "Done"; // keep session in sync
          }
        } else if (updateType === "comment_and_status") {
          await jiraService.addComment(
            task.taskId,
            task.draftSummary!,
            userData
          );
          if (task.status !== "Done") {
            const transitionId = await jiraService.getTransitionId(
              task.taskId,
              "Done",
              userData
            );
            await jiraService.updateTask(
              task.taskId,
              { type: "status", value: transitionId },
              userData
            );
            task.status = "Done";
          }
        }

        // finalize current task
        task.finalSummary = task.draftSummary;
        task.state = AgentTaskState.COMPLETED;

        // ✅ only advance/announce when we truly have a next actionable task
        let advanced = false;
        let nextIndex = session.currentIndex + 1;
        while (nextIndex < session.tasks.length) {
          if (session.tasks[nextIndex].state !== AgentTaskState.COMPLETED) {
            session.currentIndex = nextIndex;
            session.tasks[session.currentIndex].state =
              AgentTaskState.AWAITING_UPDATE;
            advanced = true;
            break;
          }
          nextIndex++;
        }

        await session.save();

        return {
          session,
          reply: advanced
            ? `Ticket updated. Let's move to your next task: "${
                session.tasks[session.currentIndex].title
              }"`
            : "Ticket updated. All tasks are done. Great job!",
        };
      }

      default:
        return { session, reply: "All tasks are complete." };
    }
  },
  async getPendingTasksCount(userId: string): Promise<number> {
    const pendingTasks = await jiraService.getPendingTasks(userId);
    return pendingTasks.length;
  },
};
