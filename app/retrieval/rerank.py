import logfire
from flashrank import Ranker, RerankRequest

_ranker = None

def get_ranker():
    global _ranker
    if _ranker is None:
        _ranker = Ranker(model_name="ms-marco-MiniLM-L-12-v2")  # flashrank's default lightweight cross-encoder
    return _ranker


def rerank_chunks(query: str, chunks: list[dict], top_n: int) -> list[dict]:
    if not chunks:
        return chunks

    with logfire.span("📊 Reranking", n_candidates=len(chunks), top_n=top_n):
        ranker = get_ranker()
        passages = [{"id": c["id"], "text": c["text"]} for c in chunks]
        request = RerankRequest(query=query, passages=passages)
        reranked = ranker.rerank(request)  # returns list sorted by relevance, each with "id" and "score"

        by_id = {c["id"]: c for c in chunks}
        result = []
        for r in reranked[:top_n]:
            chunk = dict(by_id[r["id"]])
            chunk["rerank_score"] = float(r["score"])
            result.append(chunk)

        logfire.info(f"Reranked to top {len(result)}")
        return result