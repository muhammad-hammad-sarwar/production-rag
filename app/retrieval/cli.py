import argparse
import json
from app.retrieval.orchestrator import search

def main():
    parser = argparse.ArgumentParser(description="Query the RAG retrieval pipeline")
    parser.add_argument("query", type=str, help="The search query")
    parser.add_argument("--top-k", type=int, default=25, help="Candidates fetched from vector search")
    parser.add_argument("--top-n", type=int, default=5, help="Final results returned after reranking")
    parser.add_argument("--no-rerank", action="store_true", help="Skip reranking, return raw vector search order")
    args = parser.parse_args()

    results = search(
        query=args.query,
        top_k=args.top_k,
        use_reranker=not args.no_rerank,
        top_n=args.top_n,
    )

    for i, r in enumerate(results, 1):
        score_key = "rerank_score" if "rerank_score" in r else "score"
        print(f"\n[{i}] score={r[score_key]:.4f} source={r['metadata'].get('source_file')}")
        print(r["text"][:300])

if __name__ == "__main__":
    main()