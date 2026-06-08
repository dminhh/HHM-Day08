"""
Task 9 — Retrieval Pipeline Hoàn Chỉnh.

Pipeline:
    Query
      ├─→ Semantic Search (ChromaDB dense)   ──┐
      │                                         ├─→ RRF Merge → Rerank → Results
      ├─→ Lexical Search (BM25)             ──┘
      │
      └─→ Nếu best_score < threshold → Fallback: PageIndex Vectorless

Chạy: python -m src.task9_retrieval_pipeline
"""
from __future__ import annotations

from .task5_semantic_search import semantic_search
from .task6_lexical_search import lexical_search
from .task7_reranking import rerank, rerank_rrf
from .task8_pageindex_vectorless import pageindex_search

SCORE_THRESHOLD = 0.3
DEFAULT_TOP_K = 5
RERANK_METHOD = "rrf"  # default: rrf (không cần API)


def retrieve(
    query: str,
    top_k: int = DEFAULT_TOP_K,
    score_threshold: float = SCORE_THRESHOLD,
    use_reranking: bool = True,
) -> list[dict]:
    """
    Retrieval pipeline hoàn chỉnh với fallback logic.

    Args:
        query:            Câu truy vấn
        top_k:            Số kết quả cuối cùng
        score_threshold:  Ngưỡng tối thiểu; nếu thấp hơn → fallback PageIndex
        use_reranking:    Có dùng reranking không

    Returns:
        List of {
            'content': str,
            'score': float,
            'metadata': dict,
            'source': 'hybrid' | 'pageindex' | 'pageindex_fallback'
        }
    """
    fetch_k = top_k * 3  # Lấy nhiều hơn để rerank có đủ candidates

    # --- Step 1: Chạy song song semantic + lexical search ---
    print(f"  [1/4] Semantic search (top={fetch_k})...")
    try:
        dense_results = semantic_search(query, top_k=fetch_k)
    except RuntimeError as e:
        print(f"    ⚠ Semantic search lỗi: {e}")
        dense_results = []

    print(f"  [2/4] Lexical BM25 search (top={fetch_k})...")
    try:
        sparse_results = lexical_search(query, top_k=fetch_k)
    except Exception as e:
        print(f"    ⚠ BM25 search lỗi: {e}")
        sparse_results = []

    if not dense_results and not sparse_results:
        print("  ⚠ Cả 2 search đều rỗng. Fallback → PageIndex")
        results = pageindex_search(query, top_k=top_k)
        for r in results:
            r.setdefault("source", "pageindex")
        return results

    # Track max original score before RRF (cosine similarity / normalized BM25)
    # RRF scores (~0.016) cannot be compared against score_threshold directly.
    max_original_score = max(
        (r["score"] for r in dense_results + sparse_results),
        default=0.0,
    )

    # --- Step 2: Merge bằng RRF ---
    print("  [3/4] RRF merge...")
    ranked_lists = [l for l in [dense_results, sparse_results] if l]
    merged = rerank_rrf(ranked_lists, top_k=fetch_k, k=60)
    for item in merged:
        item["source"] = "hybrid"

    # --- Step 3: Rerank ---
    if use_reranking and merged:
        print(f"  [4/4] Reranking ({RERANK_METHOD}, top={top_k})...")
        final_results = rerank(query, merged, top_k=top_k, method=RERANK_METHOD)
    else:
        final_results = merged[:top_k]

    # --- Step 4: Fallback nếu score quá thấp ---
    # So sánh max_original_score (cosine sim / BM25 normalized) với threshold,
    # không dùng RRF score vì RRF score (~0.016) luôn thấp hơn threshold 0.3.
    if max_original_score < score_threshold:
        print(f"  ⚠ Best original score {max_original_score:.4f} < threshold {score_threshold}. "
              f"Fallback → PageIndex")
        fallback = pageindex_search(query, top_k=top_k)
        for r in fallback:
            r.setdefault("source", "pageindex")
        return fallback

    return final_results[:top_k]


if __name__ == "__main__":
    test_queries = [
        "Hình phạt cho tội tàng trữ trái phép chất ma tuý",
        "Nghệ sĩ nào bị bắt vì sử dụng ma tuý",
        "Luật phòng chống ma tuý 2021 quy định gì về cai nghiện",
    ]

    for q in test_queries:
        print(f"\nQuery: {q}")
        print("-" * 60)
        results = retrieve(q, top_k=3)
        for i, r in enumerate(results, 1):
            src = r.get("source", "?")
            print(f"  {i}. [score={r['score']:.4f}] [{src}] {r['content'][:80].strip()}...")
