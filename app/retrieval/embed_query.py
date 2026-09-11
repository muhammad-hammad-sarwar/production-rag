from app.ingestion.embedding.model import get_model

def embed_query(query: str) -> list[float]:
    model = get_model()
    return model.encode(query, normalize_embeddings=True).tolist()