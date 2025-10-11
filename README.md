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
