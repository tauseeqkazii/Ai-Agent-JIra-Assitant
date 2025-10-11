"""
FastAPI Backend for Jira AI Assistant
Connects AI Engine to Frontend
"""

from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
import logging
from datetime import datetime
import sys
import os

# Add src to path
sys.path.append('src')

from src.ai_engine.main import (
    ai_assistant,
    process_message,
    get_health,
    get_metrics,
    get_costs
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI
app = FastAPI(
    title="Jira AI Assistant API",
    description="AI-powered Jira task management assistant",
    version="2.0.0"
)

# CORS Configuration (allows frontend to call API)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your frontend domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================================
# REQUEST/RESPONSE MODELS
# ============================================================================

class ProcessMessageRequest(BaseModel):
    """Request model for processing user messages"""
    user_input: str = Field(..., description="User's message", min_length=1, max_length=5000)
    user_context: Dict[str, Any] = Field(..., description="User context information")
    
    class Config:
        json_schema_extra = {
            "example": {
                "user_input": "I fixed the login bug and tested it",
                "user_context": {
                    "user_id": "user123",
                    "user_name": "John Doe",
                    "role": "Senior Engineer",
                    "current_project": "Mobile App"
                }
            }
        }


class ProcessMessageResponse(BaseModel):
    """Response model for processed messages"""
    success: bool
    route_type: Optional[str] = None
    backend_action: Optional[str] = None
    generated_content: Optional[str] = None
    requires_user_approval: Optional[bool] = None
    error: Optional[str] = None
    error_message: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class HealthResponse(BaseModel):
    """Health check response"""
    healthy: bool
    timestamp: str
    components: Optional[Dict[str, Any]] = None


class MetricsResponse(BaseModel):
    """Metrics response"""
    requests: Dict[str, Any]
    performance: Dict[str, Any]
    errors: Dict[str, Any]


# ============================================================================
# AUTHENTICATION (Simple token-based for demo)
# ============================================================================

API_TOKEN = os.getenv("OPENAI_API_KEY")  # In production, use proper auth

def verify_token(authorization: str = Header(None)):
    """Verify API token"""
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing authorization header")
    
    if authorization != f"Bearer {API_TOKEN}":
        raise HTTPException(status_code=401, detail="Invalid token")
    
    return True


# ============================================================================
# MAIN API ENDPOINTS
# ============================================================================

@app.post("/api/v1/process", response_model=ProcessMessageResponse)
async def process_user_message(
    request: ProcessMessageRequest,
    authorized: bool = Depends(verify_token)
):
    """
    Main endpoint - Process user message with AI
    
    **What it does:**
    - Routes simple commands to backend (done, productivity queries)
    - Uses AI for complex updates and email generation
    - Returns structured response for frontend to handle
    
    **Frontend should:**
    1. Call this endpoint with user input
    2. Check `backend_action` to decide what to do
    3. Display `generated_content` if present
    4. Show approval UI if `requires_user_approval` is true
    """
    try:
        logger.info(f"Processing message from user: {request.user_context.get('user_id')}")
        
        # Validate user_context has required fields
        if not request.user_context.get("user_id"):
            raise HTTPException(
                status_code=400,
                detail="user_context must include user_id"
            )
        
        # Process with AI engine
        result = process_message(
            user_input=request.user_input,
            user_context=request.user_context
        )
        
        # Format response for frontend
        response = ProcessMessageResponse(
            success=result.get("success", False),
            route_type=result.get("route_type"),
            backend_action=result.get("backend_action"),
            generated_content=result.get("generated_content"),
            requires_user_approval=result.get("requires_user_approval"),
            error=result.get("error"),
            error_message=result.get("error_message"),
            metadata={
                "confidence": result.get("confidence"),
                "quality_score": result.get("quality_score"),
                "processing_time": result.get("pipeline_metadata", {}).get("total_processing_time"),
                "from_cache": result.get("processing_metadata", {}).get("from_cache", False)
            }
        )
        
        return response
        
    except Exception as e:
        logger.error(f"Error processing message: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/health", response_model=HealthResponse)
async def health_check():
    """
    Health check endpoint
    
    **Frontend should:**
    - Poll this endpoint every 30 seconds
    - Show warning banner if unhealthy
    """
    health = get_health()
    return HealthResponse(
        healthy=health.get("healthy", False),
        timestamp=health.get("timestamp", datetime.utcnow().isoformat()),
        components=health.get("components")
    )


@app.get("/api/v1/metrics")
async def get_system_metrics(authorized: bool = Depends(verify_token)):
    """
    Get system metrics (admin only)
    
    **Frontend should:**
    - Display in admin dashboard
    - Show cache hit rate, costs, performance
    """
    try:
        metrics = get_metrics()
        return metrics
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/costs")
async def get_cost_analysis(authorized: bool = Depends(verify_token)):
    """
    Get cost analysis (admin only)
    
    **Frontend should:**
    - Display daily cost
    - Show optimization suggestions
    - Alert if approaching limit
    """
    try:
        costs = get_costs()
        return costs
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/validate-comment")
async def validate_comment(
    comment: str = Field(..., description="Comment to validate"),
    authorized: bool = Depends(verify_token)
):
    """
    Validate a comment before posting to Jira
    
    **Frontend should:**
    - Call this before user approves a generated comment
    - Show validation warnings if any
    """
    try:
        from src.ai_engine.generation.response_validator import ResponseValidator
        
        validator = ResponseValidator()
        validation = validator.validate_response(comment, "llm_rephrasing")
        
        return {
            "valid": validation["overall_score"] >= 0.7,
            "score": validation["overall_score"],
            "flags": validation.get("flags", []),
            "recommendations": validation.get("recommendations", [])
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# WEBHOOK ENDPOINTS (for Jira integration)
# ============================================================================

@app.post("/api/v1/jira/task-update")
async def jira_task_update_webhook(
    task_id: str,
    user_id: str,
    update_text: str,
    authorized: bool = Depends(verify_token)
):
    """
    Webhook endpoint for Jira task updates
    
    **Jira should:**
    - Call this when user submits a task update
    - Pass task_id, user_id, and update text
    - Receive AI-processed response
    """
    try:
        result = process_message(
            user_input=update_text,
            user_context={
                "user_id": user_id,
                "task_id": task_id
            }
        )
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# ADMIN ENDPOINTS
# ============================================================================

@app.get("/api/v1/admin/stats")
async def get_admin_stats(authorized: bool = Depends(verify_token)):
    """
    Get comprehensive statistics (admin dashboard)
    """
    try:
        stats = ai_assistant.get_pipeline_stats()
        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/admin/config")
async def get_config(authorized: bool = Depends(verify_token)):
    """
    Get current configuration
    """
    try:
        config_validation = ai_assistant.validate_configuration()
        return config_validation
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/admin/clear-cache")
async def clear_cache(authorized: bool = Depends(verify_token)):
    """
    Clear AI cache (admin only)
    """
    try:
        ai_assistant.pipeline.cache_manager.clear()
        return {"success": True, "message": "Cache cleared"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# STARTUP/SHUTDOWN EVENTS
# ============================================================================

@app.on_event("startup")
async def startup_event():
    """Run on server startup"""
    logger.info("🚀 Starting Jira AI Assistant API")
    
    # Validate configuration
    config = ai_assistant.validate_configuration()
    if not config["valid"]:
        logger.error(f"Invalid configuration: {config['issues']}")
        raise Exception("Invalid configuration")
    
    logger.info("✅ AI Assistant initialized successfully")


@app.on_event("shutdown")
async def shutdown_event():
    """Run on server shutdown"""
    logger.info("🛑 Shutting down Jira AI Assistant API")


# ============================================================================
# ERROR HANDLERS
# ============================================================================

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Catch all unhandled exceptions"""
    logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
    return {
        "success": False,
        "error": "internal_server_error",
        "error_message": str(exc)
    }


# ============================================================================
# RUN SERVER
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "api:app",
        host="0.0.0.0",
        port=8000,
        reload=True,  # Auto-reload on code changes (dev only)
        log_level="info"
    )