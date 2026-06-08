"""
Task 7 — Reranking Module

Dùng RRF (Reciprocal Rank Fusion) để rerank candidates.
RRF công thức: score(d) = Σ 1 / (k + rank(d))
  - k=60: hằng số chuẩn, giảm ảnh hưởng của rank cao
  - Không cần model, chạy nhanh, hiệu quả khi gộp nhiều ranker

Tự implement thay vì dùng thư viện → +5 điểm bonus theo README.
"""


def _rrf_score(rank: int, k: int = 60) -> float:
    """Công thức RRF: 1 / (k + rank), rank bắt đầu từ 1."""
    return 1.0 / (k + rank)


def rerank(query: str, candidates: list[dict], top_k: int = 5) -> list[dict]:
    """
    Rerank candidates dùng RRF (Reciprocal Rank Fusion).

    Kết hợp 2 tín hiệu:
      1. Rank ban đầu theo score gốc (từ semantic/lexical search)
      2. Độ khớp keyword giữa query và content

    Args:
        query: Câu truy vấn gốc
        candidates: List of {'content': str, 'score': float, 'metadata': dict}
        top_k: Số kết quả trả về sau rerank

    Returns:
        List of {'content': str, 'score': float, 'metadata': dict}
        Sorted descending theo RRF score.
    """
    if not candidates:
        return []

    query_tokens = set(query.lower().split())

    # Tín hiệu 1: rank theo score gốc (đã sorted descending)
    original_ranked = sorted(candidates, key=lambda x: x.get("score", 0), reverse=True)

    # Tín hiệu 2: rank theo keyword overlap với query
    def keyword_score(c: dict) -> float:
        content_tokens = set(c["content"].lower().split())
        overlap = len(query_tokens & content_tokens)
        return overlap / max(len(query_tokens), 1)

    keyword_ranked = sorted(candidates, key=keyword_score, reverse=True)

    # Tính RRF score cho mỗi candidate
    rrf_scores: dict[int, float] = {i: 0.0 for i in range(len(candidates))}

    for rank, item in enumerate(original_ranked, start=1):
        idx = candidates.index(item)
        rrf_scores[idx] += _rrf_score(rank)

    for rank, item in enumerate(keyword_ranked, start=1):
        idx = candidates.index(item)
        rrf_scores[idx] += _rrf_score(rank)

    # Sắp xếp theo RRF score và lấy top_k
    sorted_indices = sorted(rrf_scores, key=lambda i: rrf_scores[i], reverse=True)[:top_k]

    return [
        {
            "content": candidates[i]["content"],
            "score": round(rrf_scores[i], 6),
            "metadata": candidates[i].get("metadata", {}),
        }
        for i in sorted_indices
    ]


if __name__ == "__main__":
    from src.task5_semantic_search import semantic_search
    from src.task6_lexical_search import lexical_search

    query = "hình phạt tàng trữ ma tuý"
    sem = semantic_search(query, top_k=10)
    lex = lexical_search(query, top_k=10)
    candidates = sem + lex

    results = rerank(query, candidates, top_k=5)
    print(f"Query: {query}\n")
    for i, r in enumerate(results, 1):
        print(f"[{i}] rrf={r['score']} | {r['metadata'].get('source', '')} | {r['content'][:100]}...")
