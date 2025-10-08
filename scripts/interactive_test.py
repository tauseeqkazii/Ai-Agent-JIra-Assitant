"""
Interactive AI Testing Script - Azure OpenAI Compatible
Tests all AI capabilities with realistic scenarios
"""
import sys
import os
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Verify Azure configuration
print("\n🔍 Checking Azure OpenAI configuration...")
api_key = os.getenv("OPENAI_API_KEY")
api_base = os.getenv("OPENAI_API_BASE_URL")
api_version = os.getenv("AZURE_API_VERSION", "2023-07-01-preview")

if not api_key or not api_base:
    print("❌ Missing Azure OpenAI configuration!")
    print("   Please set OPENAI_API_KEY and OPENAI_API_BASE_URL in .env file")
    sys.exit(1)

print(f"✅ API Key: {api_key[:10]}...")
print(f"✅ API Base: {api_base}")
print(f"✅ API Version: {api_version}")
print()

from src.ai_engine.main import process_message
from src.ai_engine.utils.context_builder import ContextBuilder
from typing import Dict, Any
import json


# ============================================================================
# Mock User Data (matching your MongoDB structure)
# ============================================================================

MOCK_USER_DATA = {
    "userId": "f8187039-fb65-4885-9509-8aa2910e2581",
    "platform": "jira",
    "accessToken": "eyJraWQiOiJhdXRoLmF0bGFzc2lhbi5jb20...",
    "profileData": {
        "accountId": "712020:65b80284-4ce7-4a96-b81c-2eacc1a3f85a",
        "emailAddress": "saksham@munoai.com",
        "displayName": "Saksham Soni",
        "active": True,
        "timeZone": "Asia/Calcutta",
    },
    "expiresAt": "2025-12-31T23:59:59.000Z"  # Future date for testing
}


# ============================================================================
# Test Scenarios
# ============================================================================

TEST_SCENARIOS = {
    "1": {
        "name": "Simple Task Completion",
        "input": "done",
        "description": "Tests backend shortcut routing"
    },
    "2": {
        "name": "Complex Task Update",
        "input": "I fixed the login bug and tested it on staging environment. Ready for production deployment.",
        "description": "Tests comment generation and quality validation"
    },
    "3": {
        "name": "Sick Leave Email",
        "input": "write a sick leave email for tomorrow",
        "description": "Tests email generation",
        "context_override": {"manager_name": "John Smith"}
    },
    "4": {
        "name": "Custom Email Request",
        "input": "write an email to my manager requesting approval for the new feature implementation",
        "description": "Tests flexible email generation",
        "context_override": {"manager_name": "Jane Doe"}
    },
    "5": {
        "name": "Productivity Query",
        "input": "how productive was I this week?",
        "description": "Tests productivity routing (backend calculation needed)"
    },
    "6": {
        "name": "Out of Scope Request",
        "input": "what's the weather today?",
        "description": "Tests scope checking - should reject gracefully"
    },
    "7": {
        "name": "Ambiguous Input",
        "input": "hello",
        "description": "Tests handling of conversational/unclear input"
    },
    "8": {
        "name": "Multiple Task IDs",
        "input": "task JIRA-123 and BUG-456 are both completed",
        "description": "Tests entity extraction"
    },
    "9": {
        "name": "Azure Model Test",
        "input": "test azure connection",
        "description": "Tests Azure OpenAI API connectivity"
    },
    "10": {
        "name": "Long Response Test",
        "input": "generate a detailed project plan",
        "description": "Tests Azure token limits and streaming"
    }
}


# ============================================================================
# Interactive Functions
# ============================================================================

def build_context(context_override: Dict[str, Any] = None) -> Dict[str, Any]:
    """Build AI context from mock user data with Azure settings"""
    context = ContextBuilder.build_from_jira_user(
        MOCK_USER_DATA,
        additional_context=context_override or {}
    )
    
    # Add Azure-specific context
    context["provider"] = "azure"
    context["model_settings"] = {
        "api_type": "azure",
        "api_version": api_version,
        "deployment_id": os.getenv("AZURE_DEPLOYMENT_NAME", "gpt-35-turbo")
    }
    
    return context


def format_result(result: Dict[str, Any]) -> str:
    """Format AI result for display with Azure details"""
    lines = []
    lines.append("\n" + "="*70)
    
    # Add Azure-specific information
    if "api_provider" in result:
        lines.append(f"Provider: {result['api_provider']}")
    if "model_used" in result:
        lines.append(f"Model/Deployment: {result['model_used']}")
    
    # Status
    status = "✅ SUCCESS" if result.get("success") else "❌ FAILED"
    lines.append(f"Status: {status}")
    
    # Route type
    if "route_type" in result:
        lines.append(f"Route: {result['route_type']}")
    
    # Backend action
    if "backend_action" in result:
        lines.append(f"Backend Action: {result['backend_action']}")
    
    lines.append("-" * 70)
    
    # Generated content or message
    if "generated_content" in result:
        lines.append("\n📝 Generated Content:")
        lines.append(result["generated_content"])
    elif "message" in result:
        lines.append(f"\n💬 Message: {result['message']}")
    
    # Quality metrics
    if "quality_score" in result:
        lines.append(f"\n📊 Quality Score: {result['quality_score']:.2f}")
    
    if "requires_approval" in result:
        approval = "YES ⚠️" if result["requires_approval"] else "NO ✓"
        lines.append(f"Requires Approval: {approval}")
    
    # Metadata
    if "processing_metadata" in result:
        meta = result["processing_metadata"]
        if "tokens_used" in meta:
            lines.append(f"\n🔢 Tokens Used: {meta['tokens_used']}")
        if "from_cache" in meta:
            cache = "YES" if meta["from_cache"] else "NO"
            lines.append(f"From Cache: {cache}")
        # Add Azure-specific metadata
        if "api_version" in meta:
            lines.append(f"Azure API Version: {meta['api_version']}")
        if "deployment" in meta:
            lines.append(f"Azure Deployment: {meta['deployment']}")
    
    # Error details
    if not result.get("success"):
        if "error" in result:
            lines.append(f"\n❗ Error Type: {result['error']}")
        if "error_message" in result:
            lines.append(f"Error Message: {result['error_message']}")
    
    lines.append("="*70 + "\n")
    return "\n".join(lines)


def run_test_scenario(scenario_key: str):
    """Run a predefined test scenario"""
    scenario = TEST_SCENARIOS.get(scenario_key)
    if not scenario:
        print(f"❌ Unknown scenario: {scenario_key}")
        return
    
    print(f"\n🧪 Running Test: {scenario['name']}")
    print(f"📝 Description: {scenario['description']}")
    print(f"💬 Input: \"{scenario['input']}\"")
    
    # Build context
    context = build_context(scenario.get("context_override"))
    
    # Process
    result = process_message(scenario["input"], context)
    
    # Display result
    print(format_result(result))


def interactive_mode():
    """Run interactive testing mode with Azure support"""
    print("\n" + "="*70)
    print("🤖 Jira AI Assistant - Interactive Testing Mode (Azure OpenAI)")
    print("="*70)
    print("\nCommands:")
    print("  • Type your request normally")
    print("  • 'test <number>' - Run predefined test (e.g., 'test 1')")
    print("  • 'tests' - Show all test scenarios")
    print("  • 'context' - View current context")
    print("  • 'azure' - View Azure configuration")
    print("  • 'exit' - Quit")
    print("="*70 + "\n")
    
    while True:
        try:
            user_input = input("\n💬 Your request: ").strip()
            
            if not user_input:
                continue
            
            # Handle special commands
            if user_input.lower() == "exit":
                print("\n👋 Goodbye!")
                break
            
            elif user_input.lower() == "azure":
                print("\n📊 Azure OpenAI Configuration:")
                print(f"  API Base: {api_base}")
                print(f"  API Version: {api_version}")
                print(f"  Deployment: {os.getenv('AZURE_DEPLOYMENT_NAME', 'gpt-35-turbo')}")
                continue
            
            elif user_input.lower() == "tests":
                print("\n📋 Available Test Scenarios:")
                for key, scenario in TEST_SCENARIOS.items():
                    print(f"  {key}. {scenario['name']}: {scenario['description']}")
                continue
            
            elif user_input.lower().startswith("test "):
                scenario_key = user_input.split()[1]
                run_test_scenario(scenario_key)
                continue
            
            elif user_input.lower() == "context":
                context = build_context()
                print("\n📊 Current Context:")
                print(json.dumps(context, indent=2))
                continue
            
            # Normal processing
            print("\n⏳ Processing...")
            
            # Ask for additional context if needed
            context_override = {}
            
            if "email" in user_input.lower():
                manager = input("  Manager's name (or press Enter to skip): ").strip()
                if manager:
                    context_override["manager_name"] = manager
            
            # Build context and process
            context = build_context(context_override)
            result = process_message(user_input, context)
            
            # Display result
            print(format_result(result))
            
        except KeyboardInterrupt:
            print("\n\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"\n❌ Error: {e}")
            import traceback
            traceback.print_exc()


# ============================================================================
# Main
# ============================================================================

if __name__ == "__main__":
    print("\n🚀 Starting Jira AI Assistant Testing (Azure OpenAI)...")
    
    # Check if specific test requested
    if len(sys.argv) > 1:
        scenario_key = sys.argv[1]
        run_test_scenario(scenario_key)
    else:
        interactive_mode()