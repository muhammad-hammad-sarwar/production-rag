import uuid
import logfire
import streamlit as st
from dotenv import load_dotenv

from app.agents.graph import run_query
from app.ingestion.embedding.qdrant_setup import get_qdrant_client
import app.config as config

load_dotenv()

logfire.configure(service_name="enterprise-rag-streamlit")

st.set_page_config(page_title="RAG Assistant", page_icon="🔍")


# ---- Session / thread management ----
# One Streamlit session = one thread_id = one conversation, generated once
# and held in st.session_state so reruns (which Streamlit does constantly)
# don't spawn a new thread_id every keystroke.
if "thread_id" not in st.session_state:
    st.session_state.thread_id = str(uuid.uuid4())

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []  # list of {"role": "user"|"assistant", "content": str}


# ---- Sidebar: service/key status ----
def check_service_status() -> dict:
    """Presence checks for API keys (cheap, no network call), plus one live
    reachability check for Qdrant (also cheap, local). Does NOT ping Groq
    live — that costs quota on every sidebar render, which Streamlit does
    on nearly every interaction. Flag if you want that added anyway."""
    status = {}

    required_keys = {
        "GROQ_API_KEY": getattr(config, "GROQ_API_KEY", None),
        "QDRANT_ENDPOINT": getattr(config, "QDRANT_ENDPOINT", None),
        "LOGFIRE_TOKEN": getattr(config, "LOGFIRE_TOKEN", None),
        "HF_TOKEN": getattr(config, "HF_TOKEN", None),
    }

    for key_name, value in required_keys.items():
        status[key_name] = bool(value)

    try:
        client = get_qdrant_client()
        client.get_collections()
        status["Qdrant connection"] = True
    except Exception as e:
        status["Qdrant connection"] = False
        logfire.warning(f"Sidebar Qdrant check failed: {e}")

    return status


with st.sidebar:
    st.subheader("Service status")
    statuses = check_service_status()
    for name, ok in statuses.items():
        if ok:
            st.success(f"{name}: OK")
        else:
            st.error(f"{name}: missing or unreachable")

    st.divider()
    st.caption(f"Session thread ID: `{st.session_state.thread_id}`")

    if st.button("Start new conversation"):
        st.session_state.thread_id = str(uuid.uuid4())
        st.session_state.chat_history = []
        st.rerun()


# ---- Main chat UI ----
st.title("🔍 RAG Assistant")

for msg in st.session_state.chat_history:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])

query = st.chat_input("Ask a question...")

if query:
    st.session_state.chat_history.append({"role": "user", "content": query})
    with st.chat_message("user"):
        st.write(query)

    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            try:
                with logfire.span("💬 Streamlit query", query=query, thread_id=st.session_state.thread_id):
                    result = run_query(query, thread_id=st.session_state.thread_id)
                answer = result["final_answer"]
            except Exception as e:
                logfire.error(f"Streamlit query failed: {e}", query=query)
                answer = "Something went wrong processing that query. Check the logs."

        st.write(answer)

    st.session_state.chat_history.append({"role": "assistant", "content": answer})