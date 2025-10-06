import pytest
import unittest.mock as mock
from src.ai_engine.core.pipeline import AIProcessingPipeline
from src.ai_engine.classification.intent_classifier import RouteType
from src.ai_engine.core.config import config
from src.ai_engine.models.model_manager import ModelManager
class TestAIPipeline:
    """Comprehensive tests for AI processing pipeline"""
    
    @pytest.fixture
    def pipeline(self):
        """Create pipeline instance for testing"""
        return AIProcessingPipeline()
    
    @pytest.fixture
    def mock_user_context(self):
        """Mock user context for testing"""
        return {
            "user_id": "test_user_123",
            "user_name": "Test User",
            "role": "developer",
            "session_id": "session_456"
        }
    
    def test_backend_completion_routing(self, pipeline, mock_user_context):
        """Test simple completion routing (backend shortcut)"""
        user_input = "done"
        
        result = pipeline.process_user_request(user_input, mock_user_context)
        
        assert result["success"] == True
        assert result["route_type"] == "backend_completion"
        assert result["requires_llm"] == False
        assert result["backend_action"] == "mark_task_complete"
    
    def test_productivity_query_routing(self, pipeline, mock_user_context):
        """Test productivity query routing"""
        user_input = "how productive was I this week?"
        
        result = pipeline.process_user_request(user_input, mock_user_context)
        
        assert result["success"] == True
        assert result["route_type"] == "backend_productivity"
        assert result["requires_llm"] == False
        assert result["backend_action"] == "calculate_productivity_stats"
    
    @mock.patch('src.ai_engine.models.model_manager.ModelManager.generate_completion')
    def test_comment_generation_success(self, mock_llm, pipeline, mock_user_context):
        """Test successful comment generation"""
        user_input = "I fixed the button alignment issue and tested it on staging"
        
        # Mock LLM response
        mock_llm.return_value = {
            "success": True,
            "content": "Resolved button alignment issue. Testing completed on staging environment.",
            "usage": {"total_tokens": 50},
            "model_used": "gpt-4-turbo-preview"
        }
        
        result = pipeline.process_user_request(user_input, mock_user_context)
        
        assert result["success"] == True
        assert result["processing_type"] == "comment_generation"
        assert "Resolved button alignment issue" in result["generated_content"]
        assert result["requires_user_approval"] == True
        assert result["backend_action"] == "show_comment_for_approval"
    
    @mock.patch('src.ai_engine.models.model_manager.ModelManager.generate_completion')
    def test_email_generation_success(self, mock_llm, pipeline, mock_user_context):
        """Test successful email generation"""
        user_input = "write an email for sick leave tomorrow"
        
        # Mock LLM response
        mock_llm.return_value = {
            "success": True,
            "content": "Subject: Sick Leave Request\n\nDear Manager,\n\nI am writing to inform you that I will not be able to come to work tomorrow due to illness.\n\nBest regards,\nTest User",
            "usage": {"total_tokens": 75},
            "model_used": "gpt-4-turbo-preview"
        }
        
        result = pipeline.process_user_request(user_input, mock_user_context)
        
        assert result["success"] == True
        assert result["processing_type"] == "email_generation"
        assert "Subject: Sick Leave Request" in result["generated_content"]
        assert result["requires_user_approval"] == True
        assert result["backend_action"] == "show_email_for_approval"
    
    @mock.patch('src.ai_engine.models.model_manager.ModelManager.generate_completion')
    def test_llm_failure_handling(self, mock_llm, pipeline, mock_user_context):
        """Test handling of LLM failures"""
        user_input = "I'm working on the complex feature implementation"
        
        # Mock LLM failure
        mock_llm.return_value = {
            "success": False,
            "error": "api_error",
            "error_message": "OpenAI API rate limit exceeded"
        }
        
        result = pipeline.process_user_request(user_input, mock_user_context)
        
        assert result["success"] == False
        assert "error" in result
    
    def test_invalid_input_handling(self, pipeline, mock_user_context):
        """Test handling of invalid/empty input"""
        user_input = ""
        
        result = pipeline.process_user_request(user_input, mock_user_context)
        
        # Should handle gracefully
        assert "success" in result
    
    @mock.patch('src.ai_engine.generation.comment_generator.CommentGenerator.generate_professional_comment')
    def test_cache_hit(self, mock_generator, pipeline, mock_user_context):
        user_input = "I fixed the API bug"  # LLM route, not backend
        
        # First call
        mock_generator.return_value = {
            "success": True,
            "professional_comment": "Resolved API bug.",
            "from_cache": False
        }
        result1 = pipeline.process_user_request(user_input, mock_user_context)
        
        # Second call - should use cache
        result2 = pipeline.process_user_request(user_input, mock_user_context)
        
        # Generator should only be called once due to caching
        assert mock_generator.call_count == 1

if __name__ == "__main__":
    pytest.main([__file__])