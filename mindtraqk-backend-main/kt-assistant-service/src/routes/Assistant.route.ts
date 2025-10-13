import { Router } from "express";
import AssistantController from "../controllers/Assistant.controller";
import jwtUtils from "../utils/jwtUtils";
export const assistantRoute = Router();

assistantRoute.use(jwtUtils.jwtMiddleware);
assistantRoute.post("/ask", AssistantController.getGPTResponse);
