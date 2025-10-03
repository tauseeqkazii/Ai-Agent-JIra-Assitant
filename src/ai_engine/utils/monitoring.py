from typing import Dict, Any, List
import time
from datetime import datetime, timedelta
from .metrics import MetricsCollector
from .error_handler import error_handler
from .advanced_cache import SemanticCacheManager
from ..core.config import config

class ProductionMonitor:
    """Production monitoring and health check system"""
    
    def __init__(self):
        self.metrics = MetricsCollector()
        self.start_time = datetime.now()
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get overall system health status"""
        try:
            # Check critical components
            openai_healthy = self._check_openai_health()
            cache_healthy = self._check_cache_health()
            error_rate_ok = self._check_error_rate()
            
            overall_healthy = openai_healthy and cache_healthy and error_rate_ok
            
            return {
                "healthy": overall_healthy,
                "timestamp": datetime.now().isoformat(),
                "uptime_hours": self._get_uptime_hours(),
                "components": {
                    "openai_api": {"healthy": openai_healthy},
                    "cache_system": {"healthy": cache_healthy}, 
                    "error_rate": {"healthy": error_rate_ok}
                },
                "environment": config.environment,
                "version": "1.0.0"
            }
            
        except Exception as e:
            return {
                "healthy": False,
                "error": f"Health check failed: {str(e)}",
                "timestamp": datetime.now().isoformat()
            }
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get detailed performance metrics"""
        try:
            stats = self.metrics.get_stats()
            error_stats = error_handler.get_error_stats()
            
            return {
                "requests": {
                    "total_processed": stats.get("total_classifications", 0),
                    "backend_shortcuts": stats.get("backend_shortcuts", 0),
                    "llm_calls": stats.get("llm_calls", 0),
                    "average_confidence": stats.get("average_confidence", 0.0)
                },
                "performance": {
                    "cache_hit_rate": self._calculate_cache_hit_rate(),
                    "average_response_time": self._get_average_response_time(),
                    "tokens_per_hour": self._get_tokens_per_hour(),
                    "cost_efficiency": self._calculate_cost_efficiency()
                },
                "errors": {
                    "total_errors": error_stats.get("total_errors", 0),
                    "error_rate": self._calculate_error_rate(),
                    "errors_by_component": error_stats.get("errors_by_component", {}),
                    "circuit_breakers": error_stats.get("circuit_breakers", {})
                },
                "quality": {
                    "average_quality_score": self._get_average_quality_score(),
                    "auto_approval_rate": self._get_auto_approval_rate(),
                    "user_edit_rate": self._get_user_edit_rate()
                },
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                "error": f"Failed to get performance metrics: {str(e)}",
                "timestamp": datetime.now().isoformat()
            }
    
    def get_cost_analysis(self) -> Dict[str, Any]:
        """Get cost analysis and optimization suggestions"""
        try:
            api_calls = self.metrics.metrics.get("api_calls", [])
            
            if not api_calls:
                return {"total_cost_estimate": 0.0, "suggestions": []}
            
            # Calculate token costs (approximate)
            total_tokens = sum(call.get("tokens_used", 0) for call in api_calls)
            
            # Rough cost estimates (as of 2024)
            gpt4_cost_per_1k = 0.03  # $0.03 per 1K tokens
            gpt35_cost_per_1k = 0.002  # $0.002 per 1K tokens
            
            total_cost = 0.0
            model_usage = {}
            
            for call in api_calls:
                tokens = call.get("tokens_used", 0)
                model = call.get("model", "")
                
                if model not in model_usage:
                    model_usage[model] = {"tokens": 0, "calls": 0}
                
                model_usage[model]["tokens"] += tokens
                model_usage[model]["calls"] += 1
                
                if "gpt-4" in model.lower():
                    total_cost += (tokens / 1000) * gpt4_cost_per_1k
                elif "gpt-3.5" in model.lower():
                    total_cost += (tokens / 1000) * gpt35_cost_per_1k
            
            # Generate optimization suggestions
            suggestions = self._generate_cost_optimization_suggestions(model_usage, api_calls)
            
            return {
                "total_cost_estimate": round(total_cost, 4),
                "total_tokens": total_tokens,
                "model_usage": model_usage,
                "cost_per_request": round(total_cost / max(len(api_calls), 1), 4),
                "optimization_suggestions": suggestions,
                "analysis_period": "current_session",
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                "error": f"Cost analysis failed: {str(e)}",
                "timestamp": datetime.now().isoformat()
            }
    
    def _check_openai_health(self) -> bool:
        """Check if OpenAI API is accessible"""
        try:
            # Simple check - could be enhanced with actual API ping
            return config.openai_api_key is not None and len(config.openai_api_key) > 20
        except:
            return False
    
    def _check_cache_health(self) -> bool:
        """Check cache system health"""
        try:
            # Could add actual cache connectivity check
            return config.cache_enabled
        except:
            return False
    
    def _check_error_rate(self) -> bool:
        """Check if error rate is within acceptable limits"""
        try:
            error_stats = error_handler.get_error_stats()
            total_errors = error_stats.get("total_errors", 0)
            
            # If we have very few interactions, consider it healthy
            if total_errors < 5:
                return True
            
            # Calculate error rate from metrics
            total_requests = self.metrics.get_stats().get("total_classifications", 0)
            if total_requests == 0:
                return True
                
            error_rate = total_errors / total_requests
            return error_rate <= config.error_rate_threshold
            
        except:
            return False
    
    def _get_uptime_hours(self) -> float:
        """Get uptime in hours"""
        uptime = datetime.now() - self.start_time
        return round(uptime.total_seconds() / 3600, 2)
    
    def _calculate_cache_hit_rate(self) -> float:
        """Calculate cache hit rate"""
        try:
            # This would need to be implemented in cache manager
            return 0.0  # Placeholder
        except:
            return 0.0
    
    def _get_average_response_time(self) -> float:
        """Get average response time"""
        try:
            # This would be tracked by metrics collector
            return 0.0  # Placeholder
        except:
            return 0.0
    
    def _get_tokens_per_hour(self) -> int:
        """Calculate tokens used per hour"""
        try:
            api_calls = self.metrics.metrics.get("api_calls", [])
            if not api_calls:
                return 0
                
            total_tokens = sum(call.get("tokens_used", 0) for call in api_calls)
            uptime_hours = self._get_uptime_hours()
            
            return int(total_tokens / max(uptime_hours, 1))
            
        except:
            return 0
    
    def _calculate_cost_efficiency(self) -> Dict[str, float]:
        """Calculate cost efficiency metrics"""
        try:
            stats = self.metrics.get_stats()
            backend_shortcuts = stats.get("backend_shortcuts", 0)
            llm_calls = stats.get("llm_calls", 0)
            total = backend_shortcuts + llm_calls
            
            if total == 0:
                return {"backend_shortcut_rate": 0.0, "llm_usage_rate": 0.0}
            
            return {
                "backend_shortcut_rate": round(backend_shortcuts / total, 3),
                "llm_usage_rate": round(llm_calls / total, 3)
            }
            
        except:
            return {"backend_shortcut_rate": 0.0, "llm_usage_rate": 0.0}
    
    def _calculate_error_rate(self) -> float:
        """Calculate current error rate"""
        try:
            error_stats = error_handler.get_error_stats()
            total_errors = error_stats.get("total_errors", 0)
            total_requests = self.metrics.get_stats().get("total_classifications", 0)
            
            if total_requests == 0:
                return 0.0
                
            return round(total_errors / total_requests, 4)
            
        except:
            return 0.0
    
    def _get_average_quality_score(self) -> float:
        """Get average quality score of generated content"""
        # This would be tracked by the pipeline
        return 0.85  # Placeholder
    
    def _get_auto_approval_rate(self) -> float:
        """Get rate of automatically approved content"""
        # This would be tracked by the validation system
        return 0.75  # Placeholder
    
    def _get_user_edit_rate(self) -> float:
        """Get rate of user edits on generated content"""
        # This would be tracked by backend
        return 0.20  # Placeholder
    
    def _generate_cost_optimization_suggestions(self, model_usage: Dict, api_calls: List) -> List[str]:
        """Generate cost optimization suggestions"""
        suggestions = []
        
        try:
            total_calls = len(api_calls)
            gpt4_calls = model_usage.get("gpt-4-turbo-preview", {}).get("calls", 0)
            
            # Suggest using faster models
            if gpt4_calls / max(total_calls, 1) > 0.7:
                suggestions.append("Consider using GPT-3.5-turbo for simple classification tasks to reduce costs")
            
            # Suggest better caching
            if config.cache_enabled and self._calculate_cache_hit_rate() < 0.3:
                suggestions.append("Improve semantic caching to reduce duplicate API calls")
            
            # Suggest prompt optimization
            avg_tokens = sum(call.get("tokens_used", 0) for call in api_calls) / max(len(api_calls), 1)
            if avg_tokens > 800:
                suggestions.append("Optimize prompts to reduce token usage per request")
            
            # Suggest batch processing
            if total_calls > 50:
                suggestions.append("Implement batch processing for non-urgent requests")
            
            if not suggestions:
                suggestions.append("Cost optimization is performing well - no immediate suggestions")
                
        except Exception as e:
            suggestions.append(f"Could not generate optimization suggestions: {str(e)}")
        
        return suggestions

# Global monitor instance
production_monitor = ProductionMonitor()