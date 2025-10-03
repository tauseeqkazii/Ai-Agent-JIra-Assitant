import pytest
from src.ai_engine.classification.intent_classifier import IntentClassifier, RouteType

class TestIntentClassifier:
    """Test intent classification accuracy"""
    
    @pytest.fixture
    def classifier(self):
        return IntentClassifier()
    
    def test_simple_completion_detection(self, classifier):
        """Test detection of simple completion statements"""
        test_cases = [
            "done",
            "task is completed", 
            "finished",
            "mark as complete",
            "  done  "  # with whitespace
        ]
        
        for test_input in test_cases:
            result = classifier.classify(test_input)
            assert result.route_type == RouteType.BACKEND_COMPLETION
            assert result.confidence >= 0.9
    
    def test_productivity_query_detection(self, classifier):
        """Test detection of productivity queries"""
        test_cases = [
            "how productive was I this week?",
            "my productivity stats",
            "how many tasks completed",
            "weekly report"
        ]
        
        for test_input in test_cases:
            result = classifier.classify(test_input)
            assert result.route_type == RouteType.BACKEND_PRODUCTIVITY
            assert result.confidence >= 0.8
    
    def test_email_request_detection(self, classifier):
        """Test detection of email requests"""
        test_cases = [
            "write an email",
            "send email to my manager", 
            "compose sick leave email",
            "email for vacation request"
        ]
        
        for test_input in test_cases:
            result = classifier.classify(test_input)
            assert result.route_type == RouteType.LLM_EMAIL
            assert result.confidence >= 0.8
    
    def test_complex_update_detection(self, classifier):
        """Test detection of complex updates requiring rephrasing"""
        test_cases = [
            "I fixed the login bug and tested it on staging environment",
            "Working on the API implementation, waiting for review",
            "Implemented the feature but blocked by database issues"
        ]
        
        for test_input in test_cases:
            result = classifier.classify(test_input)
            assert result.route_type == RouteType.LLM_REPHRASING
            assert result.confidence >= 0.7

if __name__ == "__main__":
    pytest.main([__file__])
    