Jira AI Assistant
The Jira AI Assistant is a Python-based AI engine that enhances Jira workflows by processing natural language user inputs to automate tasks, generate comments, and draft emails. It leverages Azure OpenAI for language processing, integrates semantic caching for efficiency, and provides robust error handling, performance monitoring, and cost management. Designed for backend teams, it offers a clean interface for integration into Jira or similar platforms.
Features

Request Processing: Classifies user intents (e.g., task completion, comment generation, email drafting) and routes them to appropriate handlers.
Content Generation: Creates professional Jira comments and emails with customizable tone and style.
Performance Optimization: Uses caching (basic and semantic) to reduce API calls and improve response times.
Cost Management: Tracks Azure OpenAI API costs and enforces daily limits with optimization suggestions.
Reliability: Implements circuit breakers, error handling, and thread-safe metrics collection.
Monitoring: Provides health checks, performance metrics, and cost analysis for system oversight.

Directory Structure
jira_ai_assistant/
├── ai_engine/
│ ├── classification/
│ │ └── intent_classifier.py
│ ├── core/
│ │ └── config.py
│ │ pipeline.py
│ │ router.py
│ ├── generation/
│ │ └── comment_generator.py
│ │ email_generator.py
│ │ response_validator.py
│ ├── models/
│ │ └── model_manager.py
│ ├── prompts/
│ │ └── system_prompts.py
│ ├── tests/
│ ├── utils/
│ │ └── advanced_cache.py
│ │ cache.py
│ │ context_builder.py
│ │ error_handler.py
│ │ metrics.py
│ │ monitoring.py
│ └── main.py

Setup

Clone the repository:git clone <repository-url>
cd jira_ai_assistant

Install dependencies:pip install -r requirements.txt

Set environment variables:export OPENAI_API_KEY="your-api-key"
export OPENAI_API_BASE_URL="your-azure-endpoint"

File Descriptions
ai_engine/main.py

Purpose: Main entry point providing the JiraAIAssistant class for backend integration.
Key Methods:
process_user_message: Processes user inputs with validation and error handling.
get_health_status, get_performance_metrics, get_cost_analysis, get_pipeline_stats: Monitoring endpoints.
validate_configuration: Checks system configuration.

Convenience Functions: process_message, get_health, get_metrics, get_costs.

ai_engine/core/config.py

Purpose: Centralizes configuration settings (e.g., API keys, model settings, thresholds).
Key Settings: environment, openai_api_key, openai_api_base, openai_primary_model, cache_enabled, use_embedding_cache, metrics_max_records, cost_config, error_rate_threshold, confidence_threshold, quality_threshold, max_daily_cost_usd, cost_alert_percentage.

ai_engine/core/pipeline.py

Purpose: Orchestrates request processing by integrating intent classification, routing, and content generation.
Key Methods: process_user_request, get_pipeline_stats.

ai_engine/core/router.py

Purpose: Routes requests to appropriate handlers based on intent (e.g., comment generation, email drafting).
Key Methods: route_request.

ai_engine/classification/intent_classifier.py

Purpose: Classifies user intent (e.g., task_completion, email_request) for routing.
Key Methods: classify_intent.

ai_engine/generation/comment_generator.py

Purpose: Generates professional Jira comments.
Key Methods: generate_comment.

ai_engine/generation/email_generator.py

Purpose: Drafts professional emails with customizable styles.
Key Methods: generate_email.

ai_engine/generation/response_validator.py

Purpose: Validates generated content for quality and appropriateness.
Key Methods: validate_response.

ai_engine/models/model_manager.py

Purpose: Manages Azure OpenAI API calls and tracks costs.
Key Methods: generate_completion_with_cost_check, check_daily_cost_limit.

ai_engine/prompts/system_prompts.py

Purpose: Manages system prompts for intent classification and content generation, likely using hardcoded or config-based templates.
Key Methods: load_prompts, get_prompt.

ai_engine/utils/context_builder.py

Purpose: Builds user context for personalized processing.
Key Methods: build_context.

ai_engine/utils/cache.py

Purpose: Provides basic in-memory key-value caching.
Key Methods: CacheManager.get, set, clear.

ai_engine/utils/advanced_cache.py

Purpose: Optional semantic caching using embeddings for similarity-based lookups.
Key Methods: SemanticCacheManager.get_similar, set.

ai_engine/utils/error_handler.py

Purpose: Handles errors with circuit breakers and fallbacks.
Key Methods: ProductionErrorHandler.with_error_handling, get_error_stats.

ai_engine/utils/metrics.py

Purpose: Collects thread-safe metrics for classifications, API calls, pipeline executions, and cache events.
Key Methods: record_classification, record_api_call, record_pipeline_execution, record_cache_event, get_stats, get_daily_cost, get_hourly_stats, get_cache_stats.

ai_engine/utils/monitoring.py

Purpose: Monitors system health, performance, and costs with optimization suggestions.
Key Methods: ProductionMonitor.get_health_status, get_performance_metrics, get_cost_analysis.

Architecture

Input Processing:
main.py validates inputs, permissions, and cost limits, then routes to pipeline.py.

Intent Classification and Routing:
intent_classifier.py determines intent, router.py directs to comment_generator.py, email_generator.py, or backend actions.

Content Generation:
comment_generator.py and email_generator.py use model_manager.py for LLM calls, system_prompts.py for prompts, and response_validator.py for quality checks.

Optimization:
cache.py (default) and advanced_cache.py (optional) reduce API calls.
metrics.py tracks performance and costs.

Monitoring and Reliability:
error_handler.py manages failures, monitoring.py provides health and performance insights, metrics.py logs data.

Deployment

Environment: Set config.environment to prod or dev. Disable config.debug_mode in production.
Monitoring: Integrate with Prometheus/Grafana using metrics.export_metrics and monitoring.py endpoints.
Caching: Plan for Redis integration in cache.py for scalability.
Security: Implement input sanitization (future utility).
Cost Management: Configure max_daily_cost_usd and monitor via get_costs.

Contributing

Fork the repository and submit pull requests.
Follow PEP 8 and include docstrings.
Add tests in ai_engine/tests/.
Update prompt templates in system_prompts.py for new intents.

License
MIT License
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
