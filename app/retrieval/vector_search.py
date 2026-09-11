import logfire
from qdrant_client import QdrantClient
from app.ingestion.embedding.qdrant_setup import COLLECTION_NAME

def search_vectors(client: QdrantClient, query_vector: list[float], top_k: int, collection_name: str = COLLECTION_NAME) -> list[dict]:
    with logfire.span("🔍 Vector search", top_k=top_k):
        response = client.query_points(
            collection_name=collection_name,
            query=query_vector,
            limit=top_k,
            with_payload=True,
        )

        results = response.points

        chunks = [
            {
                "id": r.id,
                "score": r.score,
                "text": r.payload.get("text", ""),
                "metadata": {k: v for k, v in r.payload.items() if k != "text"},
            }
            for r in results
        ]
        logfire.info(f"Retrieved {len(chunks)} candidates")
        return chunks