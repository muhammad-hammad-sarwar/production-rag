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


PLANNER_PROMPT = """
You are a senior Kubernetes Engineer. You can catch if someone is actually talking about kubernetes/devops or not.
Even if the question is technical but in any way not related to Kubernetes or networking or devops, mark it conversational.
If they are asking something random, examples given:
    1. Hi, how can i make a tea? ""Answer"": "conversational"
    2. How to autoscale pods? ""Answer"": "technical"
    3. What is last question that is asked? ""Answer"": "conversational"
    4. tell me a jobs ""Answer"": "conversational"
Expected Answer: "conversational" or "technical".
"""


def planner_node(state: AgentState) -> AgentState:
    with logfire.span("🧭 Planner node", query=state["current_query"]):
        client = get_groq_client()
        response = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {"role": "system", "content": PLANNER_PROMPT},
                {"role": "user", "content": state["current_query"]},
            ],
            temperature=0,
            max_tokens=100,
            # this was a huge issue because i was not able to get conversational and each query was marked as technical
        )
        classification = response.choices[0].message.content.strip().lower()
        query_type = "technical" if "technical" in classification else "conversational"

        logfire.info(f"Planner classified query as: {query_type}", query=state["current_query"])

        state["query_type"] = query_type
        state["plan"] = state.get("plan", []) + ["planner"]
        state["status"] = "planner_complete"
        return state