# from src.ai_engine.main import process_message

# # Test comment rephrasing
# result = process_message(
#     "fixed the api bug, tested it works fine now",
#     {"user_id": "test123", "role": "developer"}
# )

# print(f"Original: fixed the api bug, tested it works fine now")
# print(f"Professional: {result['generated_content']}")
# print(f"Quality Score: {result.get('quality_score', 'N/A')}")
# print(f"Requires Approval: {result.get('requires_user_approval')}")

# # Test email generation
# result2 = process_message(
#     "write email for sick leave tomorrow",
#     {
#         "user_id": "test123",
#         "user_name": "John Doe",
#         "manager_name": "Jane Smith"
#     }
# )

# print(f"\n--- Email Generated ---")
# print(result2['generated_content'])
from src.ai_engine.main import process_message

print("=== Jira AI Assistant Interactive Mode ===")
print("Type 'exit' to quit.\n")

while True:
    # Get user input
    task_input = input("Enter a task or email request: ").strip()
    
    if task_input.lower() == "exit":
        print("Exiting...")
        break

    # Optional: you can ask for extra info for emails
    user_name = input("Your name (leave blank if not applicable): ").strip()
    manager_name = input("Manager's name (leave blank if not applicable): ").strip()

    # Build context for AI
    context = {"user_id": "interactive_user"}
    if user_name:
        context["user_name"] = user_name
    if manager_name:
        context["manager_name"] = manager_name

    # Process the input
    result = process_message(task_input, context)

    # Print result
    if "email" in result.get("type", "").lower():
        print("\n--- Email Generated ---")
    else:
        print("\n--- Jira Comment Rephrased ---")
    
    print(result["generated_content"])
    print(f"Quality Score: {result.get('quality_score', 'N/A')}")
    print(f"Requires Approval: {result.get('requires_user_approval', 'N/A')}")
    print("\n" + "="*50 + "\n")
