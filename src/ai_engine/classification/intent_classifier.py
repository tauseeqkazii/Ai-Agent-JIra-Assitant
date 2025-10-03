"""
Intent Classification Module
Determines routing decisions using pattern matching
"""

import re
from typing import Dict, Optional
from enum import Enum
from dataclasses import dataclass, field
import logging

logger = logging.getLogger(__name__)


class RouteType(Enum):
    """Available routing types for user requests"""
    BACKEND_COMPLETION = "backend_completion"          # Simple "done" statements
    BACKEND_PRODUCTIVITY = "backend_productivity"      # Stats queries
    LLM_REPHRASING = "llm_rephrasing"                 # Complex updates needing AI
    LLM_EMAIL = "llm_email"                           # Email generation
    LLM_CLASSIFICATION = "llm_classification"          # Ambiguous cases


@dataclass
class ClassificationResult:
    """Result of intent classification"""
    route_type: RouteType
    confidence: float
    matched_pattern: str = ""
    extracted_entities: Dict = field(default_factory=dict)  # Fixed: use default_factory


class IntentClassifier:
    """
    Classifies user intent using regex patterns
    Routes simple requests to backend, complex ones to LLM
    """
    
    def __init__(self):
        # Compile regex patterns once for performance
        self._compile_patterns()
        
        # Load confidence thresholds from config
        from ..core.config import config
        self.confidence_threshold = config.confidence_threshold
        
        logger.info("IntentClassifier initialized with compiled patterns")
    
    def _compile_patterns(self):
        """Compile all regex patterns once for better performance"""
        
        # Simple completion patterns (backend only)
        completion_patterns = [
            r'\b(done|completed|finished|complete)\b',
            r'\btask\s+(is\s+)?(done|finished|complete)',
            r'\bmark\s+as\s+(done|complete)',
            r'\b(finish|close)\s+task',
            r'^\s*(done|finished|completed)\s*$',
        ]
        self.completion_regex = re.compile('|'.join(f'({p})' for p in completion_patterns), re.IGNORECASE)
        
        # Productivity query patterns (backend calculation)
        productivity_patterns = [
            r'how\s+productive\s+was\s+I',
            r'my\s+productivity\s+(this\s+week|last\s+week)',
            r'productivity\s+(score|stats|report)',
            r'how\s+many\s+tasks\s+(completed|finished)',
            r'completion\s+rate',
            r'weekly\s+(summary|report)',
        ]
        self.productivity_regex = re.compile('|'.join(f'({p})' for p in productivity_patterns), re.IGNORECASE)
        
        # Email generation patterns
        email_patterns = [
            r'write\s+(an?\s+)?email',
            r'send\s+(an?\s+)?email',
            r'compose\s+(an?\s+)?email',
            r'email\s+(my\s+)?manager',
            r'sick\s+leave\s+(request|email)',
            r'(pto|vacation)\s+(request|email)',
        ]
        self.email_regex = re.compile('|'.join(f'({p})' for p in email_patterns), re.IGNORECASE)
        
        # Complex update indicators (need LLM rephrasing)
        complex_indicators = [
            r'\b(tested|testing|fixed|fixing|implemented|working on)\b',
            r'\b(waiting for|blocked by|pending)\b',
            r'\b(staging|production|deployment)\b',
            r'\b(issue|bug|problem|error)\b',
            r'\b(review|approval|qa|quality)\b',
        ]
        self.complex_regex = re.compile('|'.join(f'({p})' for p in complex_indicators), re.IGNORECASE)
    
    def classify(self, user_input: str) -> ClassificationResult:
        """
        Main classification method - determines routing decision
        
        Args:
            user_input: Raw user message
            
        Returns:
            ClassificationResult with route type and confidence
        """
        if not user_input or not user_input.strip():
            logger.warning("Empty input received for classification")
            return ClassificationResult(
                route_type=RouteType.LLM_CLASSIFICATION,
                confidence=0.0,
                matched_pattern="empty_input"
            )
        
        # Validate input length
        from ..core.config import config
        if len(user_input) > config.max_input_length:
            logger.warning(f"Input too long: {len(user_input)} chars")
            user_input = user_input[:config.max_input_length]
        
        # Normalize input once
        user_input_normalized = user_input.strip()
        
        # Priority 1: Check for simple completions (highest confidence)
        if self.completion_regex.search(user_input_normalized):
            logger.debug("Matched completion pattern")
            return ClassificationResult(
                route_type=RouteType.BACKEND_COMPLETION,
                confidence=0.95,
                matched_pattern="completion"
            )
        
        # Priority 2: Check for productivity queries
        if self.productivity_regex.search(user_input_normalized):
            logger.debug("Matched productivity pattern")
            return ClassificationResult(
                route_type=RouteType.BACKEND_PRODUCTIVITY,
                confidence=0.90,
                matched_pattern="productivity"
            )
        
        # Priority 3: Check for email requests
        if self.email_regex.search(user_input_normalized):
            logger.debug("Matched email pattern")
            return ClassificationResult(
                route_type=RouteType.LLM_EMAIL,
                confidence=0.85,
                matched_pattern="email"
            )
        
        # Priority 4: Check if it's a complex update (needs rephrasing)
        complex_matches = len(self.complex_regex.findall(user_input_normalized))
        
        # If multiple complex indicators or long text, route to LLM
        if complex_matches >= 2 or len(user_input_normalized) > 50:
            logger.debug(f"Complex update detected: {complex_matches} indicators")
            return ClassificationResult(
                route_type=RouteType.LLM_REPHRASING,
                confidence=0.80,
                matched_pattern=f"complex_indicators_{complex_matches}"
            )
        
        # Default: send to LLM for classification (ambiguous cases)
        logger.debug("No clear pattern matched, defaulting to LLM classification")
        return ClassificationResult(
            route_type=RouteType.LLM_CLASSIFICATION,
            confidence=0.60,
            matched_pattern="ambiguous"
        )
    
    def extract_task_info(self, user_input: str) -> Dict:
        """
        Extract task-related information from user input
        
        Args:
            user_input: Raw user message
            
        Returns:
            Dictionary with extracted entities (task IDs, status keywords)
        """
        if not user_input:
            return {}
        
        entities = {}
        
        try:
            # Extract task numbers (e.g., "task #123", "JIRA-456", "BUG-789")
            # Fixed: Changed pattern to work with JIRA-style IDs
            task_pattern = r'(?:task\s*#?|[A-Z]+-?)(\d+)\b'
            task_matches = re.findall(task_pattern, user_input, re.IGNORECASE)
            if task_matches:
                entities['task_ids'] = list(set(task_matches))  # Remove duplicates
                logger.debug(f"Extracted task IDs: {entities['task_ids']}")
            
            # Extract completion status keywords
            status_keywords = ['done', 'completed', 'finished', 'pending', 'blocked', 'testing', 'in progress', 'resolved']
            found_keywords = [kw for kw in status_keywords if kw in user_input.lower()]
            if found_keywords:
                entities['status_keywords'] = found_keywords
                logger.debug(f"Extracted status keywords: {found_keywords}")
            
            # Extract technical terms (for context)
            technical_terms = ['api', 'bug', 'feature', 'database', 'frontend', 'backend', 'deployment', 'staging', 'production']
            found_terms = [term for term in technical_terms if term in user_input.lower()]
            if found_terms:
                entities['technical_terms'] = found_terms
                logger.debug(f"Extracted technical terms: {found_terms}")
        
        except Exception as e:
            logger.error(f"Error extracting task info: {e}")
            # Return empty dict instead of crashing
        
        return entities
    
    def get_pattern_stats(self) -> Dict:
        """
        Get statistics about pattern matching (for monitoring)
        
        Returns:
            Dictionary with pattern configuration info
        """
        return {
            "patterns_compiled": True,
            "confidence_threshold": self.confidence_threshold,
            "route_types": [rt.value for rt in RouteType],
        }