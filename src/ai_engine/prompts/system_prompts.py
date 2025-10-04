"""
System Prompts Module
Contains all AI prompt templates with optimized token usage
"""


class SystemPrompts:
    """
    Centralized prompt templates for different AI tasks
    Optimized for token efficiency while maintaining quality
    """
    
    # =========================================================================
    # JIRA COMMENT REPHRASER (Optimized: ~85 tokens, was ~150)
    # =========================================================================
    JIRA_COMMENT_REPHRASER = """Convert casual task updates to professional Jira comments.

Rules:
- Be concise and professional
- Present tense for completed work, future for pending
- Keep technical details and meaning
- Never add info not in original
- Only mark complete if user says "done/finished/completed"

Examples:
"fixed button bug, tested staging" → "Resolved button alignment issue. Testing completed on staging environment."
"working on login" → "Currently investigating login functionality."
"done with API" → "API endpoint implementation completed."

Convert this update:"""

    # =========================================================================
    # EMAIL GENERATOR (Optimized: ~110 tokens, was ~200)
    # =========================================================================
    EMAIL_GENERATOR = """Write professional business emails based on user requests.

Format: Subject line, greeting, body, closing

Rules:
- Use placeholders for unknown info: [Manager Name], [Date], [Your Name]
- Match tone to recipient (formal for managers)
- Be concise but complete
- Always include proper subject and closing

Example:
Request: "sick leave tomorrow"
Output:
Subject: Sick Leave Request - [Date]

Dear [Manager Name],

I am unable to work tomorrow due to illness. I will monitor emails and address urgent matters remotely if possible.

Thank you for understanding.

Best regards,
[Your Name]

Write this email:"""

    # =========================================================================
    # CLASSIFICATION HELPER (Optimized: ~95 tokens, was ~140)
    # =========================================================================
    CLASSIFICATION_HELPER = """You are a Jira assistant intent classifier. Determine what the user wants to do.

Possible intents:
- task_completion: Mark task done
- task_update: Update progress
- productivity_query: Ask about stats
- email_request: Write an email
- general_question: Other questions
- unclear: Ambiguous request

CRITICAL: Return ONLY valid JSON, no markdown, no extra text.

Format:
{
  "intent": "task_completion",
  "confidence": 0.9,
  "extracted_info": {"task_id": "123"},
  "user_friendly_response": "I understand you want to mark task 123 as complete."
}

Classify:"""

    # =========================================================================
    # HELPER METHOD: Build Context-Aware Prompts
    # =========================================================================
    
    @staticmethod
    def build_comment_prompt_with_context(
        user_role: str = None,
        project_type: str = None,
        task_type: str = None
    ) -> str:
        """
        Build context-aware comment rephrasing prompt
        
        Args:
            user_role: User's role (e.g., "Senior Engineer")
            project_type: Type of project (e.g., "Mobile App")
            task_type: Type of task (e.g., "Bug Fix")
            
        Returns:
            Prompt with added context
        """
        base_prompt = SystemPrompts.JIRA_COMMENT_REPHRASER
        
        context_parts = []
        if user_role:
            context_parts.append(f"User role: {user_role}")
        if project_type:
            context_parts.append(f"Project: {project_type}")
        if task_type:
            context_parts.append(f"Task type: {task_type}")
        
        if context_parts:
            context = "\nContext: " + ", ".join(context_parts)
            return base_prompt + context
        
        return base_prompt
    
    @staticmethod
    def build_email_prompt_with_context(
        user_name: str = None,
        manager_name: str = None,
        department: str = None
    ) -> str:
        """
        Build context-aware email generation prompt
        
        Args:
            user_name: User's name
            manager_name: Manager's name
            department: User's department
            
        Returns:
            Prompt with added context
        """
        base_prompt = SystemPrompts.EMAIL_GENERATOR
        
        context_parts = []
        if user_name:
            context_parts.append(f"From: {user_name}")
        if manager_name:
            context_parts.append(f"To: {manager_name}")
        if department:
            context_parts.append(f"Department: {department}")
        
        if context_parts:
            context = "\nContext: " + ", ".join(context_parts)
            return base_prompt + context
        
        return base_prompt
    
    # =========================================================================
    # VALIDATION PROMPTS (New: For response validation)
    # =========================================================================
    
    VALIDATE_PROFESSIONAL_TONE = """Rate the professionalism of this text on a scale of 0.0 to 1.0.

Consider:
- Professional vocabulary
- Appropriate tone
- Grammar and spelling
- Clarity and conciseness

Text: {text}

Return only a number between 0.0 and 1.0."""

    # =========================================================================
    # METADATA
    # =========================================================================
    
    PROMPT_VERSION = "2.0"
    LAST_UPDATED = "2025-01-09"
    
    @classmethod
    def get_all_prompts(cls) -> dict:
        """Get all available prompts"""
        return {
            "comment_rephraser": cls.JIRA_COMMENT_REPHRASER,
            "email_generator": cls.EMAIL_GENERATOR,
            "classification_helper": cls.CLASSIFICATION_HELPER,
            "validate_tone": cls.VALIDATE_PROFESSIONAL_TONE
        }
    
    @classmethod
    def get_prompt_stats(cls) -> dict:
        """Get statistics about prompt token usage"""
        import tiktoken
        
        try:
            # Use tiktoken to count tokens (GPT-4 encoding)
            encoding = tiktoken.encoding_for_model("gpt-4")
            
            stats = {}
            for name, prompt in cls.get_all_prompts().items():
                token_count = len(encoding.encode(prompt))
                stats[name] = {
                    "characters": len(prompt),
                    "estimated_tokens": token_count
                }
            
            return stats
        except Exception as e:
            # If tiktoken not available, use rough estimate
            return {
                name: {
                    "characters": len(prompt),
                    "estimated_tokens": len(prompt) // 4  # Rough estimate
                }
                for name, prompt in cls.get_all_prompts().items()
            }