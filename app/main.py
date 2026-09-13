import logfire
from fastapi import FastAPI, HTTPException
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel, Field
from dotenv import load_dotenv
from .config import LOGFIRE_TOKEN, ENVIRONMENT

from .agents.graph import run_query
from .ingestion.embedding.qdrant_setup import get_qdrant_client

load_dotenv()

logfire.configure(
    token=LOGFIRE_TOKEN,
    environment=ENVIRONMENT,
    service_name="enterprise-rag-api",
)

app = FastAPI(title="Enterprise RAG API")
logfire.instrument_fastapi(app)  # auto-traces every request, nests your existing spans underneath — this IS your waterfall


class QueryRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=2000)
    thread_id: str = Field(default="default", description="Conversation session ID for memory persistence")


class QueryResponse(BaseModel):
    answer: str
    status: str
    plan: list[str]
    query_type: str | None


@app.post("/query", response_model=QueryResponse)
async def query_endpoint(request: QueryRequest):
    with logfire.span("📨 /query request", query=request.query, thread_id=request.thread_id):
        try:
            result = await run_in_threadpool(run_query, request.query, request.thread_id)
        except Exception as e:
            logfire.error(f"Query pipeline failed: {e}", query=request.query, thread_id=request.thread_id)
            raise HTTPException(status_code=500, detail="Failed to process query. Check server logs for details.")

        if not result.get("final_answer"):
            logfire.warning("Pipeline completed but produced no answer", query=request.query)
            raise HTTPException(status_code=500, detail="Pipeline completed without generating an answer.")

        return QueryResponse(
            answer=result["final_answer"],
            status=result["status"],
            plan=result["plan"],
            query_type=result.get("query_type"),
        )


@app.get("/health")
async def health_check():
    """Checks actual downstream dependencies, not just 'the process is running.'
    A health check that only confirms the FastAPI process is alive is close to
    useless — Qdrant being unreachable is a real failure mode this needs to catch."""
    checks = {"qdrant": False}

    try:
        client = get_qdrant_client()
        client.get_collections()  # cheap call that proves the connection actually works
        checks["qdrant"] = True
    except Exception as e:
        logfire.warning(f"Health check: Qdrant unreachable: {e}")

    healthy = all(checks.values())
    status_code = 200 if healthy else 503

    from fastapi.responses import JSONResponse
    return JSONResponse(
        status_code=status_code,
        content={"status": "healthy" if healthy else "degraded", "checks": checks},
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)