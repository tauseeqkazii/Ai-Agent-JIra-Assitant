Each submodule is responsible for a specific layer in the AI engine's processing pipeline — from interpreting user intent to generating the final AI response.

---

## 🧩 Module Breakdown

### 1. `classification/`

**Purpose:** Detects the intent, route, or task type of a user message before it reaches the model.  
This enables efficient routing (e.g., summarization, ticket creation, query answering, etc.) and prevents unnecessary LLM calls.

**Typical files inside:**

- `intent_classifier.py` — Uses regex, keyword patterns, or lightweight ML models to determine user intent.
- `router.py` — Maps intents to specific pipelines or response strategies.
- `__init__.py` — Module initializer.

**Example Flow:**

```python
intent = IntentClassifier.predict("Create a Jira ticket for bug fix")
# Output: "ticket_creation"
```
