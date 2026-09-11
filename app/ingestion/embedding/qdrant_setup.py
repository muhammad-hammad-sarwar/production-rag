import os
from qdrant_client import QdrantClient
from qdrant_client.models import VectorParams, Distance
from app.config import QDRANT_ENDPOINT, QDRANT_API_KEY

EMBEDDING_DIM = 384
COLLECTION_NAME = "embeddings"

def get_qdrant_client() -> QdrantClient:
    url = QDRANT_ENDPOINT
    if not url:
        raise RuntimeError("Missing QDRANT_ENDPOINT env var")
    return QdrantClient(url=url, api_key=QDRANT_API_KEY or None)

def ensure_collection(client: QdrantClient, collection_name: str = COLLECTION_NAME, dim: int = EMBEDDING_DIM):
    if client.collection_exists(collection_name):
        existing_dim = client.get_collection(collection_name).config.params.vectors.size
        if existing_dim != dim:
            raise RuntimeError(
                f"'{collection_name}' exists with dim={existing_dim}, current model needs dim={dim}. "
                f"Mixing dims in one collection corrupts search — pick a new name or recreate deliberately."
            )
        return
    client.create_collection(
        collection_name=collection_name,
        vectors_config=VectorParams(size=dim, distance=Distance.COSINE),
    )