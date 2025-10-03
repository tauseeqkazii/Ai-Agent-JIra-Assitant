import re
from typing import Dict, List, Tuple
from enum import Enum
from dataclasses import dataclass

class RouteType(Enum):
    BACKEND_COMPLETION = "backend_completion"      # "done", "finished"
    BACKEND_PRODUCTIVITY = "backend_productivity"  # "how productive was I"  
    LLM_REPHRASING = "llm_rephrasing"             # Complex updates needing professional tone
    LLM_EMAIL = "llm_email"                       # Email generation
    LLM_CLASSIFICATION = "llm_classification"      # Ambiguous cases

@dataclass
class ClassificationResult:
    route_type: RouteType
    confidence: float
    # confidence=config.settings.completion_confidence
    matched_pattern: str = ""
    extracted_entities: Dict = field(default_factory=dict)

class IntentClassifier:
    def __init__(self):
        # Simple completion patterns (backend only)
        self.completion_patterns = [
            r'\b(done|completed|finished|complete)\b',
            r'\btask\s+(is\s+)?(done|finished|complete)',
            r'\bmark\s+as\s+(done|complete)',
            r'\b(finish|close)\s+task',
            r'^\s*(done|finished|completed)\s*$',  # Just the word alone
        ]
        
        # Productivity query patterns (backend calculation)
        self.productivity_patterns = [
            r'how\s+productive\s+was\s+I',
            r'my\s+productivity\s+(this\s+week|last\s+week)',
            r'productivity\s+(score|stats|report)',
            r'how\s+many\s+tasks\s+(completed|finished)',
            r'completion\s+rate',
            r'weekly\s+(summary|report)',
        ]
        
        # Email generation patterns
        self.email_patterns = [
            r'write\s+(an?\s+)?email',
            r'send\s+(an?\s+)?email',
            r'compose\s+(an?\s+)?email',
            r'email\s+(my\s+)?manager',
            r'sick\s+leave\s+(request|email)',
            r'(pto|vacation)\s+(request|email)',
        ]
        
        # Complex update indicators (need LLM rephrasing)
        self.complex_update_indicators = [
            r'\b(tested|testing|fixed|fixing|implemented|working on)\b',
            r'\b(waiting for|blocked by|pending)\b',
            r'\b(staging|production|deployment)\b',
            r'\b(issue|bug|problem|error)\b',
            r'\b(review|approval|qa|quality)\b',
        ]
    
    def classify(self, user_input: str) -> ClassificationResult:
        """
        Main classification method - determines routing decision
        """
        user_input_lower = user_input.lower().strip()
        
        # Check for simple completions first (highest confidence)
        for pattern in self.completion_patterns:
            if re.search(pattern, user_input_lower, re.IGNORECASE):
                return ClassificationResult(
                    route_type=RouteType.BACKEND_COMPLETION,
                    confidence=0.95,
                    matched_pattern=pattern
                )
        
        # Check for productivity queries
        for pattern in self.productivity_patterns:
            if re.search(pattern, user_input_lower, re.IGNORECASE):
                return ClassificationResult(
                    route_type=RouteType.BACKEND_PRODUCTIVITY,
                    confidence=0.90,
                    matched_pattern=pattern
                )
        
        # Check for email requests
        for pattern in self.email_patterns:
            if re.search(pattern, user_input_lower, re.IGNORECASE):
                return ClassificationResult(
                    route_type=RouteType.LLM_EMAIL,
                    confidence=0.85,
                    matched_pattern=pattern
                )
        
        # Check if it's a complex update (needs rephrasing)
        complex_matches = 0
        for pattern in self.complex_update_indicators:
            if re.search(pattern, user_input_lower, re.IGNORECASE):
                complex_matches += 1
        
        # If multiple complex indicators or long text, route to LLM
        if complex_matches >= 2 or len(user_input) > 50:
            return ClassificationResult(
                route_type=RouteType.LLM_REPHRASING,
                confidence=0.80,
                matched_pattern=f"complex_indicators_{complex_matches}"
            )
        
        # Default: send to LLM for classification (ambiguous cases)
        return ClassificationResult(
            route_type=RouteType.LLM_CLASSIFICATION,
            confidence=0.60,
            matched_pattern="ambiguous"
        )
    
    def extract_task_info(self, user_input: str) -> Dict:
        """
        Extract task-related information from user input
        """
        entities = {}
        
        # Extract task numbers (e.g., "task #123", "JIRA-456")
        task_pattern = r'\b(?:task\s*#?|[A-Z]+-)\s*(\d+)\b'
        task_matches = re.findall(task_pattern, user_input, re.IGNORECASE)
        if task_matches:
            entities['task_ids'] = task_matches
        
        # Extract completion status keywords
        completion_keywords = re.findall(r'\b(done|completed|finished|pending|blocked|testing)\b', 
                                       user_input, re.IGNORECASE)
        if completion_keywords:
            entities['status_keywords'] = completion_keywords
        
        return entities
    
    
print("Loaded intent_classifier.py successfully. Contents:", dir())
