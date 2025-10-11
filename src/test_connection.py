import requests
import json
import logging
import sys
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_backend_connection():
    """Test if backend API is responding"""
    BASE_URL = "http://localhost:8000"
    logger.info(f"Testing backend connection to {BASE_URL}")
    
    # 1. Test health endpoint
    try:
        logger.info("Testing health endpoint...")
        health_response = requests.get(f"{BASE_URL}/api/v1/health")
        print("\n1. Health Check:")
        print(f"Status: {health_response.status_code}")
        print(f"Response: {health_response.json() if health_response.ok else health_response.text}")
    except requests.ConnectionError:
        logger.error(f"Could not connect to {BASE_URL}. Is the server running?")
        return False
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return False

    # 2. Test message processing endpoint
    try:
        logger.info("Testing message processing endpoint...")
        headers = {
            "Authorization": "Bearer your-secret-token-here",
            "Content-Type": "application/json"
        }
        
        test_data = {
            "user_input": "test connection",
            "user_context": {
                "user_id": "test_user",
                "user_name": "Test User",
                "role": "Tester",
                "timestamp": datetime.utcnow().isoformat()
            }
        }
        
        process_response = requests.post(
            f"{BASE_URL}/api/v1/process",
            headers=headers,
            json=test_data
        )
        
        print("\n2. Message Processing:")
        print(f"Status: {process_response.status_code}")
        print(f"Response: {process_response.json() if process_response.ok else process_response.text}")
        
        return process_response.ok
    
    except requests.ConnectionError:
        logger.error("Could not connect to message processing endpoint")
        return False
    except Exception as e:
        logger.error(f"Message processing test failed: {str(e)}")
        return False

def main():
    """Main function to run connection tests"""
    logger.info("Starting backend connection tests...")
    
    # Ensure backend is running
    if not test_backend_connection():
        logger.error("❌ Backend connection tests failed")
        sys.exit(1)
    
    logger.info("✅ Backend connection tests completed successfully")

if __name__ == "__main__":
    main()