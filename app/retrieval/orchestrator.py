import logfire
# from ingestion.embedding.qdrant_setup import get_qdrant_client
from app.ingestion.embedding.qdrant_setup import get_qdrant_client
from app.retrieval.embed_query import embed_query
from app.retrieval.vector_search import search_vectors
from app.retrieval.rerank import rerank_chunks

def search(query: str, top_k: int = 25, use_reranker: bool = True, top_n: int = 5) -> list[dict]:
    with logfire.span("🔎 Retrieval", query=query, top_k=top_k, use_reranker=use_reranker):
        client = get_qdrant_client()
        query_vector = embed_query(query)
        candidates = search_vectors(client, query_vector, top_k=top_k)

        if use_reranker:
            return rerank_chunks(query, candidates, top_n=top_n)
        return candidates[:top_n]