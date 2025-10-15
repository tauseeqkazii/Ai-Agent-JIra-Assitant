"""
FastAPI Service for AI Engine
Bridge between Node.js backend and Python AI engine
"""
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional
import logging
from datetime import datetime
import sys
import os

# Add src to path so we can import ai_engine
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.ai_engine.main import (
    process_message,
    get_health,
    get_metrics,
    get_costs,
    ai_assistant
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastAPI
app = FastAPI(
    title="Jira AI Assistant API",
    description="AI-powered task management and email generation",
    version="2.0.0"
)

# CORS - Allow Node.js backend to access this
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # Node.js backend
        "http://localhost:5173",  # React frontend (Vite default)
        "http://localhost:5000",  # Alternative ports
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================================
# Request/Response Models
# ============================================================================

class UserContext(BaseModel):
    """User context from Node.js backend"""
    user_id: str
    user_name: Optional[str] = None
    email_address: Optional[str] = None
    manager_name: Optional[str] = None
    jira_connected: bool = False
    jira_account_id: Optional[str] = None
    jira_access_token: Optional[str] = None
    role: Optional[str] = None
    department: Optional[str] = None
    current_task: Optional[Dict[str, Any]] = None


class ProcessRequest(BaseModel):
    """Request to process user message"""
    user_input: str = Field(..., min_length=1, max_length=5000)
    user_context: UserContext


# ============================================================================
# Middleware
# ============================================================================

@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all requests"""
    start_time = datetime.utcnow()
    logger.info(f"📨 {request.method} {request.url.path}")
    
    response = await call_next(request)
    
    duration = (datetime.utcnow() - start_time).total_seconds()
    logger.info(f"✅ {request.method} {request.url.path} - {response.status_code} - {duration:.3f}s")
    
    return response


# ============================================================================
# API Endpoints
# ============================================================================

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "Jira AI Assistant",
        "version": "2.0.0",
        "status": "running",
        "provider": "Azure OpenAI",
        "endpoints": {
            "process": "POST /api/v1/process",
            "health": "GET /api/v1/health",
            "metrics": "GET /api/v1/metrics",
            "costs": "GET /api/v1/costs"
        }
    }


@app.post("/api/v1/process")
async def process_user_message(request: ProcessRequest):
    """
    Main endpoint: Process user message through AI engine
    Called by Node.js backend
    """
    try:
        logger.info(f"Processing message from user: {request.user_context.user_id}")
        logger.debug(f"Input: {request.user_input[:100]}...")
        
        # Convert Pydantic model to dict
        user_context_dict = request.user_context.dict()
        
        # Process with AI engine
        result = process_message(
            user_input=request.user_input,
            user_context=user_context_dict
        )
        
        logger.info(
            f"✅ Processing complete: action={result.get('backend_action')}, "
            f"success={result.get('success')}"
        )
        
        return result
        
    except Exception as e:
        logger.error(f"❌ Error processing message: {e}", exc_info=True)
        return {
            "success": False,
            "backend_action": "show_error_message",
            "error": "processing_failed",
            "error_message": str(e)
        }


@app.get("/api/v1/health")
async def health_check():
    """Health check endpoint"""
    try:
        health_status = get_health()
        return health_status
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "healthy": False,
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }


@app.get("/api/v1/metrics")
async def get_performance_metrics():
    """Get AI performance metrics"""
    try:
        return get_metrics()
    except Exception as e:
        logger.error(f"Failed to get metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/costs")
async def get_cost_analysis():
    """Get cost analysis"""
    try:
        return get_costs()
    except Exception as e:
        logger.error(f"Failed to get costs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Startup Event
# ============================================================================

@app.on_event("startup")
async def startup_event():
    """Run on startup"""
    logger.info("="*70)
    logger.info("🚀 Jira AI Assistant API Starting...")
    logger.info("="*70)
    
    # Validate configuration
    validation = ai_assistant.validate_configuration()
    
    if not validation["valid"]:
        logger.error("❌ Configuration validation failed:")
        for issue in validation.get("issues", []):
            logger.error(f"   - {issue}")
        logger.error("\n⚠️  API will start but may not function correctly!")
    else:
        logger.info("✅ Configuration validated successfully")
    
    if validation.get("warnings"):
        for warning in validation["warnings"]:
            logger.warning(f"⚠️  {warning}")
    
    logger.info(f"🌍 Environment: {validation.get('environment')}")
    logger.info(f"🤖 Primary Model: {validation.get('primary_model')}")
    logger.info(f"💾 Cache Enabled: {validation.get('cache_enabled')}")
    logger.info(f"💰 Max Daily Cost: ${validation.get('max_daily_cost')}")
    logger.info("="*70)


@app.on_event("shutdown")
async def shutdown_event():
    """Run on shutdown"""
    logger.info("👋 Jira AI Assistant API Shutting Down...")


if __name__ == "__main__":
    import uvicorn
    
    # Get port from environment or use default
    port = int(os.getenv("AI_ENGINE_PORT", "8000"))
    
    logger.info(f"Starting server on http://0.0.0.0:{port}")
    
    uvicorn.run(
        "ai_engine_api:app",
        host="0.0.0.0",
        port=port,
        reload=True,  # Auto-reload on code changes (disable in production)
        log_level="info"
    )