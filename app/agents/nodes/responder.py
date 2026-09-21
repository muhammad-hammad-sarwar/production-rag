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

        system_prompt = f"""
            You are a helpful Kubernetes Assistant - Kube.
            You only help people with Technical issues.
        """
        
        if state["query_type"] == "conversational":
            user_content = state["current_query"]
        else:
            context = _build_context(documents)
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