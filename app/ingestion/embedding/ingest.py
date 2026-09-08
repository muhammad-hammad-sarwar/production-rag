import logfire
from app.ingestion.embedding.model import embed_texts
from app.ingestion.embedding.checkpoint import load_checkpoint, save_checkpoint

BATCH_SIZE = 64  # CPU-bound now, not rate-limit-bound — tune for your RAM/CPU, not an API limit

def process_chunks_to_qdrant(chunks: list[dict], qdrant_client, collection_name: str):
    embedded_ids = load_checkpoint()
    pending = [c for c in chunks if c["id"] not in embedded_ids]
    logfire.info(f"{len(pending)}/{len(chunks)} chunks pending ({len(embedded_ids)} already done)")

    for i in range(0, len(pending), BATCH_SIZE):
        batch = pending[i:i + BATCH_SIZE]
        vectors = embed_texts([c["text"] for c in batch])  # local — no try/except needed for rate limits

        points = [
            {"id": chunk["id"], "vector": vector, "payload": {"text": chunk["text"], **chunk["metadata"]}}
            for chunk, vector in zip(batch, vectors)
        ]
        qdrant_client.upsert(collection_name=collection_name, points=points)

        embedded_ids.update(c["id"] for c in batch)
        save_checkpoint(embedded_ids)  # after every batch — this is what actually prevents re-embedding
        logfire.info(f"Upserted batch {i // BATCH_SIZE + 1}/{(len(pending) - 1) // BATCH_SIZE + 1}")