import argparse
from .graph import run_query

def main():
    parser = argparse.ArgumentParser(description="Query the RAG agent")
    parser.add_argument("query", type=str)
    parser.add_argument("--thread-id", type=str, default="default", help="Conversation session ID for memory persistence")
    args = parser.parse_args()

    result = run_query(args.query, thread_id=args.thread_id)
    print(f"\n[{result['status']}] plan={result['plan']}")
    print(f"\n{result['final_answer']}")

if __name__ == "__main__":
    main()