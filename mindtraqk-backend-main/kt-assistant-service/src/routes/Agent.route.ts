import { Router } from "express";
import jwtUtils from "../utils/jwtUtils";
import { allowedTo } from "../middlewares/allowedTo";
import { Roles } from "../utils/enum";
import AgentController from "../controllers/Agent.controller";

export const AgentRoute = Router();

// ✅ Apply authentication middleware (DO NOT wrap with catchAsync)
AgentRoute.use(jwtUtils.jwtMiddleware); // authenticated user in req.body.user

// ✅ Routes
// Start a new agent session (only employees can use)
AgentRoute.post(
  "/session/start",
  allowedTo(Roles.EMPLOYEE, Roles.MANAGER),
  AgentController.startSession
);

// Send a message to the agent
AgentRoute.post(
  "/message",
  allowedTo(Roles.EMPLOYEE, Roles.MANAGER),
  AgentController.handleMessage
);

AgentRoute.get(
  "/pending-tasks/count",
  allowedTo(Roles.EMPLOYEE, Roles.MANAGER),
  AgentController.getPendingTasksCount
);
