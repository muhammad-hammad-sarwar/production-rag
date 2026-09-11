import logfire
from ..state import AgentState
from app.retrieval.orchestrator import search

def retriever_node(state: AgentState) -> AgentState:
    with logfire.span("🔍 Retriever node", query=state["current_query"]):
        results = search(
            query=state["current_query"],
            top_k=25,
            use_reranker=True,
            top_n=5,
        )

        logfire.info(
            f"Retrieved {len(results)} reranked docs",
            query=state["current_query"],
            sources=[r["metadata"].get("source_file") for r in results],
        )

        state["documents"] = results
        state["plan"] = state.get("plan", []) + ["retriever"]
        state["status"] = "retriever_complete"
        return state