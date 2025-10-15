# Jira AI Assistant – Project Overview

This repository glues together three major pieces:

1. **Python AI Engine** (`src/ai_engine` + FastAPI wrapper) – the model pipeline that classifies intents and generates Jira-ready summaries/emails with Azure OpenAI.
2. **Node.js KT Assistant Service** (`mindtraqk-backend-main/kt-assistant-service`) – REST API that powers the “Mbot / Magent” chat experience in the React frontend.
3. **Mindtraqk Web App** (`mindtraqk-frontend-main`) – React UI that exposes the agent to end users.

The repo also contains a Python FastAPI service (`ai_engine_api.py`) that exposes the AI engine over HTTP so the Node backend can call it.

---

## 1. Top-level layout

```
.
├── backend/                     # Old FastAPI harness (legacy, optional)
├── mindtraqk-backend-main/      # Microservices written in Node.js/TypeScript
│   ├── analysis-service/
│   ├── auth-service/
│   └── kt-assistant-service/    # Service that integrates with the Python engine
├── mindtraqk-frontend-main/     # React (Vite) application containing Mbot UI
├── src/                         # Python AI engine source code (core pipeline)
│   └── ai_engine/
├── ai_engine_api.py             # FastAPI wrapper for the Python engine
├── requirements.txt             # Python dependencies for the AI engine wrapper
├── package.json (frontend)      # Present in mindtraqk-frontend-main/
├── README.md                    # You are here
└── ...
```

---

## 2. Python AI Engine (`src/ai_engine`)

1. **`core/`**

   - `config.py` – Consolidates environment variables (Azure OpenAI keys, model names, thresholds).
   - `pipeline.py` – Orchestrator that calls router, generators, metrics, cache, etc.
   - `router.py` – Decides which processing path to use (backend action vs. LLM content generation).

2. **`classification/`**

   - `intent_classifier.py` – Regex- and keyword-based intent routing (task completion, email drafting, etc.).

3. **`generation/`**

   - `comment_generator.py`, `email_generator.py` – Produce Jira comments/emails using LLMs.
   - `response_validator.py` – Enforces tone/quality thresholds before returning to the caller.

4. **`models/`**

   - `model_manager.py` – Wraps OpenAI/Azure OpenAI clients, handles retries, cost tracking, rate limits.

5. **`prompts/`**

   - `system_prompts.py` – Central store for reusable prompt templates and helper builders.

6. **`utils/`**

   - `advanced_cache.py`, `cache.py` – Response caching (semantic + standard).
   - `context_builder.py` – Constructs richer context from raw user data.
   - `error_handler.py`, `monitoring.py`, `metrics.py` – Observability, circuit breakers, cost reporting.
   - `production_monitor.py`, `production_setup.py` – Deployment helpers.

7. **`tests/`**

   - `test_ai_pipeline.py` and related fixtures exercise the pipeline end-to-end.

8. **`main.py`**
   - Provides a friendly class `JiraAIAssistant` and convenience functions: `process_message`, `get_health`, `get_metrics`, `get_costs`.

---

## 3. FastAPI bridge (`ai_engine_api.py`)

This file exposes the AI engine through HTTP:

- `POST /api/v1/process` – Calls `process_message` with the provided payload.
- `GET /api/v1/health` – Returns health info (`get_health`).
- `GET /api/v1/metrics` – Returns pipeline/LLM metrics.
- `GET /api/v1/costs` – Returns cost analysis.

The endpoint expects input like:

```json
{
  "user_input": "completed",
  "user_context": {
    "user_id": "68b02a3c551abd93b8fdc72f",
    "agent_operation": "draft_summary",
    "task_title": "Add Analytics events in Dashboard Page"
  }
}
```

and returns the full pipeline response (success flag, generated text, route type, quality flags, metadata).

---

## 4. KT Assistant Service (`mindtraqk-backend-main/kt-assistant-service`)

This service glues the frontend to the Python AI engine via HTTP.

1. **Entry point**

   - `src/app.ts` – Express setup, loads routes (`/api/v1/...`).

2. **Routes**

   - `src/routes/Agent.route.ts` – Exposes `/agent/session/start`, `/agent/message`, `/agent/pending-tasks/count`.
   - `src/routes/ai.routes.ts` – `/ai/process`, `/ai/health` (proxy to AI engine).
   - `src/routes/Root.routes.ts` – Aggregates module routes.

3. **Controllers**

   - `src/controllers/Agent.controller.ts` – Accepts requests from the frontend, calls service layer.

4. **Services**

   - `src/services/agentConversation.service.ts` – Conversation state machine; calls Jira APIs, LLM helpers.
   - `src/services/AI.service.ts` – Wraps external LLM service. In the current integration it sends requests to the Python engine through `aiEngineClient`.

5. **Utilities**

   - `src/utils/aiEngineClient.ts` – Axios client pointing at `AI_ENGINE_URL` (`/process`, `/health`, etc.).
   - `src/utils/llmService.ts` – Convenience wrapper for agent operations (draft summary, apply edits, analyze update).
   - `src/utils/jiraService.ts` – Integrates with Jira REST API using stored tokens.
   - `src/utils/metrics.ts`, `src/utils/logger.ts`, `src/utils/redis.ts`, `src/utils/apiResponse.ts` – Observability and helpers.
   - `src/middlewares` – Authentication (`auth.ts` -> JWT), request validation (Zod), monitoring.

6. **Types**

   - `src/types/ai.types.ts` – Expected shapes from LLM responses.
   - `src/types/types.ts` – Login token/user shape.
   - `src/types/express.d.ts` – Express augmentation to add `req.user`.

7. **Tests**

   - `src/tests/ai.service.test.ts` – Ensures the AI proxy handles success/failure and rate limits.

8. **Configuration**
   - `.env` – Service config (port, MongoDB, JWT, OpenAI, AI engine URL).

---

## 5. Auth Service (`mindtraqk-backend-main/auth-service`)

Contains user management, integrations (Jira/Slack/etc.), and JWT middleware:

- `src/services/User.service.ts` – CRUD for users.
- `src/controller/User.controller.ts` – Express endpoint handlers.
- `src/utils/jwtUtils.ts` (re-exported in KT service) – Validates the cookie (`mindtraqk-token`).
- Other subdirectories (`routes`, `models`, `Integrations`) manage third-party tokens.

---

## 6. Analysis service (`mindtraqk-backend-main/analysis-service`)

Handles analytics/usage data. Key pieces mirror KT service: Express app, controllers, MongoDB models. Not directly involved in the AI integration, but shares env/Mongo utilities.

---

## 7. Frontend (`mindtraqk-frontend-main`)

1. **Store (Zustand)**

   - `src/store/agentStore.ts` – Tracks agent session state, messages, loading flags. Calls KT assistant API.
   - `src/store/KtDataStore.ts`, `src/store/authStore.ts` – Additional global state (KT alerts, authentication).

2. **Components**

   - `src/components/mbot-comp/MbotComp.tsx` – Chat UI for Mbot/Magent. Switches between normal assistant and agent mode.
   - Numerous other components under `components/*` for dashboards, alerts, settings.

3. **Services**

   - `src/services/apiClientKtService.ts` – Axios instance for backend calls (`API_BASE_URL_KT_ASSISTANT`).
   - Additional clients for auth and analysis.

4. **Routing / Layout**

   - `src/routes`, `src/pages`, `src/layouts` – Standard React SPA modules.

5. **Assets & Styles**

   - `src/assets`, `src/styles`, Tailwind configuration (`tailwind.config.js` in project root).

6. **Config**
   - `.env` – Frontend base URLs for different services.

---

## 8. Legacy FastAPI harness (`backend/`)

Contains an older FastAPI service that also exposed the AI engine (`backend/api.py`). It can be used in place of `ai_engine_api.py` but isn’t required if you rely on the new wrapper. Consult `backend/README` for details if needed.

---

## 9. Environment variables

### Python AI Engine (`src/ai_engine/.env`)

- `OPENAI_API_KEY`, `OPENAI_API_BASE_URL`, `AZURE_API_VERSION`
- Model/deployment names, cache flags, cost thresholds.

### FastAPI wrapper (`ai_engine_api.py`)

- Inherits AI engine vars.
- `AI_ENGINE_PORT` (default 8000).

### KT Assistant service (`mindtraqk-backend-main/kt-assistant-service/.env`)

- `PORT`, `MONGO_URI`, `JWT_SECRET`, etc.
- `AI_ENGINE_URL`, `AI_ENGINE_TOKEN` – point to the FastAPI service (e.g., `http://127.0.0.1:8300/api/v1`).

### Frontend (`mindtraqk-frontend-main/.env`)

- `VITE_API_BASE_URL_KT_ASSISTANT`, `VITE_API_URL`, etc.

---

## 10. Running the system locally

1. **Install Python deps**

   ```bash
   pip install -r requirements.txt
   ```

2. **Install Node deps**

   ```bash
   cd mindtraqk-backend-main/kt-assistant-service && npm install
   cd ../auth-service && npm install
   cd ../../mindtraqk-frontend-main && npm install
   ```

3. **Run AI engine (FastAPI)**

   ```bash
   uvicorn ai_engine_api:app --host 127.0.0.1 --port 8300 --env-file src/ai_engine/.env
   ```

4. **Run KT assistant service**

   ```bash
   cd mindtraqk-backend-main/kt-assistant-service
   npm run dev   # or npm run start
   ```

5. **Run auth/analysis services** as needed (optional for agent-only testing).

6. **Run frontend**

   ```bash
   cd mindtraqk-frontend-main
   npm run dev   # Vite dev server (defaults to http://localhost:5173)
   ```

7. **Test AI proxy**

   ```bash
   curl -X POST http://127.0.0.1:8300/api/v1/process \
     -H "Content-Type: application/json" \
     -d '{"user_input":"completed","user_context":{"user_id":"test","agent_operation":"draft_summary","task_title":"Add Analytics events"}}'
   ```

8. **Run lints/tests**
   - Python: `pytest tests/` (under `src/ai_engine/tests`).
   - Node (KT service): `npm run build` and `npm test`.
   - Frontend: `npm run lint`, `npm run test` (if configured).

---

## 11. Customising behaviour

- **Add new FastAPI endpoints:** edit `ai_engine_api.py` (or `backend/api.py`) and call the relevant functions from `src.ai_engine.main`.
- **Change intent routing:** adjust patterns/logic in `classification/intent_classifier.py`.
- **Modify generated text:** update prompts (`prompts/system_prompts.py`) or logic in `generation/*.py`.
- **Swap/augment models:** extend `models/model_manager.py` to call different providers.
- **Adjust conversation flow:** edit `mindtraqk-backend-main/kt-assistant-service/src/services/agentConversation.service.ts`.
- **Frontend UX tweaks:** update `MbotComp.tsx` or the Zustand store in `agentStore.ts`.

---

## 12. Useful references

- `src/ai_engine/core/pipeline.py` – best place to understand end-to-end flow.
- `mindtraqk-backend-main/kt-assistant-service/src/utils/aiEngineClient.ts` – handshake between Node and Python.
- `ai_engine_api.py` – minimal FastAPI wrapper you can repurpose for other backends.
- `tests/test_ai_pipeline.py` (Python) and `src/tests/ai.service.test.ts` (Node) – examples of programmatic usage.

---

## 13. Contributing

1. Create a feature branch, make your changes, and run relevant tests.
2. Follow PEP 8 for Python and the existing ESLint/Prettier config for TypeScript/React.
3. Keep prompt updates and env variable additions documented.
4. Submit a pull request summarising the change and testing performed.

---

## 14. License

This repository currently does not declare a specific license. Please contact the project owners before reusing the code in a different product or distribution.
