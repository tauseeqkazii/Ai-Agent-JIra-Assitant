"""
Metrics Collector Module
Tracks AI performance, costs, and usage statistics
"""

from typing import Dict, Any, List, Optional
from collections import defaultdict
from datetime import datetime, timedelta
from threading import Lock
import logging

from ..core.config import config

logger = logging.getLogger(__name__)


class MetricsCollector:
    """
    Thread-safe metrics collection with memory limits and cost tracking
    """
    
    def __init__(self, max_records: Optional[int] = None):
        """
        Initialize metrics collector
        
        Args:
            max_records: Maximum records to keep in memory (defaults to config)
        """
        self.metrics: Dict[str, List[Dict]] = defaultdict(list)
        self.max_records = max_records or config.metrics_max_records
        self._lock = Lock()
        
        logger.info(f"MetricsCollector initialized with max_records={self.max_records}")
    
    def record_classification(self, route_type: str, confidence: float, user_id: str):
        """
        Record classification metrics (thread-safe)
        
        Args:
            route_type: Type of route classified
            confidence: Classification confidence score
            user_id: User who made the request
        """
        with self._lock:
            self.metrics["classifications"].append({
                "route_type": route_type,
                "confidence": confidence,
                "user_id": user_id,
                "timestamp": datetime.utcnow().isoformat()
            })
            
            # Enforce memory limit
            if len(self.metrics["classifications"]) > self.max_records:
                self.metrics["classifications"] = self.metrics["classifications"][-self.max_records:]
            
            logger.debug(f"Classified: {route_type} (confidence: {confidence:.2f})")
    
    def record_api_call(
        self, 
        model: str, 
        tokens_used: int, 
        success: bool,
        prompt_tokens: int = 0,
        completion_tokens: int = 0
    ):
        """
        Record OpenAI API call with cost calculation (thread-safe)
        
        Args:
            model: Model used (e.g., "gpt-4o")
            tokens_used: Total tokens consumed
            success: Whether call succeeded
            prompt_tokens: Input tokens
            completion_tokens: Output tokens
        """
        with self._lock:
            # Calculate cost
            cost_usd = self._calculate_cost(model, prompt_tokens, completion_tokens)
            
            self.metrics["api_calls"].append({
                "model": model,
                "tokens_used": tokens_used,
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "cost_usd": cost_usd,
                "success": success,
                "timestamp": datetime.utcnow().isoformat()
            })
            
            # Enforce memory limit
            if len(self.metrics["api_calls"]) > self.max_records:
                self.metrics["api_calls"] = self.metrics["api_calls"][-self.max_records:]
            
            logger.info(f"API call: {model} - {tokens_used} tokens - ${cost_usd:.4f}")
    
    def record_pipeline_execution(
        self, 
        route_type: str, 
        requires_llm: bool, 
        success: bool, 
        processing_time: Optional[float],
        user_id: str
    ):
        """
        Record pipeline execution metrics (thread-safe)
        
        Args:
            route_type: Route that was executed
            requires_llm: Whether LLM processing was needed
            success: Whether execution succeeded
            processing_time: Time taken in seconds (optional)
            user_id: User who made the request
        """
        with self._lock:
            self.metrics["pipeline_executions"].append({
                "route_type": route_type,
                "requires_llm": requires_llm,
                "success": success,
                "processing_time": processing_time,
                "user_id": user_id,
                "timestamp": datetime.utcnow().isoformat()
            })
            
            # Enforce memory limit
            if len(self.metrics["pipeline_executions"]) > self.max_records:
                self.metrics["pipeline_executions"] = self.metrics["pipeline_executions"][-self.max_records:]
            
            logger.debug(f"Pipeline: {route_type} - LLM:{requires_llm} - Success:{success}")
    
    def record_cache_event(self, event_type: str, key_prefix: str, hit: bool = False):
        """
        Record cache hit/miss events (thread-safe)
        
        Args:
            event_type: Type of cache event (hit, miss, set)
            key_prefix: Cache key prefix (e.g., "route", "comment")
            hit: Whether it was a cache hit
        """
        with self._lock:
            self.metrics["cache_events"].append({
                "event_type": event_type,
                "key_prefix": key_prefix,
                "hit": hit,
                "timestamp": datetime.utcnow().isoformat()
            })
            
            # Enforce memory limit
            if len(self.metrics["cache_events"]) > self.max_records:
                self.metrics["cache_events"] = self.metrics["cache_events"][-self.max_records:]
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get current metrics statistics (thread-safe)
        
        Returns:
            Dictionary with aggregated statistics
        """
        with self._lock:
            if not self.metrics["classifications"]:
                return {
                    "total_classifications": 0,
                    "total_api_calls": 0,
                    "total_cost_usd": 0.0
                }
            
            classifications = self.metrics["classifications"]
            api_calls = self.metrics.get("api_calls", [])
            
            # Aggregate classification stats
            route_counts = defaultdict(int)
            total_confidence = 0.0
            
            for record in classifications:
                route_counts[record["route_type"]] += 1
                total_confidence += record["confidence"]
            
            # Aggregate API call stats
            total_cost = sum(call.get("cost_usd", 0.0) for call in api_calls)
            total_tokens = sum(call.get("tokens_used", 0) for call in api_calls)
            successful_calls = sum(1 for call in api_calls if call.get("success"))
            
            # Calculate backend vs LLM distribution
            backend_shortcuts = (
                route_counts.get("backend_completion", 0) + 
                route_counts.get("backend_productivity", 0)
            )
            llm_calls = sum(route_counts.values()) - backend_shortcuts
            
            return {
                "total_classifications": len(classifications),
                "average_confidence": total_confidence / len(classifications),
                "route_distribution": dict(route_counts),
                "backend_shortcuts": backend_shortcuts,
                "llm_calls": llm_calls,
                "total_api_calls": len(api_calls),
                "successful_api_calls": successful_calls,
                "total_tokens": total_tokens,
                "total_cost_usd": round(total_cost, 4),
                "average_cost_per_call": round(total_cost / max(len(api_calls), 1), 4)
            }
    
    def get_daily_cost(self) -> float:
        """
        Calculate total cost for today (thread-safe)
        
        Returns:
            Total cost in USD for current day
        """
        with self._lock:
            api_calls = self.metrics.get("api_calls", [])
            if not api_calls:
                return 0.0
            
            today = datetime.utcnow().date()
            daily_calls = [
                call for call in api_calls
                if datetime.fromisoformat(call["timestamp"]).date() == today
            ]
            
            daily_cost = sum(call.get("cost_usd", 0.0) for call in daily_calls)
            return round(daily_cost, 4)
    
    def get_hourly_stats(self, hours: int = 1) -> Dict[str, Any]:
        """
        Get statistics for the last N hours (thread-safe)
        
        Args:
            hours: Number of hours to look back
            
        Returns:
            Statistics for the time period
        """
        with self._lock:
            cutoff_time = datetime.utcnow() - timedelta(hours=hours)
            
            api_calls = self.metrics.get("api_calls", [])
            recent_calls = [
                call for call in api_calls
                if datetime.fromisoformat(call["timestamp"]) >= cutoff_time
            ]
            
            if not recent_calls:
                return {
                    "period_hours": hours,
                    "api_calls": 0,
                    "total_tokens": 0,
                    "total_cost_usd": 0.0
                }
            
            total_tokens = sum(call.get("tokens_used", 0) for call in recent_calls)
            total_cost = sum(call.get("cost_usd", 0.0) for call in recent_calls)
            
            return {
                "period_hours": hours,
                "api_calls": len(recent_calls),
                "total_tokens": total_tokens,
                "tokens_per_hour": total_tokens // hours if hours > 0 else 0,
                "total_cost_usd": round(total_cost, 4),
                "cost_per_hour": round(total_cost / hours, 4) if hours > 0 else 0.0
            }
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """
        Get cache performance statistics (thread-safe)
        
        Returns:
            Cache hit rate and related metrics
        """
        with self._lock:
            cache_events = self.metrics.get("cache_events", [])
            if not cache_events:
                return {
                    "total_events": 0,
                    "hit_rate": 0.0
                }
            
            hits = sum(1 for event in cache_events if event.get("hit"))
            total = len(cache_events)
            
            return {
                "total_events": total,
                "cache_hits": hits,
                "cache_misses": total - hits,
                "hit_rate": round(hits / total, 3) if total > 0 else 0.0
            }
    
    def _calculate_cost(self, model: str, prompt_tokens: int, completion_tokens: int) -> float:
        """
        Calculate cost for API call based on token usage
        
        Args:
            model: Model name
            prompt_tokens: Input tokens
            completion_tokens: Output tokens
            
        Returns:
            Cost in USD
        """
        cost_config = config.cost_config
        
        # Get pricing for model (default to gpt-3.5 if not found)
        if model in cost_config:
            pricing = cost_config[model]
        elif "gpt-4" in model.lower():
            pricing = cost_config.get("gpt-4o", {"input": 0.0025, "output": 0.01})
        else:
            pricing = cost_config.get("gpt-3.5-turbo", {"input": 0.0005, "output": 0.0015})
        
        # Calculate cost (pricing is per 1K tokens)
        input_cost = (prompt_tokens / 1000) * pricing["input"]
        output_cost = (completion_tokens / 1000) * pricing["output"]
        
        return input_cost + output_cost
    
    def reset_stats(self):
        """Reset all metrics (thread-safe)"""
        with self._lock:
            self.metrics.clear()
            logger.info("All metrics reset")
    
    def export_metrics(self, metric_type: Optional[str] = None) -> List[Dict]:
        """
        Export metrics for external storage/analysis (thread-safe)
        
        Args:
            metric_type: Specific metric type to export, or None for all
            
        Returns:
            List of metric records
        """
        with self._lock:
            if metric_type:
                return self.metrics.get(metric_type, []).copy()
            else:
                return {
                    key: values.copy() 
                    for key, values in self.metrics.items()
                }


# Global metrics instance (can be imported by other modules)
metrics = MetricsCollector()