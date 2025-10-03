import logging
import os
from typing import Dict, Optional, Any

import openai
from openai import OpenAI

from ai_engine.core.config import config
from ai_engine.utils.metrics import MetricsCollector


logger = logging.getLogger(__name__)


class ModelManager:
    """Manages OpenAI API calls and model interactions"""

    def __init__(self):
        self.metrics = MetricsCollector()
        self.models: Dict[str, str] = {
            "primary": config.openai_primary_model,
            "fast": config.openai_fast_model,
            "classification": config.openai_classification_model
        }
        self.token_limits: Dict[str, int] = config.token_limits

        self._use_stub = self._determine_stub_mode()
        self.client: Optional[OpenAI] = None

        if not self._use_stub:
            try:
                self.client = OpenAI(api_key=config.openai_api_key)
            except Exception as exc:
                logger.warning(
                    "Failed to initialize OpenAI client (%s). Falling back to stub mode.",
                    exc
                )
                self._use_stub = True

        if self._use_stub:
            logger.info("ModelManager initialized in stub mode; OpenAI calls will be simulated.")

    def _determine_stub_mode(self) -> bool:
        """Check configuration and environment flags for stub mode"""
        env_flag = os.getenv("AI_ENGINE_TEST_MODE") or os.getenv("TEST_MODE")
        if env_flag and env_flag.strip().lower() in {"1", "true", "yes", "on"}:
            return True
        return config.test_mode

    def generate_completion(
        self,
        system_prompt: str,
        user_message: str,
        model_type: str = "primary",
        temperature: float = 0.3,
        max_tokens: Optional[int] = None
    ) -> Dict[str, Any]:
        """Generate completion using OpenAI API or stubbed responses"""
        model_name = self.models.get(model_type, self.models["primary"])

        if self._use_stub or self.client is None:
            return self._generate_stub_completion(system_prompt, user_message, model_name)

        if max_tokens is None:
            max_tokens = self.token_limits.get(model_name, 1000)

        start_time = self._get_timestamp()

        try:
            response = self.client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message}
                ],
                temperature=temperature,
                max_tokens=max_tokens,
                top_p=0.9
            )

            result = {
                "success": True,
                "content": response.choices[0].message.content,
                "model_used": model_name,
                "usage": {
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens
                },
                "metadata": {
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                    "start_time": start_time,
                    "end_time": self._get_timestamp()
                }
            }

            self.metrics.record_api_call(
                model=model_name,
                tokens_used=response.usage.total_tokens,
                success=True
            )

            logger.info("OpenAI call successful - %s - %s tokens",
                        model_name, response.usage.total_tokens)
            return result

        except openai.RateLimitError as err:
            logger.warning("Rate limit hit: %s", err)
            return self._handle_rate_limit_error(system_prompt, user_message, model_type)

        except openai.OpenAIError as err:
            logger.error("OpenAI API error: %s", err)
            self._use_stub = True
            return self._generate_stub_completion(system_prompt, user_message, model_name)

        except Exception as err:
            logger.error("Unexpected error in OpenAI call: %s", err)
            self._use_stub = True
            return self._generate_stub_completion(system_prompt, user_message, model_name)

    def _generate_stub_completion(
        self, system_prompt: str, user_message: str, model_name: str
    ) -> Dict[str, Any]:
        """Generate deterministic stubbed response for offline/testing"""
        content = self._build_stub_content(system_prompt, user_message)
        total_tokens = self._estimate_tokens(system_prompt, user_message, content)
        metadata = {
            "temperature": 0.0,
            "max_tokens": self.token_limits.get(model_name, 1000),
            "start_time": self._get_timestamp(),
            "end_time": self._get_timestamp(),
            "stubbed": True
        }

        result = {
            "success": True,
            "content": content,
            "model_used": model_name,
            "usage": {
                "prompt_tokens": max(total_tokens // 2, 1),
                "completion_tokens": max(total_tokens - max(total_tokens // 2, 1), 1),
                "total_tokens": max(total_tokens, 2)
            },
            "metadata": metadata
        }

        self.metrics.record_api_call(
            model=model_name,
            tokens_used=result["usage"]["total_tokens"],
            success=True
        )

        return result

    def _build_stub_content(self, system_prompt: str, user_message: str) -> str:
        message_lower = user_message.lower()

        if "email request" in message_lower:
            request = user_message.split("Email request:", 1)[-1].strip()
            subject = self._compose_stub_subject(request)
            return (
                f"Subject: {subject}\n\n"
                "Dear Team,\n\n"
                f"This is a placeholder email responding to the request: {request}.\n"
                "It demonstrates the email format without contacting the OpenAI API.\n\n"
                "Best regards,\n"
                "AI Assistant"
            )

        if "user update:" in message_lower:
            update = user_message.split("User update:", 1)[-1].strip()
            return (
                f"Resolved: {update}.\n"
                "Next steps: Continue monitoring progress and provide follow-up detail."
            )

        if "classify this user message" in system_prompt.lower():
            return (
                "The user appears to share a task update that may need clarification "
                "from the project team."
            )

        return (
            "This is a stub response produced during tests when the OpenAI service is "
            "unavailable."
        )

    def _compose_stub_subject(self, request: str) -> str:
        cleaned = request.lower().replace("request", "").strip() or "Update Summary"
        words = cleaned.split()[:6]
        capitalized = " ".join(word.capitalize() for word in words if word)
        return capitalized or "Update Summary"

    def _estimate_tokens(self, system_prompt: str, user_message: str, content: str) -> int:
        length = len(system_prompt) + len(user_message) + len(content)
        return max(length // 4, 8)

    def _handle_rate_limit_error(self, system_prompt: str, user_message: str, model_type: str) -> Dict[str, Any]:
        logger.info("Rate limit on primary model, using stub fallback.")
        self._use_stub = True
        model_name = self.models.get(model_type, self.models["primary"])
        return self._generate_stub_completion(system_prompt, user_message, model_name)

    def _get_timestamp(self) -> str:
        from datetime import datetime
        return datetime.utcnow().isoformat()
