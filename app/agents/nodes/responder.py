import logfire
from ..state import AgentState
from .planner import get_groq_client  # reuse the same client, don't reinstantiate
from app.config import GROQ_MODEL


def _build_context(documents: list[dict]) -> str:
    if not documents:
        return ""
    parts = []
    for i, doc in enumerate(documents, 1):
        source = doc["metadata"].get("source_file", "unknown")
        parts.append(f"[{i}] (source: {source})\n{doc['text']}")
    return "\n\n".join(parts)


def responder_node(state: AgentState) -> AgentState:
    with logfire.span("💬 Responder node", query_type=state["query_type"]):
        client = get_groq_client()
        documents = state.get("documents", [])

        if state["query_type"] == "conversational":
            system_prompt = "You are a helpful assistant. Respond naturally and briefly."
            user_content = state["current_query"]
        else:
            context = _build_context(documents)
            system_prompt = (
                "You are a professional Kubernetes and technical expret. You only have to answer queries that are related to kubernetes and networking."
                "If any query is not related to Kubernetes directly or indirectly, dont answer say: I am kubernetes assistant i cant help you with that."
                "Otherwise ignore the context and say i am not sure or any answer that is professional to say no."
                "Answer the user's question using ONLY the provided context. "
                "If the context doesn't contain the answer, say so — don't invent one."
                "Examples: 1. Tell me a joke? Say i cant"
                "Examples: 2. How to increase creativity in LLM? Say i cant"
                "Examples: 3. Write me a pytohn script that is a calculator? Say i cant. For your context: This is technical but not related to kubernetes."
            )
            user_content = f"Context:\n{context}\n\nQuestion: {state['current_query']}"

        response = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
            temperature=0.3,
        )

        answer = response.choices[0].message.content
        logfire.info(
            "Responder generated answer",
            query=state["current_query"],
            query_type=state["query_type"],
            n_docs_used=len(documents),
            answer=answer,
        )

        state["final_answer"] = answer
        state["plan"] = state.get("plan", []) + ["responder"]
        state["status"] = "complete"
        return state