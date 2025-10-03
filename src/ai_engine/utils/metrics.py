import logging
from typing import Dict, Any
from collections import defaultdict
from datetime import datetime

logger = logging.getLogger(__name__)

class MetricsCollector:
    """Collect metrics for monitoring AI performance"""
    
    def __init__(self):
        self.metrics = defaultdict(list)
    
    def record_classification(self, route_type: str, confidence: float, user_id: str):
        """Record classification metrics"""
        self.metrics["classifications"].append({
            "route_type": route_type,
            "confidence": confidence,
            "user_id": user_id,
            "timestamp": datetime.utcnow().isoformat()
        })
        
        logger.info(f"Classified: {route_type} (confidence: {confidence:.2f})")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get current metrics"""
        if not self.metrics["classifications"]:
            return {"total_classifications": 0}
            
        classifications = self.metrics["classifications"]
        route_counts = defaultdict(int)
        total_confidence = 0
        
        for record in classifications:
            route_counts[record["route_type"]] += 1
            total_confidence += record["confidence"]
        
        return {
            "total_classifications": len(classifications),
            "average_confidence": total_confidence / len(classifications),
            "route_distribution": dict(route_counts),
            "backend_shortcuts": route_counts["backend_completion"] + route_counts["backend_productivity"],
            "llm_calls": sum(route_counts.values()) - (route_counts["backend_completion"] + route_counts["backend_productivity"])
        }
        
        

    def record_api_call(self, model: str, tokens_used: int, success: bool):
        """Record OpenAI API call metrics"""
        self.metrics["api_calls"].append({
            "model": model,
            "tokens_used": tokens_used,
            "success": success,
            "timestamp": datetime.utcnow().isoformat()
        })

    def record_pipeline_execution(self, route_type: str, requires_llm: bool, success: bool, 
                                processing_time: float, user_id: str):
        """Record pipeline execution metrics"""
        self.metrics["pipeline_executions"].append({
            "route_type": route_type,
            "requires_llm": requires_llm,
            "success": success,
            "processing_time": processing_time,
            "user_id": user_id,
            "timestamp": datetime.utcnow().isoformat()
        })
        
        
        