"""
Task 7 — Reranking Module.

Implement 2 phương pháp:
  1. RRF (Reciprocal Rank Fusion) — không cần model, gộp nhiều ranked lists
     Formula: RRF(d) = Σ 1/(k + rank_r(d))   [Cormack et al. 2009, k=60]
  2. Cross-encoder — dùng Jina Reranker API (multilingual, tiếng Việt tốt)
     Fallback về RRF nếu không có JINA_API_KEY

Mặc định dùng RRF vì không cần API key và hoạt động tốt khi combine semantic + lexical.
"""

import os


def rerank_rrf(ranked_lists: list[list[dict]], top_k: int = 5, k: int = 60) -> list[dict]:
    """
    Reciprocal Rank Fusion — gộp kết quả từ nhiều ranker.

    RRF(d) = Σ 1 / (k + rank_r(d))
    k=60: smoothing constant giảm ảnh hưởng của rank rất cao

    Args:
        ranked_lists: List of ranked result lists (mỗi list từ 1 ranker)
        top_k: Số lượng kết quả cuối cùng
        k: Smoothing constant (default=60)

    Returns:
        List of top_k candidates sorted by RRF score descending.
    """
    rrf_scores: dict[str, float] = {}
    content_map: dict[str, dict] = {}

    for ranked_list in ranked_lists:
        for rank, item in enumerate(ranked_list, 1):
            key = item["content"]
            rrf_scores[key] = rrf_scores.get(key, 0.0) + 1.0 / (k + rank)
            content_map[key] = item

    sorted_items = sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)

    results = []
    for content, score in sorted_items[:top_k]:
        item = content_map[content].copy()
        item["score"] = round(score, 6)
        results.append(item)

    return results


def rerank_cross_encoder(query: str, candidates: list[dict], top_k: int = 5) -> list[dict]:
    """
    Rerank bằng Jina Reranker v2 (multilingual, hỗ trợ tiếng Việt).
    Fallback về RRF nếu không có JINA_API_KEY.

    Args:
        query: Câu truy vấn
        candidates: List of {'content': str, 'score': float, 'metadata': dict}
        top_k: Số kết quả sau rerank

    Returns:
        List of top_k candidates re-scored và sorted.
    """
    api_key = os.getenv("JINA_API_KEY", "")
    if not api_key:
        # Fallback: wrap candidates thành ranked_lists cho RRF
        return rerank_rrf([candidates], top_k=top_k)

    import requests
    response = requests.post(
        "https://api.jina.ai/v1/rerank",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json={
            "model": "jina-reranker-v2-base-multilingual",
            "query": query,
            "documents": [c["content"] for c in candidates],
            "top_n": top_k,
        },
        timeout=30,
    )
    response.raise_for_status()

    reranked = response.json()["results"]
    return [
        {**candidates[r["index"]], "score": round(r["relevance_score"], 4)}
        for r in reranked
    ]


def rerank_mmr(
    query_embedding: list[float],
    candidates: list[dict],
    top_k: int = 5,
    lambda_param: float = 0.7,
) -> list[dict]:
    """
    Maximal Marginal Relevance — chọn candidates vừa relevant vừa diverse.
    MMR = λ * sim(query, doc) - (1-λ) * max(sim(doc, selected_docs))

    Args:
        query_embedding: Vector embedding của query (normalized)
        candidates: List có key 'embedding' trong metadata hoặc riêng
        top_k: Số kết quả
        lambda_param: 1.0 = chỉ relevance, 0.0 = chỉ diversity
    """
    import numpy as np

    def cosine(a, b):
        return float(np.dot(a, b))

    q = np.array(query_embedding, dtype="float32")
    embeddings = [np.array(c.get("embedding", [0.0]), dtype="float32") for c in candidates]

    selected_indices = []
    remaining = list(range(len(candidates)))

    for _ in range(min(top_k, len(candidates))):
        best_idx, best_score = None, float("-inf")
        for idx in remaining:
            relevance = cosine(q, embeddings[idx]) if len(embeddings[idx]) > 1 else candidates[idx]["score"]
            max_sim = max((cosine(embeddings[idx], embeddings[s]) for s in selected_indices), default=0.0)
            mmr_score = lambda_param * relevance - (1 - lambda_param) * max_sim
            if mmr_score > best_score:
                best_score, best_idx = mmr_score, idx
        selected_indices.append(best_idx)
        remaining.remove(best_idx)

    return [
        {**candidates[i], "score": round(float(np.dot(q, embeddings[i])), 4)}
        for i in selected_indices
    ]


def rerank(
    query: str,
    candidates: list[dict],
    top_k: int = 5,
    method: str = "rrf",
) -> list[dict]:
    """
    Unified reranking interface.

    Args:
        method: 'rrf' | 'cross_encoder' | 'mmr'
    """
    if not candidates:
        return []
    if method == "rrf":
        return rerank_rrf([candidates], top_k=top_k)
    elif method == "cross_encoder":
        return rerank_cross_encoder(query, candidates, top_k)
    elif method == "mmr":
        raise ValueError("Dùng rerank_mmr() trực tiếp với query_embedding")
    else:
        raise ValueError(f"Unknown method: {method}")


if __name__ == "__main__":
    import sys, io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

    list1 = [
        {"content": "Điều 248 tàng trữ trái phép chất ma tuý", "score": 0.9, "metadata": {}},
        {"content": "Hình phạt tù từ 2-7 năm", "score": 0.7, "metadata": {}},
        {"content": "Ca sĩ Long Nhật bị bắt", "score": 0.5, "metadata": {}},
    ]
    list2 = [
        {"content": "Ca sĩ Long Nhật bị bắt", "score": 8.1, "metadata": {}},
        {"content": "Điều 248 tàng trữ trái phép chất ma tuý", "score": 5.3, "metadata": {}},
        {"content": "Miu Lê dương tính 3 chất cấm", "score": 4.2, "metadata": {}},
    ]
    print("RRF merge:")
    for r in rerank_rrf([list1, list2], top_k=4):
        print(f"  [{r['score']:.5f}] {r['content']}")
