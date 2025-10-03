"""
Standalone testing script to verify AI Engine works without backend
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add src to path
sys.path.append('src')

def test_basic_functionality():
    """Test basic AI engine functionality"""
    print("🧪 Testing AI Engine Standalone...")
    
    try:
        # Import AI engine
        from ai_engine.main import ai_assistant, process_message
        
        print("✅ AI Engine imported successfully")
        
        # Test configuration validation
        config_result = ai_assistant.validate_configuration()
        print(f"📋 Configuration: {'✅ Valid' if config_result['valid'] else '❌ Invalid'}")
        
        if not config_result['valid']:
            print("Issues:", config_result.get('issues', []))
            return False
        
        # Mock user context
        user_context = {
            "user_id": "test_user_123",
            "user_name": "Test User",
            "role": "developer",
            "session_id": "test_session"
        }
        
        # Test cases
        test_cases = [
            {
                "name": "Simple Completion (Backend Shortcut)",
                "input": "done",
                "expected_route": "backend_completion",
                "expected_llm": False
            },
            {
                "name": "Productivity Query (Backend Shortcut)", 
                "input": "how productive was I this week?",
                "expected_route": "backend_productivity",
                "expected_llm": False
            },
            {
                "name": "Complex Update (LLM Processing)",
                "input": "I fixed the login bug and tested it on staging environment",
                "expected_route": "llm_rephrasing",
                "expected_llm": True
            },
            {
                "name": "Email Request (LLM Processing)",
                "input": "write an email for sick leave tomorrow",
                "expected_route": "llm_email", 
                "expected_llm": True
            }
        ]
        
        print("\n🔍 Running test cases...")
        
        for i, test_case in enumerate(test_cases, 1):
            print(f"\n--- Test {i}: {test_case['name']} ---")
            print(f"Input: '{test_case['input']}'")
            
            try:
                result = process_message(test_case['input'], user_context)
                
                print(f"Route: {result.get('route_type', 'unknown')}")
                print(f"Requires LLM: {result.get('requires_llm', 'unknown')}")
                print(f"Success: {result.get('success', False)}")
                
                if result.get('backend_action'):
                    print(f"Backend Action: {result['backend_action']}")
                
                if result.get('generated_content'):
                    print(f"Generated Content: {result['generated_content'][:100]}...")
                
                # Validate expectations
                route_match = result.get('route_type') == test_case['expected_route']
                llm_match = result.get('requires_llm') == test_case['expected_llm']
                
                if route_match and llm_match:
                    print("✅ Test passed")
                else:
                    print("❌ Test failed - routing mismatch")
                
            except Exception as e:
                print(f"❌ Test failed with error: {str(e)}")
        
        # Test health and metrics
        print("\n🏥 Testing health and metrics...")
        health = ai_assistant.get_health_status()
        print(f"Health Status: {'✅ Healthy' if health.get('healthy') else '❌ Unhealthy'}")
        
        metrics = ai_assistant.get_performance_metrics()
        print(f"Metrics Available: {'✅ Yes' if 'requests' in metrics else '❌ No'}")
        
        print("\n🎉 Standalone testing completed!")
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("Make sure all dependencies are installed: pip install -r requirements.txt")
        return False
        
    except Exception as e:
        print(f"❌ Test failed: {str(e)}")
        return False

if __name__ == "__main__":
    # Set environment variables for testing
    if not os.getenv("OPENAI_API_KEY"):
        print("❌ Please set OPENAI_API_KEY environment variable")
        print("Create .env file with: OPENAI_API_KEY=your_key_here")
        sys.exit(1)
    
    success = test_basic_functionality()
    sys.exit(0 if success else 1)