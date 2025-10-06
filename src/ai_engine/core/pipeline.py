"""
AI Processing Pipeline Module
Orchestrates the complete AI workflow from routing to response generation
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime

from .router import TaskRouter
from ..generation.comment_generator import CommentGenerator
from ..generation.email_generator import EmailGenerator
from ..generation.response_validator import ResponseValidator
from ..models.model_manager import ModelManager
from ..utils.metrics import MetricsCollector
from ..utils.cache import CacheManager
from ..core.config import config

logger = logging.getLogger(__name__)


class AIProcessingPipeline:
    """
    Main AI pipeline that orchestrates the entire AI processing flow
    Routes requests and handles LLM processing with shared dependencies
    """
    
    def __init__(self):
        """
        Initialize pipeline with shared dependencies
        Creates single instances of metrics, cache, and model manager
        """
        # Create shared instances (CRITICAL: fixes isolation bug)
        self.metrics = MetricsCollector()
        self.cache_manager = CacheManager()
        self.model_manager = ModelManager(metrics=self.metrics)
        
        # Initialize components with shared dependencies
        self.router = TaskRouter(
            cache_manager=self.cache_manager,
            metrics=self.metrics
        )
        
        self.comment_generator = CommentGenerator(
            model_manager=self.model_manager,
            cache_manager=self.cache_manager
        )
        
        self.email_generator = EmailGenerator(
            model_manager=self.model_manager,
            cache_manager=self.cache_manager
        )
        
        self.response_validator = ResponseValidator()
        
        logger.info("AI Processing Pipeline initialized with shared dependencies")
    
    def process_user_request(
        self, 
        user_input: str, 
        user_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Main processing method - handles complete AI workflow
        
        Args:
            user_input: Raw user message
            user_context: User information and context
            
        Returns:
            Complete processing result for backend to handle
        """
        start_time = datetime.utcnow()
        
        try:
            # Validate inputs
            if not user_input or not user_input.strip():
                return self._create_error_response(
                    "empty_input",
                    "Please provide a message",
                    user_input,
                    user_context
                )
            
            if not user_context:
                user_context = {}
                logger.warning("No user context provided, using empty dict")
            
            # Step 1: Route the request
            routing_result = self.router.route_request(user_input, user_context)
            
            logger.info(f"Request routed to: {routing_result['route_type']}")
            
            # Step 2: Process based on route type
            if not routing_result["requires_llm"]:
                # Backend shortcut - no AI processing needed
                return self._create_backend_response(routing_result)
            
            # Step 3: LLM Processing required
            processing_result = self._handle_llm_processing(routing_result)
            
            # Step 4: Validate response quality (if content was generated)
            if processing_result.get("success") and "generated_content" in processing_result:
                validation_result = self.response_validator.validate_response(
                    processing_result["generated_content"],
                    routing_result["route_type"]
                )
                processing_result["validation"] = validation_result
                
                # Override approval based on validation
                if not validation_result.get("approved_for_auto_send", False):
                    processing_result["requires_user_approval"] = True
                    if validation_result.get("flags"):
                        processing_result["approval_reason"] = validation_result["flags"]
            
            # Step 5: Calculate total processing time
            end_time = datetime.utcnow()
            processing_time = (end_time - start_time).total_seconds()
            
            # Step 6: Record pipeline metrics
            try:
                self._record_pipeline_metrics(
                    routing_result, 
                    processing_result,
                    processing_time
                )
            except Exception as e:
                logger.warning(f"Failed to record pipeline metrics: {e}")
            
            # Add final metadata
            processing_result["pipeline_metadata"] = {
                "total_processing_time": round(processing_time, 3),
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat(),
                "pipeline_version": "2.0"
            }
            
            return processing_result
            
        except Exception as e:
            logger.error(f"Pipeline processing error: {str(e)}", exc_info=True)
            return self._create_error_response(
                "pipeline_error",
                str(e),
                user_input,
                user_context
            )
    
    def _handle_llm_processing(self, routing_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle different types of LLM processing
        
        Args:
            routing_result: Routing decision from router
            
        Returns:
            Processing result dict
        """
        route_type = routing_result["route_type"]
        user_input = routing_result["user_input"]
        user_context = routing_result["user_context"]
        
        try:
            if route_type == "llm_rephrasing":
                return self._process_comment_generation(user_input, user_context, routing_result)
                
            elif route_type == "llm_email":
                return self._process_email_generation(user_input, user_context, routing_result)
                
            elif route_type == "llm_classification":
                return self._process_classification_fallback(user_input, user_context, routing_result)
                
            else:
                return {
                    "success": False,
                    "error": "unknown_llm_route",
                    "route_type": route_type,
                    "backend_action": "show_error_message"
                }
                
        except Exception as e:
            logger.error(f"LLM processing error for {route_type}: {str(e)}", exc_info=True)
            return {
                "success": False,
                "error": "llm_processing_failed",
                "error_message": str(e),
                "route_type": route_type,
                "backend_action": "show_error_message"
            }
    
    def _process_comment_generation(
        self, 
        user_input: str, 
        user_context: Dict[str, Any],
        routing_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Process professional comment generation
        
        Args:
            user_input: User's message
            user_context: User context
            routing_result: Routing decision
            
        Returns:
            Processing result for backend
        """
        # Extract additional context from routing
        extracted_entities = routing_result.get("classification_details", {}).get("extracted_entities", {})
        
        # Build context for comment generator
        comment_context = {
            "user_role": user_context.get("role"),
            "project_type": user_context.get("current_project_type"),
            "task_info": extracted_entities
        }
        
        # Generate professional comment
        generation_result = self.comment_generator.generate_professional_comment(
            user_input, 
            comment_context
        )
        
        if not generation_result["success"]:
            return generation_result
        
        # Format response for backend
        return {
            "success": True,
            "processing_type": "comment_generation",
            "route_type": "llm_rephrasing",
            "original_input": user_input,
            "generated_content": generation_result["professional_comment"],
            "requires_user_approval": generation_result.get("requires_approval", True),
            "quality_score": generation_result.get("quality_score", 0.0),
            "processing_metadata": {
                "word_count": generation_result.get("word_count", 0),
                "model_used": generation_result.get("processing_metadata", {}).get("model_used"),
                "tokens_used": generation_result.get("processing_metadata", {}).get("tokens_used"),
                "fallback_used": generation_result.get("fallback_used", False),
                "from_cache": generation_result.get("from_cache", False)
            },
            "backend_action": "show_comment_for_approval"
        }
    
    def _process_email_generation(
        self, 
        user_input: str, 
        user_context: Dict[str, Any],
        routing_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Process email generation
        
        Args:
            user_input: User's message
            user_context: User context
            routing_result: Routing decision
            
        Returns:
            Processing result for backend
        """
        # Generate email
        generation_result = self.email_generator.generate_email(user_input, user_context)
        
        if not generation_result["success"]:
            return generation_result
        
        # Format response for backend
        return {
            "success": True,
            "processing_type": "email_generation", 
            "route_type": "llm_email",
            "original_input": user_input,
            "generated_content": generation_result["generated_email"],
            "email_components": generation_result.get("email_components", {}),
            "requires_user_approval": True,  # Always require approval for emails
            "validation": generation_result.get("validation", {}),
            "processing_metadata": {
                **generation_result.get("processing_metadata", {}),
                "from_cache": generation_result.get("from_cache", False)
            },
            "backend_action": "show_email_for_approval"
        }
    
    def _process_classification_fallback(
        self, 
        user_input: str, 
        user_context: Dict[str, Any],
        routing_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Handle ambiguous cases that need LLM classification
        
        Args:
            user_input: User's message
            user_context: User context
            routing_result: Routing decision
            
        Returns:
            Processing result for backend
        """
        # Use classification prompt to understand user intent
        from ..prompts.system_prompts import SystemPrompts
        
        classification_result = self.model_manager.generate_completion_with_cost_check(
            system_prompt=SystemPrompts.CLASSIFICATION_HELPER,
            user_message=user_input,
            model_type="classification",  # Use faster model for classification
            temperature=0.1
        )
        
        if not classification_result["success"]:
            return {
                "success": False,
                "error": "classification_failed",
                "original_input": user_input,
                "backend_action": "request_clarification"
            }
        
        # Parse classification result
        classification_text = classification_result["content"]
        
        # Try to extract JSON (LLM might wrap in markdown)
        import json
        import re
        
        try:
            # Try direct JSON parse
            parsed = json.loads(classification_text)
        except json.JSONDecodeError:
            # Try to extract JSON from markdown
            json_match = re.search(r'```json\s*(\{.*?\})\s*```', classification_text, re.DOTALL)
            if json_match:
                try:
                    parsed = json.loads(json_match.group(1))
                except:
                    parsed = {"intent": "unclear", "confidence": 0.5}
            else:
                parsed = {"intent": "unclear", "confidence": 0.5}
        
        # Format response
        return {
            "success": True,
            "processing_type": "classification_help",
            "route_type": "llm_classification", 
            "original_input": user_input,
            "classification_result": parsed,
            "generated_content": parsed.get("user_friendly_response", "I'm not sure what you want to do. Could you please clarify?"),
            "requires_user_approval": False,
            "backend_action": "show_clarification_request",
            "processing_metadata": classification_result.get("usage", {})
        }
    
    def _create_backend_response(self, routing_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create response for backend shortcuts (no LLM needed)
        
        Args:
            routing_result: Routing decision
            
        Returns:
            Backend response dict
        """
        route_type = routing_result["route_type"]
        
        if route_type == "backend_completion":
            return {
                "success": True,
                "processing_type": "backend_shortcut",
                "route_type": route_type,
                "original_input": routing_result["user_input"],
                "requires_llm": False,
                "backend_action": "mark_task_complete",
                "extracted_entities": routing_result.get("classification_details", {}).get("extracted_entities", {}),
                "confidence": routing_result["confidence"]
            }
            
        elif route_type == "backend_productivity":
            return {
                "success": True,
                "processing_type": "backend_calculation",
                "route_type": route_type, 
                "original_input": routing_result["user_input"],
                "requires_llm": False,
                "backend_action": "calculate_productivity_stats",
                "confidence": routing_result["confidence"]
            }
        
        return {
            "success": False,
            "error": "unknown_backend_route",
            "route_type": route_type,
            "backend_action": "show_error_message"
        }
    
    def _record_pipeline_metrics(
        self, 
        routing_result: Dict, 
        processing_result: Dict,
        processing_time: float
    ):
        """
        Record metrics for monitoring
        
        Args:
            routing_result: Routing decision
            processing_result: Processing result
            processing_time: Total time in seconds
        """
        self.metrics.record_pipeline_execution(
            route_type=routing_result["route_type"],
            requires_llm=routing_result["requires_llm"],
            success=processing_result.get("success", False),
            processing_time=processing_time,
            user_id=routing_result.get("user_context", {}).get("user_id", "unknown")
        )
    
    def _create_error_response(
        self,
        error_type: str,
        error_message: str,
        user_input: str,
        user_context: Dict
    ) -> Dict[str, Any]:
        """
        Create error response when pipeline fails
        
        Args:
            error_type: Type of error
            error_message: Error message
            user_input: Original input
            user_context: User context
            
        Returns:
            Error response dict
        """
        return {
            "success": False,
            "error": error_type,
            "error_message": error_message,
            "original_input": user_input,
            "user_context": user_context,
            "backend_action": "show_error_message",
            "fallback_message": "I'm having trouble processing your request. Please try again or contact support."
        }
    
    def get_pipeline_stats(self) -> Dict[str, Any]:
        """
        Get pipeline statistics for monitoring
        
        Returns:
            Pipeline statistics
        """
        try:
            metrics_stats = self.metrics.get_stats()
            cache_stats = self.cache_manager.get_stats()
            
            return {
                "metrics": metrics_stats,
                "cache": cache_stats,
                "config": {
                    "environment": config.environment,
                    "cache_enabled": config.cache_enabled,
                    "max_daily_cost": config.max_daily_cost_usd
                }
            }
        except Exception as e:
            logger.error(f"Error getting pipeline stats: {e}")
            return {"error": str(e)}