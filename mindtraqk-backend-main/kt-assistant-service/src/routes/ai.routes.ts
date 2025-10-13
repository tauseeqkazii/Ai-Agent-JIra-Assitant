import express from "express";
import { rateLimit } from "express-rate-limit";
import { validateRequest } from "../middlewares/validateRequest";
import { authMiddleware } from "../middlewares/auth";
import AIService from "../services/AI.service";
import { z } from "zod";

const router = express.Router();

// Rate limiting middleware
const limiter = rateLimit({
  windowMs: 15 * 60 * 1000, // 15 minutes
  max: 100, // Limit each IP to 100 requests per windowMs
  message: "Too many requests from this IP, please try again later",
});

// Request validation schema
const messageSchema = z.object({
  message: z.string().min(1).max(4000),
  context: z
    .object({
      userId: z.string(),
      teamId: z.string().optional(),
      projectId: z.string().optional(),
      metadata: z.record(z.any()).optional(),
    })
    .optional(),
});

// Routes
router.post(
  "/ai/process",
  authMiddleware,
  limiter,
  validateRequest(messageSchema),
  async (req, res) => {
    const result = await AIService.processMessage({
      message: req.body.message,
      context: {
        userId: req.user.id,
        ...req.body.context,
      },
    });
    res.json(result);
  }
);

router.get("/ai/health", async (req, res) => {
  const health = await AIService.getHealth();
  res.status(health.status === "healthy" ? 200 : 503).json(health);
});

export default router;
