"""
Task 9 — Retrieval Pipeline Hoàn Chỉnh.

Pipeline:
    Query
      ├→ Semantic Search (FAISS cosine)   ──┐
      ├→ Lexical Search (BM25)            ──┼→ RRF merge → Rerank → Results
      │                                      │
      └→ If best_score < threshold:          │
            └→ Fallback PageIndex ←──────────┘
"""

import sys
from pathlib import Path

# Support cả import tương đối (module) và tuyệt đối (script trực tiếp)
try:
    from .task5_semantic_search import semantic_search
    from .task6_lexical_search import lexical_search
    from .task7_reranking import rerank_rrf, rerank
    from .task8_pageindex_vectorless import pageindex_search
except ImportError:
    sys.path.insert(0, str(Path(__file__).parent))
    from task5_semantic_search import semantic_search
    from task6_lexical_search import lexical_search
    from task7_reranking import rerank_rrf, rerank
    from task8_pageindex_vectorless import pageindex_search

SCORE_THRESHOLD = 0.3
DEFAULT_TOP_K = 5


def retrieve(
    query: str,
    top_k: int = DEFAULT_TOP_K,
    score_threshold: float = SCORE_THRESHOLD,
    use_reranking: bool = True,
) -> list[dict]:
    """
    Retrieval pipeline hoàn chỉnh.

    1. Semantic Search + Lexical Search song song
    2. Merge bằng RRF (Reciprocal Rank Fusion)
    3. Rerank (cross-encoder nếu có JINA_API_KEY, else RRF)
    4. Nếu top score < threshold → fallback PageIndex/BM25
    5. Return top_k kết quả

    Returns:
        List of {'content', 'score', 'metadata', 'retrieval_source'}
    """
    # Step 1: Song song semantic + lexical
    fetch_k = top_k * 3
    dense_results = semantic_search(query, top_k=fetch_k)
    sparse_results = lexical_search(query, top_k=fetch_k)

    # Dùng best semantic score (cosine 0-1) để check threshold
    best_semantic_score = dense_results[0]["score"] if dense_results else 0.0

    # Step 2: Merge bằng RRF
    merged = rerank_rrf([dense_results, sparse_results], top_k=fetch_k)
    for item in merged:
        item["source"] = "hybrid"
        item["retrieval_source"] = "hybrid"

    # Step 3: Rerank
    if use_reranking and merged:
        final = rerank(query, merged, top_k=top_k, method="cross_encoder")
    else:
        final = merged[:top_k]

    # Step 4: Fallback nếu semantic score quá thấp (query out-of-domain)
    if best_semantic_score < score_threshold:
        print(f"  Semantic score {best_semantic_score:.4f} < threshold {score_threshold} → fallback PageIndex")
        fallback = pageindex_search(query, top_k=top_k)
        return fallback if fallback else final

    return final


if __name__ == "__main__":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

    queries = [
        "Hình phạt cho tội tàng trữ trái phép chất ma tuý",
        "Những nghệ sĩ nào bị bắt vì liên quan tới ma tuý",
        "Luật phòng chống ma tuý 2021 quy định về cai nghiện",
    ]

    for q in queries:
        print(f"\nQuery: {q}")
        print("-" * 60)
        results = retrieve(q, top_k=3)
        for i, r in enumerate(results, 1):
            src = r.get("retrieval_source", "?")
            print(f"  {i}. [{r['score']:.4f}] [{src}] {r['content'][:100]}...")
