import logfire
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.sqlite import SqliteSaver
import sqlite3
from .state import AgentState
from .nodes.planner import planner_node
from .nodes.retriever import retriever_node
from .nodes.responder import responder_node
from app.config import LOGFIRE_TOKEN

logfire.configure(token=LOGFIRE_TOKEN, environment="development", service_name="enterprise-ingestion-service")
def route_after_planner(state: AgentState) -> str:
    decision = "retriever" if state["query_type"] == "technical" else "responder"
    logfire.info(f"Routing after planner: {decision}", query_type=state["query_type"])
    return decision


def build_graph():
    graph = StateGraph(AgentState)

    graph.add_node("planner", planner_node)
    graph.add_node("retriever", retriever_node)
    graph.add_node("responder", responder_node)

    graph.set_entry_point("planner")
    graph.add_conditional_edges("planner", route_after_planner, {
        "retriever": "retriever",
        "responder": "responder",
    })
    graph.add_edge("retriever", "responder")
    graph.add_edge("responder", END)

    checkpointer = SqliteSaver(sqlite3.connect("checkpoints.db", check_same_thread=False))
    return graph.compile(checkpointer=checkpointer)


def run_query(query: str, thread_id: str = "default") -> dict:
    app = build_graph()
    config = {"configurable": {"thread_id": thread_id}}

    with logfire.span("🚀 Agent run", query=query, thread_id=thread_id):
        result = app.invoke(
            {
                "messages": [],
                "current_query": query,
                "plan": [],
                "status": "starting",
                "query_type": None,
                "documents": [],
                "final_answer": None,
            },
            config=config,
        )
        logfire.info(f"Run complete: plan={result['plan']}", final_answer=result["final_answer"])
        return result