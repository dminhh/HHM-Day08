"""
Task 6 — Lexical Search Module (BM25)

Dùng rank-bm25 (BM25Okapi) để thực hiện keyword-based retrieval.
Corpus được load từ data/standardized/ (các chunk đã tạo ở Task 4).
"""

from pathlib import Path

from rank_bm25 import BM25Okapi

from src.task4_chunking_indexing import load_documents, chunk_documents

# Build BM25 index một lần khi import
_chunks: list[dict] = []
_bm25: BM25Okapi | None = None


def _build_index() -> None:
    """Load documents, chunk, và build BM25 index."""
    global _chunks, _bm25
    docs = load_documents()
    _chunks = chunk_documents(docs)
    tokenized = [c["content"].lower().split() for c in _chunks]
    _bm25 = BM25Okapi(tokenized)


def lexical_search(query: str, top_k: int = 10) -> list[dict]:
    """
    BM25 lexical search trên toàn bộ chunks.

    Args:
        query: Câu truy vấn
        top_k: Số kết quả trả về

    Returns:
        List of {'content': str, 'score': float, 'metadata': dict}
        Sorted descending theo BM25 score.
    """
    global _bm25, _chunks
    if _bm25 is None:
        _build_index()

    tokenized_query = query.lower().split()
    scores = _bm25.get_scores(tokenized_query)

    # Lấy top_k index có score cao nhất
    top_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:top_k]

    return [
        {
            "content": _chunks[i]["content"],
            "score": round(float(scores[i]), 4),
            "metadata": _chunks[i]["metadata"],
        }
        for i in top_indices
    ]


if __name__ == "__main__":
    query = "tàng trữ trái phép chất ma tuý"
    print(f"Query: {query}\n")
    results = lexical_search(query, top_k=5)
    for i, r in enumerate(results, 1):
        print(f"[{i}] score={r['score']} | {r['metadata'].get('source')} | {r['content'][:100]}...")
