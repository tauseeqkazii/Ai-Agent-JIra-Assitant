import { NextFunction, Request, Response } from "express";
import catchAsync from "../utils/catchAsync";
import { agentConversationService } from "../services/agentConversation.service";
import { LoginToken } from "../types/types";

class AgentController {
  // Start a new agent session for the user
  startSession = catchAsync(
    async (req: Request, res: Response, next: NextFunction) => {
      const userData: LoginToken = req.body.user;
      const session = await agentConversationService.startSession(userData.id);

      res.status(201).json({
        status: "success",
        message: "Agent session started",
        data: session,
      });
    }
  );

  // Handle a new user message
  handleMessage = catchAsync(
    async (req: Request, res: Response, next: NextFunction) => {
      const { sessionId, message } = req.body;

      if (!sessionId || !message) {
        return res.status(400).json({
          status: "fail",
          message: "sessionId and message are required",
        });
      }
      const userData: LoginToken = req.body.user;

      const { reply, session } = await agentConversationService.handleMessage(
        sessionId,
        message,
        userData
      );

      res.status(200).json({
        status: "success",
        reply,
        session,
      });
    }
  );

  getPendingTasksCount = catchAsync(
    async (req: Request, res: Response, next: NextFunction) => {
      const userData: LoginToken = req.body.user;

      const count = await agentConversationService.getPendingTasksCount(
        userData.id
      );

      res.status(200).json({
        status: "success",
        message: "Pending tasks count fetched successfully",
        data: { count },
      });
    }
  );
}

export default new AgentController();
