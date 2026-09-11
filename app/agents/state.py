from typing import TypedDict, Literal
from langchain_core.messages import BaseMessage


class AgentState(TypedDict):
    messages: list[BaseMessage]          # full conversation history (LangGraph checkpointer persists this)
    current_query: str
    plan: list[str]                       # nodes executed so far, e.g. ["planner", "retriever"]
    status: str                           # which node is currently active
    query_type: Literal["conversational", "technical"] | None
    documents: list[dict]                 # reranked chunks from retrieval, empty if skipped
    final_answer: str | None