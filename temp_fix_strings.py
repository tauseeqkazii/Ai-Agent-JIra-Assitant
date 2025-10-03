from pathlib import Path

path = Path('src/ai_engine/models/model_manager.py')
text = path.read_text()

old = "        if \"email request\" in message_lower:\n            request = user_message.split(\"Email request:\", 1)[-1].strip()\n            subject = self._compose_stub_subject(request)\n            return (\n                f\"Subject: {subject}\r\n\r\n\n\"\n                \"Dear Team,\r\n\r\n\n\"\n                f\"This is a placeholder email responding to the request: {request}.\r\n\n\"\n                \"It demonstrates the email format without contacting the OpenAI API.\r\n\r\n\n\"\n                \"Best regards,\r\n\n\"\n                \"AI Assistant\"\n            )\n\n        if \"user update:\" in message_lower:\n            update = user_message.split(\"User update:\", 1)[-1].strip()\n            return (\n                f\"Resolved: {update}.\r\n\n\"\n                \"Next steps: Continue monitoring progress and provide follow-up detail.\"\n            )\n"

new = "        if \"email request\" in message_lower:\n            request = user_message.split(\"Email request:\", 1)[-1].strip()\n            subject = self._compose_stub_subject(request)\n            return (\n                f\"Subject: {subject}\\n\\n\"\n                \"Dear Team,\\n\\n\"\n                f\"This is a placeholder email responding to the request: {request}.\\n\"\n                \"It demonstrates the email format without contacting the OpenAI API.\\n\\n\"\n                \"Best regards,\\n\"\n                \"AI Assistant\"\n            )\n\n        if \"user update:\" in message_lower:\n            update = user_message.split(\"User update:\", 1)[-1].strip()\n            return (\n                f\"Resolved: {update}.\\n\"\n                \"Next steps: Continue monitoring progress and provide follow-up detail.\"\n            )\n"

if old not in text:
    raise SystemExit('pattern not found')

path.write_text(text.replace(old, new), encoding='utf-8')
