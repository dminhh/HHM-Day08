"""
Task 9 — Retrieval Pipeline Hoàn Chỉnh

Flow:
    Query
      ├→ Semantic Search (Task 5)  ──┐
      │                               ├→ Merge + Rerank (Task 7) → Results
      ├→ Lexical Search (Task 6)  ──┘
      │
      └→ Nếu top score < score_threshold
            └→ Fallback: PageIndex Vectorless (Task 8)
"""

from src.task5_semantic_search import semantic_search
from src.task6_lexical_search import lexical_search
from src.task7_reranking import rerank


def _merge_candidates(sem_results: list[dict], lex_results: list[dict]) -> list[dict]:
    """Gộp semantic + lexical results, loại bỏ duplicate content."""
    seen = set()
    merged = []
    for r in sem_results + lex_results:
        key = r["content"][:100]
        if key not in seen:
            seen.add(key)
            merged.append(r)
    return merged


def retrieve(
    query: str,
    top_k: int = 5,
    score_threshold: float = 0.3,
) -> list[dict]:
    """
    Retrieval pipeline hoàn chỉnh với fallback logic.

    1. Chạy semantic_search + lexical_search song song
    2. Merge kết quả (loại duplicate)
    3. Rerank bằng RRF (Task 7)
    4. Nếu top result score < score_threshold → fallback PageIndex (Task 8)
    5. Return top_k results với field 'source'

    Args:
        query: Câu truy vấn
        top_k: Số kết quả trả về
        score_threshold: Ngưỡng score tối thiểu trước khi fallback

    Returns:
        List of {'content': str, 'score': float, 'metadata': dict, 'source': str}
    """
    # Bước 1: Hybrid search
    sem_results = semantic_search(query, top_k=top_k * 2)
    lex_results = lexical_search(query, top_k=top_k * 2)

    # Bước 2: Merge
    candidates = _merge_candidates(sem_results, lex_results)

    # Bước 3: Rerank
    reranked = rerank(query, candidates, top_k=top_k)

    # Đánh dấu source = hybrid
    for r in reranked:
        r["source"] = "hybrid"

    # Bước 4: Fallback nếu score thấp
    if not reranked or reranked[0].get("score", 0) < score_threshold:
        try:
            from src.task8_pageindex_vectorless import pageindex_search
            fallback = pageindex_search(query, top_k=top_k)
            if fallback:
                return fallback[:top_k]
        except Exception:
            pass  # Không có PageIndex API key → dùng hybrid results

    return reranked[:top_k]


if __name__ == "__main__":
    query = "hình phạt tàng trữ trái phép chất ma tuý"
    print(f"Query: {query}\n")
    results = retrieve(query, top_k=5)
    for i, r in enumerate(results, 1):
        print(f"[{i}] score={r['score']} | source={r['source']} | {r['content'][:100]}...")
