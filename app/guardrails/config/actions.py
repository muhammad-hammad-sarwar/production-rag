import re
import logfire
from nemoguardrails.actions import action

SECRET_PATTERNS = {
    "openai_key": re.compile(r"sk-[A-Za-z0-9]{20,}"),
    "groq_key": re.compile(r"gsk_[A-Za-z0-9]{20,}"),
    "generic_api_key": re.compile(r"(?i)(api[_-]?key|secret|token)\s*[:=]\s*['\"]?[A-Za-z0-9_\-]{16,}"),
    "aws_key": re.compile(r"AKIA[0-9A-Z]{16}"),
}

PIN_CONTEXT_PATTERN = re.compile(r"(?i)(pin|password|passcode|security code)\D{0,10}\d{4,6}")

URGENCY_MARKERS = ["urgent", "immediately", "right now", "emergency", "asap", "compromised"]


@action(name="check secrets input")
async def check_secrets_input(context: dict) -> bool:
    text = context.get("user_message", "")
    for name, pattern in SECRET_PATTERNS.items():
        if pattern.search(text):
            logfire.warning(f"Input blocked: secret pattern '{name}' detected")
            return False  # False = block
    return True


@action(name="check secrets output")
async def check_secrets_output(context: dict) -> bool:
    text = context.get("bot_message", "")
    for name, pattern in SECRET_PATTERNS.items():
        if pattern.search(text):
            logfire.warning(f"Output blocked: secret pattern '{name}' detected in generated response")
            return False
    return True


@action(name="check urgency")
async def check_urgency(context: dict) -> bool:
    text = context.get("user_message", "").lower()
    if any(marker in text for marker in URGENCY_MARKERS):
        logfire.info("Urgency detected in query", query=text)
    return True  # informational only — doesn't block, just logs; wire a real downstream action once you decide what urgency should trigger