import logging
import traceback
from typing import Dict, Any, Optional, Callable
from functools import wraps
from datetime import datetime, timedelta
from collections import defaultdict
from ..core.config import config

logger = logging.getLogger(__name__)

class ProductionErrorHandler:
    """Production-grade error handling with monitoring and alerts"""
    
    def __init__(self):
        self.error_counts = defaultdict(int)
        self.error_history = []
        self.last_alert_time = {}
        self.circuit_breakers = {}
    
    def with_error_handling(self, component_name: str, fallback_response: Optional[Dict] = None):
        """Decorator for robust error handling with circuit breaker pattern"""
        def decorator(func: Callable):
            @wraps(func)
            def wrapper(*args, **kwargs):
                try:
                    # Check circuit breaker
                    if self._is_circuit_open(component_name):
                        logger.warning(f"Circuit breaker open for {component_name}")
                        return self._get_circuit_breaker_response(component_name, fallback_response)
                    
                    # Execute function
                    result = func(*args, **kwargs)
                    
                    # Record success (reset circuit breaker)
                    self._record_success(component_name)
                    
                    return result
                    
                except Exception as e:
                    # Record error
                    error_context = self._record_error(component_name, e, args, kwargs)
                    
                    # Check if we should open circuit breaker
                    self._update_circuit_breaker(component_name)
                    
                    # Send alerts if needed
                    if self._should_send_alert(component_name):
                        self._send_error_alert(component_name, e, error_context)
                    
                    # Return fallback response or raise
                    if fallback_response is not None:
                        logger.info(f"Using fallback response for {component_name}")
                        return fallback_response
                    
                    # Re-raise if no fallback
                    raise e
                    
            return wrapper
        return decorator
    
    def _record_error(self, component_name: str, error: Exception, args, kwargs) -> Dict:
        """Record error details for monitoring"""
        error_context = {
            "component": component_name,
            "error_type": type(error).__name__,
            "error_message": str(error),
            "timestamp": datetime.now().isoformat(),
            "args_count": len(args),
            "kwargs_keys": list(kwargs.keys()) if kwargs else [],
            "traceback": traceback.format_exc()
        }
        
        self.error_counts[component_name] += 1
        self.error_history.append(error_context)
        
        # Keep only recent errors (last 1000)
        if len(self.error_history) > 1000:
            self.error_history = self.error_history[-1000:]
        
        logger.error(f"Error in {component_name}: {error_context['error_type']} - {error_context['error_message']}")
        
        return error_context
    
    def _record_success(self, component_name: str):
        """Record successful execution"""
        if component_name in self.circuit_breakers:
            self.circuit_breakers[component_name]["consecutive_failures"] = 0
    
    def _is_circuit_open(self, component_name: str) -> bool:
        """Check if circuit breaker is open"""
        if component_name not in self.circuit_breakers:
            return False
            
        breaker = self.circuit_breakers[component_name]
        
        # Check if enough time has passed to try again
        if breaker["state"] == "open":
            if datetime.now() > breaker["next_attempt"]:
                breaker["state"] = "half_open"
                logger.info(f"Circuit breaker for {component_name} moved to half-open")
                return False
            return True
            
        return False
    
    def _update_circuit_breaker(self, component_name: str):
        """Update circuit breaker state based on errors"""
        if component_name not in self.circuit_breakers:
            self.circuit_breakers[component_name] = {
                "consecutive_failures": 0,
                "state": "closed",  # closed, open, half_open
                "next_attempt": None,
                "failure_threshold": 5,
                "timeout_minutes": 5
            }
        
        breaker = self.circuit_breakers[component_name]
        breaker["consecutive_failures"] += 1
        
        # Open circuit if too many failures
        if breaker["consecutive_failures"] >= breaker["failure_threshold"]:
            breaker["state"] = "open"
            breaker["next_attempt"] = datetime.now() + timedelta(minutes=breaker["timeout_minutes"])
            logger.warning(f"Circuit breaker opened for {component_name} after {breaker['consecutive_failures']} failures")
    
    def _get_circuit_breaker_response(self, component_name: str, fallback_response: Optional[Dict]) -> Dict:
        """Get response when circuit breaker is open"""
        if fallback_response:
            return {
                **fallback_response,
                "circuit_breaker_active": True,
                "component": component_name
            }
        
        return {
            "success": False,
            "error": "circuit_breaker_open",
            "error_message": f"Service temporarily unavailable for {component_name}",
            "circuit_breaker_active": True,
            "retry_after_minutes": 5
        }
    
    def _should_send_alert(self, component_name: str) -> bool:
        """Determine if we should send an alert"""
        if not config.alert_on_high_error_rate:
            return False
        
        # Don't spam alerts - wait at least 10 minutes between alerts for same component
        last_alert = self.last_alert_time.get(component_name)
        if last_alert and datetime.now() - last_alert < timedelta(minutes=10):
            return False
        
        # Calculate error rate in last 5 minutes
        recent_errors = [
            err for err in self.error_history
            if err["component"] == component_name and
            datetime.now() - datetime.fromisoformat(err["timestamp"]) < timedelta(minutes=5)
        ]
        
        if len(recent_errors) >= 3:  # 3 errors in 5 minutes
            return True
        
        return False
    
    def _send_error_alert(self, component_name: str, error: Exception, error_context: Dict):
        """Send error alert (log for now, backend can implement email/slack)"""
        self.last_alert_time[component_name] = datetime.now()
        
        alert_message = f"""
        🚨 HIGH ERROR RATE ALERT 🚨
        Component: {component_name}
        Error: {type(error).__name__}: {str(error)}
        Time: {error_context['timestamp']}
        Recent Error Count: {self.error_counts[component_name]}
        """
        
        logger.critical(alert_message)
        # Backend team can implement actual alerting (email, Slack, etc.)
    
    def get_error_stats(self) -> Dict[str, Any]:
        """Get error statistics for monitoring"""
        return {
            "total_errors": len(self.error_history),
            "errors_by_component": dict(self.error_counts),
            "circuit_breakers": {
                name: {
                    "state": breaker["state"],
                    "consecutive_failures": breaker["consecutive_failures"]
                }
                for name, breaker in self.circuit_breakers.items()
            },
            "recent_errors": [
                {
                    "component": err["component"],
                    "error_type": err["error_type"],
                    "timestamp": err["timestamp"]
                }
                for err in self.error_history[-10:]  # Last 10 errors
            ]
        }

# Global error handler instance
error_handler = ProductionErrorHandler()