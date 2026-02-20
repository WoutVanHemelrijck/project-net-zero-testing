"""
query.py — Embed a Python function via Voyage AI, query ChromaDB, return top-k patterns.

Usage (CLI):
    python rag/query.py --code "def get_user(id): return db.query(f'SELECT * FROM users WHERE id={id}')"

Programmatic usage:
    from rag.query import query_patterns
    patterns = query_patterns(function_code)
"""

import argparse
import json
import os

import voyageai
import chromadb
from dotenv import load_dotenv

load_dotenv()


def _get_collection():
    persist_dir = os.getenv("CHROMA_PERSIST_DIR", "./rag/chroma_store")
    client = chromadb.PersistentClient(path=persist_dir)
    return client.get_collection("gsf_patterns")


def query_patterns(
    function_code: str,
    top_k: int = 3,
    threshold: float = 0.4,
) -> list[dict]:
    """
    Return the top-k GSF patterns most relevant to the given Python function.

    Args:
        function_code: Source code of the Python function to analyse.
        top_k:         Maximum number of patterns to return.
        threshold:     Minimum cosine similarity (0–1) to include a result.

    Returns:
        List of dicts ordered by similarity descending:
            {
                "pattern_name": str,
                "full_text":    str,
                "url":          str,
                "similarity":   float,
            }
        Empty list if no pattern meets the threshold.
    """
    vo = voyageai.Client()
    collection = _get_collection()

    embedding = vo.embed(
        [function_code], model="voyage-code-2", input_type="query"
    ).embeddings[0]

    results = collection.query(
        query_embeddings=[embedding],
        n_results=top_k,
        include=["documents", "metadatas", "distances"],
    )

    patterns = []
    for metadata, distance in zip(
        results["metadatas"][0],
        results["distances"][0],
    ):
        similarity = 1 - distance  # ChromaDB cosine distance → similarity
        if similarity >= threshold:
            patterns.append(
                {
                    "pattern_name": metadata["pattern_name"],
                    "full_text": metadata["full_text"],
                    "url": metadata["url"],
                    "similarity": round(similarity, 3),
                }
            )

    return patterns


def main():
    parser = argparse.ArgumentParser(
        description="Query GSF patterns relevant to a Python function"
    )
    parser.add_argument("--code", required=True, help="Python function source code")
    parser.add_argument("--top-k", type=int, default=3, help="Number of results")
    parser.add_argument(
        "--threshold", type=float, default=0.4, help="Minimum similarity score"
    )
    args = parser.parse_args()

    patterns = query_patterns(args.code, top_k=args.top_k, threshold=args.threshold)

    if not patterns:
        print("No patterns found above threshold.")
        return

    for p in patterns:
        print(f"\n[{p['similarity']:.3f}] {p['pattern_name']}")
        print(f"  URL: {p['url']}")
        print(f"  Preview: {p['full_text'][:200].replace(chr(10), ' ')}...")


if __name__ == "__main__":
    main()
