import logfire
from nemoguardrails import LLMRails, RailsConfig

_rails = None


def get_rails() -> LLMRails:
    global _rails
    if _rails is None:
        config = RailsConfig.from_path("guardrails/config")
        _rails = LLMRails(config)
    return _rails


async def check_input(query: str) -> tuple[bool, str | None]:
    """
    Runs ONLY input rails (jailbreak check, off-topic, sensitive-topic, sensitive
    data masking) — dialog/output/retrieval are disabled, so this never triggers
    NeMo's own LLM to generate an actual answer. It either echoes the input back
    unchanged (allowed), returns an altered version (e.g. PII masked), or returns
    a refusal message (blocked).
    """
    rails = get_rails()
    with logfire.span("🛡️ NeMo input rails", query=query):
        result = await rails.generate_async(
            messages=[{"role": "user", "content": query}],
            options={"rails": {"dialog": False, "output": False, "retrieval": False}},
        )
        response_text = result.response[0]["content"] if hasattr(result, "response") else result["content"]

        # NeMo doesn't give a clean boolean flag here — a blocked input returns
        # its configured refusal message verbatim. Comparing against known refusal
        # strings is brittle; the more reliable path (once verified) is checking
        # result.log.activated_rails for a rail that returned "blocked" / stop.
        # Using text comparison as a stopgap — replace once you've inspected
        # result.log.activated_rails on a real blocked case.
        was_blocked = response_text != query and "I can't" in response_text

        if was_blocked:
            logfire.warning("Input blocked by NeMo rails", query=query, refusal=response_text)
            return False, response_text

        if response_text != query:
            logfire.info("Input altered by NeMo rails (e.g. PII masked)", original=query, altered=response_text)

        return True, response_text  # response_text may be the masked/altered version — use THIS downstream, not the raw query


async def check_output(bot_message: str) -> tuple[bool, str]:
    """
    Runs ONLY output rails against an already-generated response (from your
    LangGraph responder, not NeMo's own LLM). Input/dialog/retrieval disabled.
    """
    rails = get_rails()
    with logfire.span("🛡️ NeMo output rails", response_preview=bot_message[:100]):
        result = await rails.generate_async(
            messages=[
                {"role": "user", "content": ""},
                {"role": "assistant", "content": bot_message},
            ],
            options={"rails": {"input": False, "dialog": False, "retrieval": False}},
        )
        response_text = result.response[0]["content"] if hasattr(result, "response") else result["content"]

        was_blocked = response_text != bot_message and "withheld" in response_text.lower()

        if was_blocked:
            logfire.warning("Output blocked/altered by NeMo rails")

        return not was_blocked, response_text