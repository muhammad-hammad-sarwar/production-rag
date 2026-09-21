import logfire
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.sqlite import SqliteSaver
import sqlite3
from .state import AgentState
from .nodes.planner import planner_node
from .nodes.retriever import retriever_node
from .nodes.responder import responder_node
from app.config import LOGFIRE_TOKEN

logfire.configure(token=LOGFIRE_TOKEN, environment="development", service_name="enterprise-agent-service")


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


_APP = build_graph()  # built once at import time, not per-request

def run_query(query: str, thread_id: str = "default") -> dict:
    config = {"configurable": {"thread_id": thread_id}}
    with logfire.span("🚀 Agent run", query=query, thread_id=thread_id):
        result = _APP.invoke(
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

async def run_query_with_guardrails(query: str, thread_id: str = "default") -> dict:
    from app.guardrails.rails_app import check_input, check_output
    from app.guardrails.config.actions import check_secrets_input, check_secrets_output, check_urgency

    with logfire.span("🛡️ Guardrails: input", query=query, thread_id=thread_id):
        secrets_ok = await check_secrets_input({"user_message": query})
        if not secrets_ok:
            return {"status": "blocked", "plan": ["guardrails_secrets"], "query_type": None,
                    "final_answer": "I can't process that — it looks like it contains sensitive information."}

        input_ok, checked_query = await check_input(query)
        await check_urgency({"user_message": query})
        if not input_ok:
            return {"status": "blocked", "plan": ["guardrails_input"], "query_type": None, "final_answer": checked_query}

    result = run_query(checked_query, thread_id=thread_id)  # use checked_query, not raw query — carries PII masking through

    with logfire.span("🛡️ Guardrails: output", thread_id=thread_id):
        secrets_out_ok = await check_secrets_output({"bot_message": result.get("final_answer", "")})
        if not secrets_out_ok:
            result["final_answer"] = "Response withheld — contained sensitive information."
            result["status"] = "output_blocked"
        else:
            output_ok, checked_answer = await check_output(result.get("final_answer", ""))
            result["final_answer"] = checked_answer
            if not output_ok:
                result["status"] = "output_blocked"

    return result