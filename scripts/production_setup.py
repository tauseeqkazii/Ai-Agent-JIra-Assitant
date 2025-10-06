"""
Production setup and validation script
"""

import os
import sys
import subprocess
from pathlib import Path

def validate_environment():
    """Validate production environment"""
    print("🔍 Validating production environment...")
    
    issues = []
    
    # Check Python version
    if sys.version_info < (3, 9):
        issues.append("Python 3.9+ required")
    
    # Check required environment variables
    required_vars = [
        "OPENAI_API_KEY",
        "ENVIRONMENT"
    ]
    
    for var in required_vars:
        if not os.getenv(var):
            issues.append(f"Missing environment variable: {var}")
    
    # Check OpenAI API key format
    api_key = os.getenv("OPENAI_API_KEY", "")
    if api_key and not api_key.startswith("sk-"):
        issues.append("Invalid OpenAI API key format")
    
    if issues:
        print("❌ Environment validation failed:")
        for issue in issues:
            print(f"  - {issue}")
        return False
    
    print("✅ Environment validation passed")
    return True

def install_dependencies():
    """Install production dependencies"""
    print("📦 Installing dependencies...")
    
    try:
        subprocess.run([
            sys.executable, "-m", "pip", "install", "-r", "requirements.txt"
        ], check=True, capture_output=True)
        
        print("✅ Dependencies installed successfully")
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install dependencies: {e}")
        return False

def run_tests():
    """Run test suite"""
    print("🧪 Running test suite...")
    
    try:
        result = subprocess.run([
            sys.executable, "-m", "pytest", "tests/", "-v"
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ All tests passed")
            return True
        else:
            print("❌ Some tests failed:")
            print(result.stdout)
            print(result.stderr)
            return False
            
    except Exception as e:
        print(f"❌ Failed to run tests: {e}")
        return False

def validate_ai_configuration():
    """Validate AI configuration"""
    print("🤖 Validating AI configuration...")
    
    try:
        # Import after dependencies are installed
        from src.ai_engine.main import ai_assistant
        
        validation_result = ai_assistant.validate_configuration()
        
        if validation_result["valid"]:
            print("✅ AI configuration valid")
            
            if validation_result.get("warnings"):
                print("⚠️  Configuration warnings:")
                for warning in validation_result["warnings"]:
                    print(f"  - {warning}")
            
            return True
        else:
            print("❌ AI configuration issues:")
            for issue in validation_result.get("issues", []):
                print(f"  - {issue}")
            return False
            
    except Exception as e:
        print(f"❌ Failed to validate AI configuration: {e}")
        return False

def main():
    """Main setup function"""
    print("🚀 Setting up Jira AI Assistant for production...")
    
    steps = [
        ("Validate Environment", validate_environment),
        ("Install Dependencies", install_dependencies),
        ("Run Tests", run_tests),
        ("Validate AI Configuration", validate_ai_configuration)
    ]
    
    for step_name, step_func in steps:
        print(f"\n--- {step_name} ---")
        if not step_func():
            print(f"\n❌ Setup failed at step: {step_name}")
            sys.exit(1)
    
    print("\n🎉 Production setup completed successfully!")
    print("\n📋 Next steps for backend team:")
    print("1. Import: from src.ai_engine.main import process_message")
    print("2. Set up monitoring endpoint using get_health() and get_metrics()")
    print("3. Configure error alerting based on circuit breaker states")
    print("4. Set up user approval workflows for generated content")

if __name__ == "__main__":
    main()