# Jira AI Assistant (Python AI Engine)

This repository holds a Python AI engine that classifies user intents, generates Jira-ready updates/emails, and tracks costs/metrics using Azure OpenAI. Everything lives under `src/ai_engine/`, and the engine can be exposed over HTTP via `ai_engine_api.py`.

---

## Directory structure

```
.
├── src/
│   └── ai_engine/
│       ├── classification/         # Intent routing logic
│       │   └── intent_classifier.py
│       ├── core/                   # Pipeline orchestration
│       │   ├── config.py
│       │   ├── pipeline.py
│       │   └── router.py
│       ├── generation/             # Comment/email generation + validation
│       │   ├── comment_generator.py
│       │   ├── email_generator.py
│       │   └── response_validator.py
│       ├── models/                 # Azure OpenAI client wrapper
│       │   └── model_manager.py
│       ├── prompts/                # Prompt templates and helpers
│       │   └── system_prompts.py
│       ├── utils/                  # Caching, metrics, monitoring, error handling
│       │   ├── advanced_cache.py
│       │   ├── cache.py
│       │   ├── context_builder.py
│       │   ├── error_handler.py
│       │   ├── metrics.py
│       │   └── monitoring.py
│       ├── tests/                  # Pipeline tests
│       │   └── test_ai_pipeline.py
│       └── main.py                 # Public interface (process_message, etc.)
├── ai_engine_api.py                # FastAPI wrapper exposing the engine
├── backend/                        # Legacy FastAPI app (optional)
├── requirements.txt                # Python dependencies
└── README.md                       # You are here
```

---

## Pipeline overview

1. **entry point** – `src/ai_engine/main.py` exposes `process_message`, `get_health`, `get_metrics`, `get_costs`, `get_pipeline_stats`.  
2. **pipeline** – `core/pipeline.py` orchestrates the full workflow:
   - `TaskRouter` (`core/router.py`) classifies the request using regex-based heuristics (`classification/intent_classifier.py`).
   - For backend-only actions it returns immediately; for LLM routes it calls the relevant generator.
   - Generation modules (`generation/comment_generator.py`, `generation/email_generator.py`) leverage `models/model_manager.py` to call Azure OpenAI and `prompts/system_prompts.py` for instructions.
   - `generation/response_validator.py` enforces tone/quality and marks responses requiring approval.
   - `utils/cache.py` / `utils/advanced_cache.py` provide caching; `utils/metrics.py` records stats; `utils/error_handler.py` wraps calls with circuit breakers.
3. **return value** – the pipeline always returns a JSON-friendly dict:
   ```json
   {
     "success": true,
     "route_type": "llm_rephrasing",
     "generated_content": "...",
     "requires_user_approval": false,
     "quality_score": 0.94,
     "processing_metadata": {...},
     "pipeline_metadata": {...}
   }
   ```
   Errors include `success: false`, `error`, and `backend_action` hints.

---

## FastAPI bridge (`ai_engine_api.py`)

Run this wrapper to expose the engine over HTTP:

```bash
uvicorn ai_engine_api:app --host 127.0.0.1 --port 8300 --env-file src/ai_engine/.env
```

Endpoints:
- `POST /api/v1/process` → `process_message(user_input, user_context)`
- `GET /api/v1/health` → `get_health()`
- `GET /api/v1/metrics` → `get_metrics()`
- `GET /api/v1/costs` → `get_costs()`

Example payload:
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

The router will automatically detect `agent_operation` and route to the appropriate handler in the pipeline.

---

## Configuration

Use `src/ai_engine/.env` (or export env vars) to configure:

```
OPENAI_API_KEY=<azure-openai-key>
OPENAI_API_BASE_URL=<azure-endpoint>
AZURE_API_VERSION=2023-07-01-preview
AZURE_DEPLOYMENT_NAME=<deployment>
CACHE_ENABLED=true
USE_EMBEDDING_CACHE=false
MAX_DAILY_COST_USD=50
```

All values are parsed in `core/config.py`. Add new options there if needed.

---

## Usage examples

### Python
```python
from src.ai_engine.main import process_message

payload = {
    "user_input": "Sprint completed",
    "user_context": {
        "user_id": "user-123",
        "agent_operation": "draft_summary",
        "task_title": "Implement billing API"
    }
}

result = process_message(**payload)
print(result["generated_content"])
```

### HTTP (FastAPI)
```bash
curl -X POST http://127.0.0.1:8300/api/v1/process \
  -H "Content-Type: application/json" \
  -d '{"user_input":"completed","user_context":{"user_id":"user-123","agent_operation":"draft_summary","task_title":"Add analytics events"}}'
```

---

## Customization points

- **Prompts / style** – edit `prompts/system_prompts.py` or adjust the generators in `generation/`.
- **Intent routing** – update `classification/intent_classifier.py` and `core/router.py`.
- **Agent operations** – extend `_process_agent_operation` in `core/pipeline.py` and send a new `agent_operation` from the client.
- **Caching** – configure `CACHE_ENABLED`, tweak `utils/cache.py` or swap in Redis.
- **Error handling / metrics** – change logic in `utils/error_handler.py`, `utils/metrics.py`, `utils/monitoring.py`.
- **HTTP API** – add routes to `ai_engine_api.py` (or use `backend/api.py`) and call the functions from `main.py`.

---

## Testing

Run unit/integration tests:
```bash
pytest src/ai_engine/tests
```

Key file: `src/ai_engine/tests/test_ai_pipeline.py` exercises `process_message` end-to-end.

---

## Contributing

1. Create a feature branch and make your changes.
2. Follow PEP 8, include docstrings, and keep prompts/env updates documented.
3. Run tests before submitting a pull request.

---

## License

No explicit license is defined. Contact the maintainers before reusing the code in another product or distribution.
