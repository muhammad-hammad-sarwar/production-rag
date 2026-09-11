import logfire
from groq import Groq
from ..state import AgentState
from app.config import GROQ_API_KEY, GROQ_MODEL

_client = None

def get_groq_client():
    global _client
    if _client is None:
        api_key = GROQ_API_KEY
        if not api_key:
            raise RuntimeError("Missing GROQ_API_KEY env var")
        _client = Groq(api_key=api_key)
    return _client


PLANNER_PROMPT = """Classify the user's latest message as either "conversational" or "technical".
"conversational": greetings, small talk, chit-chat, vague follow-ups needing no document lookup.
"technical": questions that need factual/document-grounded answers.
Respond with exactly one word: conversational or technical. If the related documents are not related to kubernetes or networkin, make it conversational."""


def planner_node(state: AgentState) -> AgentState:
    with logfire.span("🧭 Planner node", query=state["current_query"]):
        client = get_groq_client()
        response = client.chat.completions.create(
            model=GROQ_MODEL,  # verify this model name is still live on Groq before relying on it
            messages=[
                {"role": "system", "content": PLANNER_PROMPT},
                {"role": "user", "content": state["current_query"]},
            ],
            temperature=0,
            max_tokens=10,
        )
        classification = response.choices[0].message.content.strip().lower()
        query_type = "conversational" if "conversational" in classification else "technical"

        logfire.info(f"Planner classified query as: {query_type}", query=state["current_query"])

        state["query_type"] = query_type
        state["plan"] = state.get("plan", []) + ["planner"]
        state["status"] = "planner_complete"
        return state