from typing import Dict, Any, Optional
import logging
from .router import TaskRouter
from ..generation.comment_generator import CommentGenerator
from ..generation.email_generator import EmailGenerator
from ..generation.response_validator import ResponseValidator
from ..models.model_manager import ModelManager
from ..utils.metrics import MetricsCollector

logger = logging.getLogger(__name__)

class AIProcessingPipeline:
    """
    Main AI pipeline that orchestrates the entire AI processing flow
    Routes requests and handles LLM processing
    """
    
    def __init__(self):
        # Initialize all AI components
        self.model_manager = ModelManager()
        self.router = TaskRouter()
        self.comment_generator = CommentGenerator(self.model_manager)
        self.email_generator = EmailGenerator(self.model_manager)
        self.response_validator = ResponseValidator()
        self.metrics = MetricsCollector()
        
        logger.info("AI Processing Pipeline initialized")
    
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
        try:
            # Step 1: Route the request
            routing_result = self.router.route_request(user_input, user_context)
            
            logger.info(f"Request routed to: {routing_result['route_type']}")
            
            # Step 2: Process based on route type
            if not routing_result["requires_llm"]:
                # Backend shortcut - no AI processing needed
                return self._create_backend_response(routing_result)
            
            # Step 3: LLM Processing required
            processing_result = self._handle_llm_processing(routing_result)
            
            # Step 4: Validate response quality
            if processing_result.get("success") and "generated_content" in processing_result:
                validation_result = self.response_validator.validate_response(
                    processing_result["generated_content"],
                    routing_result["route_type"]
                )
                processing_result["validation"] = validation_result
            
            # Step 5: Record metrics
            self._record_pipeline_metrics(routing_result, processing_result)
            
            return processing_result
            
        except Exception as e:
            logger.error(f"Pipeline processing error: {str(e)}")
            return self._create_error_response(user_input, user_context, str(e))
    
    def _handle_llm_processing(self, routing_result: Dict[str, Any]) -> Dict[str, Any]:
        """Handle different types of LLM processing"""
        
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
                    "route_type": route_type
                }
                
        except Exception as e:
            logger.error(f"LLM processing error for {route_type}: {str(e)}")
            return {
                "success": False,
                "error": "llm_processing_failed",
                "error_message": str(e),
                "route_type": route_type
            }
    
    def _process_comment_generation(
        self, 
        user_input: str, 
        user_context: Dict[str, Any],
        routing_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Process professional comment generation"""
        
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
            "requires_llm": True,
            "original_input": user_input,
            "generated_content": generation_result["professional_comment"],
            "requires_user_approval": generation_result.get("requires_approval", True),
            "quality_score": generation_result.get("quality_score", 0.0),
            "processing_metadata": {
                "word_count": generation_result.get("word_count", 0),
                "model_used": generation_result.get("processing_metadata", {}).get("model_used"),
                "tokens_used": generation_result.get("processing_metadata", {}).get("tokens_used"),
                "fallback_used": generation_result.get("fallback_used", False)
            },
            "backend_action": "show_comment_for_approval"  # Tell backend what to do
        }
    
    def _process_email_generation(
        self, 
        user_input: str, 
        user_context: Dict[str, Any],
        routing_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Process email generation"""
        
        # Generate email
        generation_result = self.email_generator.generate_email(user_input, user_context)
        
        if not generation_result["success"]:
            return generation_result
        
        # Format response for backend
        return {
            "success": True,
            "processing_type": "email_generation", 
            "route_type": "llm_email",
            "requires_llm": True,
            "original_input": user_input,
            "generated_content": generation_result["generated_email"],
            "email_components": generation_result.get("email_components", {}),
            "requires_user_approval": True,  # Always require approval for emails
            "processing_metadata": generation_result.get("processing_metadata", {}),
            "backend_action": "show_email_for_approval"  # Tell backend what to do
        }
    
    def _process_classification_fallback(
        self, 
        user_input: str, 
        user_context: Dict[str, Any],
        routing_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle ambiguous cases that need LLM classification"""
        
        # Use classification prompt to understand user intent
        classification_result = self.model_manager.generate_completion(
            system_prompt=self.comment_generator.prompts.CLASSIFICATION_HELPER,
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
        
        # Parse classification result and suggest action
        return {
            "success": True,
            "processing_type": "classification_help",
            "route_type": "llm_classification", 
            "requires_llm": True,
            "original_input": user_input,
            "classification_result": classification_result["content"],
            "generated_content": f"I understand you want to: {classification_result['content']}. Could you please clarify?",
            "requires_user_approval": False,
            "backend_action": "show_clarification_request",
            "processing_metadata": classification_result.get("usage", {})
        }
    
    def _create_backend_response(self, routing_result: Dict[str, Any]) -> Dict[str, Any]:
        """Create response for backend shortcuts (no LLM needed)"""
        
        route_type = routing_result["route_type"]
        
        if route_type == "backend_completion":
            return {
                "success": True,
                "processing_type": "backend_shortcut",
                "route_type": route_type,
                "original_input": routing_result["user_input"],
                "requires_llm": False,
                "backend_action": "mark_task_complete",  # Direct instruction for backend
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
                "backend_action": "calculate_productivity_stats",  # Direct instruction for backend
                "confidence": routing_result["confidence"]
            }
        
        return {
            "success": False,
            "error": "unknown_backend_route",
            "route_type": route_type
        }
    
    def _record_pipeline_metrics(self, routing_result: Dict, processing_result: Dict):
        """Record metrics for monitoring"""
        
        self.metrics.record_pipeline_execution(
            route_type=routing_result["route_type"],
            requires_llm=routing_result["requires_llm"],
            success=processing_result.get("success", False),
            processing_time=None,  # Backend can add timing
            user_id=routing_result.get("user_context", {}).get("user_id")
        )
    
    def _create_error_response(self, user_input: str, user_context: Dict, error_msg: str) -> Dict[str, Any]:
        """Create error response when pipeline fails"""
        
        return {
            "success": False,
            "error": "pipeline_error",
            "error_message": error_msg,
            "original_input": user_input,
            "user_context": user_context,
            "backend_action": "show_error_message",
            "fallback_message": "I'm having trouble processing your request. Please try again or contact support."
        }