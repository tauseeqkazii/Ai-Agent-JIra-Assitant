import { Response } from "express";
import { z } from "zod";
import axios from "axios";
import OpenAI from "openai";
import { assistantResValidation } from "../utils/validation";
import ResponseHandler from "../utils/apiResponse";
import dotenv from "dotenv";
import { LoginToken } from "../types/types";
import redis from "../utils/redisClient";
dotenv.config();

const openai = new OpenAI({
  baseURL: process.env.OPENAI_API_BASE_URL,
  apiKey: process.env.OPENAI_API_KEY,
});

const MODEL = "gpt-4o-mini";

/** Top-level sections available in your payload */
type SectionKey =
  | "workDistribution"
  | "workDepth"
  | "weeklyAnalysis" // meetings
  | "productivityReport"
  | "proactiveAnalysis"
  | "performanceReport"
  | "okrAlignment"
  | "dailyProductivity"
  | "contributionInsights"
  | "burnoutReport"
  | "aiInsight";

/** Map prompt intent → section key(s) */
const SECTION_KEYWORDS: Record<SectionKey, string[]> = {
  workDistribution: [
    "work distribution",
    "workdistribution",
    "deep work",
    "shallow work",
    "support work",
    "distribution",
  ],
  workDepth: [
    "work depth",
    "depth score",
    "overall score",
    "completion percentage",
    "change from last week",
  ],
  weeklyAnalysis: [
    "meeting",
    "meetings",
    "calendar",
    "weekly analysis",
    "weekly summary",
    "talk time",
    "productivity of meetings",
    "participants",
    "outcomes",
    "todos",
    "decisions",
  ],
  productivityReport: [
    "productivity report",
    "productivity score",
    "change from last week",
    "productivity",
  ],
  proactiveAnalysis: [
    "proactive",
    "risk",
    "risks",
    "potential risks",
    "issues",
    "challenges",
  ],
  performanceReport: [
    "performance report",
    "performance",
    "daily performance",
    "meetings contributed",
  ],
  okrAlignment: ["okr", "okrs", "alignment", "key results", "objectives"],
  dailyProductivity: ["daily productivity", "daily score", "scores by day"],
  contributionInsights: [
    "contribution",
    "insight",
    "insights",
    "deep work tasks list",
    "shallow work tasks list",
  ],
  burnoutReport: [
    "burnout",
    "fatigue",
    "stuck tasks",
    "high focus",
    "burnout days",
    "no tasks",
  ],
  aiInsight: ["ai insight", "main highlight", "insights summary"],
};

/** For the meetings section, we can narrow to facets if the prompt asks */
type MeetingFacet =
  | "weeklySummary"
  | "participants"
  | "mainOutcomes"
  | "todos"
  | "decisions"
  | "dailyMetrics";

const MEETING_FACET_KEYWORDS: Record<MeetingFacet, string[]> = {
  weeklySummary: [
    "summary",
    "overall",
    "overview",
    "review",
    "productivity",
    "outcome clarity",
    "most common classification",
    "total meetings",
  ],
  participants: [
    "participant",
    "participants",
    "contribution",
    "talk time",
    "average productivity",
  ],
  mainOutcomes: ["outcomes", "main outcomes"],
  todos: ["todo", "todos", "action items"],
  decisions: ["decision", "decisions"],
  dailyMetrics: ["daily", "per day", "day-wise", "day wise", "daily metrics"],
};

function detectRelevantSections(prompt: string): SectionKey[] {
  const p = prompt.toLowerCase();
  const hits = new Set<SectionKey>();
  (Object.keys(SECTION_KEYWORDS) as SectionKey[]).forEach((k) => {
    if (SECTION_KEYWORDS[k].some((kw) => p.includes(kw))) hits.add(k);
  });
  return Array.from(hits);
}

function detectMeetingFacets(prompt: string): MeetingFacet[] {
  const p = prompt.toLowerCase();
  const hits = new Set<MeetingFacet>();
  (Object.keys(MEETING_FACET_KEYWORDS) as MeetingFacet[]).forEach((k) => {
    if (MEETING_FACET_KEYWORDS[k].some((kw) => p.includes(kw))) hits.add(k);
  });
  return Array.from(hits);
}

/** From your large payload, keep only the requested sections.
 *  If meetings (weeklyAnalysis) is requested, optionally narrow to requested facets.
 */
function filterPayloadByIntent(
  raw: any,
  sections: SectionKey[],
  prompt: string
) {
  // If no detected sections, keep everything (model will still be forced to answer only the asked thing).
  if (sections.length === 0) return raw;

  const filtered: any = {};
  for (const key of sections) {
    if (key !== "weeklyAnalysis") {
      filtered[key] = raw?.[key];
    } else {
      // Meetings facet filtering
      const facets = detectMeetingFacets(prompt);
      const src = raw?.weeklyAnalysis || null;
      if (!src) {
        filtered.weeklyAnalysis = null;
        continue;
      }

      if (facets.length === 0) {
        // Default concise meetings view if user didn’t specify a facet
        filtered.weeklyAnalysis = {
          weeklySummary: src.weeklySummary
            ? {
                totalMeetingsAnalyzed: src.weeklySummary.totalMeetingsAnalyzed,
                overallProductivity: src.weeklySummary.overallProductivity,
                mostCommonClassification:
                  src.weeklySummary.mostCommonClassification,
                outcomeClarity: src.weeklySummary.outcomeClarity,
                review: src.weeklySummary.review,
              }
            : null,
        };
      } else {
        const narrowed: any = {};
        for (const f of facets) {
          if (f === "weeklySummary") {
            narrowed.weeklySummary = src.weeklySummary
              ? {
                  totalMeetingsAnalyzed:
                    src.weeklySummary.totalMeetingsAnalyzed,
                  overallProductivity: src.weeklySummary.overallProductivity,
                  mostCommonClassification:
                    src.weeklySummary.mostCommonClassification,
                  outcomeClarity: src.weeklySummary.outcomeClarity,
                  review: src.weeklySummary.review,
                }
              : null;
          } else if (f === "participants") {
            narrowed.participants = src.participants ?? null;
          } else if (f === "mainOutcomes") {
            narrowed.mainOutcomes = src.mainOutcomes ?? null;
          } else if (f === "todos") {
            narrowed.todos = src.todos ?? null;
          } else if (f === "decisions") {
            narrowed.decisions = src.decisions ?? null;
          } else if (f === "dailyMetrics") {
            narrowed.dailyMetrics = src.dailyMetrics ?? null;
          }
        }
        filtered.weeklyAnalysis = narrowed;
      }
    }
  }
  return filtered;
}

class AssistantService {
  async getGPTResponse(
    promptData: z.infer<typeof assistantResValidation>,
    res: Response,
    userData: LoginToken
  ) {
    const { prompt } = promptData;

    // Guardrail: require analysis-related intent
    const allowedKeywords = [
      // generic
      "analysis",
      "report",
      "score",
      "trend",
      "change",
      // specific
      "workdistribution",
      "work distribution",
      "deep work",
      "shallow work",
      "work depth",
      "depth score",
      "meeting",
      "meetings",
      "participants",
      "outcomes",
      "todos",
      "decisions",
      "productivity report",
      "productivity score",
      "performance report",
      "okr",
      "alignment",
      "daily productivity",
      "contribution insights",
      "burnout",
      "fatigue",
      "stuck tasks",
      "proactive",
      "risk",
      "risks",
      "potential risks",
      "ai insight",
    ];
    const isRelated = allowedKeywords.some((kw) =>
      prompt.toLowerCase().includes(kw.toLowerCase())
    );
    if (!isRelated) {
      return ResponseHandler.badRequest(
        res,
        "I can only answer questions about your analysis data (meetings, productivity, work depth, burnout, OKRs, etc.)."
      );
    }

    try {
      // 1) Rate limit per user per day
      const dayKey = `gpt-usage:${userData.id}:${new Date()
        .toISOString()
        .slice(0, 10)}`;
      const used = await redis.get(dayKey);
      if (used && parseInt(used) >= 10) {
        return ResponseHandler.tooManyRequests(
          res,
          "Daily GPT usage limit reached (10 calls/day)"
        );
      }
      await redis.multi().incr(dayKey).expire(dayKey, 86400).exec();

      // 2) Fetch your large “latest analysis data”
      const apiUrl = `${process.env.ANALYZE_BASE_URL}/api/v1/fetch/user/${userData.id}`;
      const { data } = await axios.get(apiUrl);
      const raw = data?.data;

      // 3) Detect intent → filter payload
      const sections = detectRelevantSections(prompt);
      const filtered = filterPayloadByIntent(raw, sections, prompt);

      // 4) Strong instructions to keep answer scoped + concise
      const systemMessage = `
You are an analytical assistant.
Use ONLY the JSON provided by the user. Do NOT invent data or advice.
Answer ONLY what the user asked. If they ask for meetings, restrict to meetings.
Keep it concise, in plain text (no lists) unless the user asks for a list.
If a requested section or field is missing, reply exactly: "No data available."
      `.trim();

      const userMessage = `
Here is the latest analysis JSON (filtered to relevant sections when detected):
${JSON.stringify(filtered, null, 2)}

User question: ${prompt}

Rules:
- Answer strictly from the JSON above.
- If multiple sections are present, respond only about what the question targets.
- Prefer a short, direct answer. If the user asked "only about meetings", do not include any non-meeting info.
- If the needed data is missing in the JSON, say "No data available."
      `.trim();

      // 5) Call OpenAI
      const aiResponse = await openai.chat.completions.create({
        model: MODEL,
        messages: [
          { role: "system", content: systemMessage },
          { role: "user", content: userMessage },
        ],
        max_tokens: 600,
        temperature: 0.2,
      });

      const reply =
        aiResponse.choices?.[0]?.message?.content?.trim() ||
        "No data available.";

      return ResponseHandler.success(res, "AI response generated", { reply });
    } catch (err: any) {
      console.error("❌ Error in getGPTResponse:", err?.response?.data || err);
      return ResponseHandler.internalError(
        res,
        "Failed to generate AI response",
        err?.response?.data || err
      );
    }
  }
}

export default new AssistantService();
