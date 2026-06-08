"""
Task 7 — Reranking Module.

Implement 3 phương pháp:
  1. RRF (Reciprocal Rank Fusion) — default, không cần API
     Gộp rank từ nhiều retriever: score = Σ 1/(k + rank_i)
  2. MMR (Maximal Marginal Relevance) — giảm trùng lặp
     score = λ*sim(q,d) - (1-λ)*max(sim(d,selected))
  3. Jina Reranker API — cross-encoder multilingual (cần API key)

Chạy: python -m src.task7_reranking
"""
from __future__ import annotations

import os

import numpy as np
import requests
from dotenv import load_dotenv

load_dotenv()

JINA_API_KEY = os.getenv("JINA_API_KEY", "")


# =============================================================================
# RRF — Reciprocal Rank Fusion
# =============================================================================

def rerank_rrf(
    ranked_lists: list[list[dict]],
    top_k: int = 5,
    k: int = 60,
) -> list[dict]:
    """
    Reciprocal Rank Fusion — gộp kết quả từ nhiều ranker.

    Công thức: RRF(d) = Σ 1 / (k + rank_r(d))
    - k=60: hằng số làm mịn (Cormack et al. 2009), giảm ảnh hưởng của rank 1
    - Document xuất hiện ở vị trí cao trong nhiều list → score cao

    Args:
        ranked_lists: List of ranked result lists (mỗi list từ 1 ranker)
        top_k: Số kết quả cuối cùng
        k: Smoothing constant

    Returns:
        List of top_k candidates sorted by RRF score descending.
    """
    rrf_scores: dict[str, float] = {}
    content_map: dict[str, dict] = {}

    for ranked_list in ranked_lists:
        for rank, item in enumerate(ranked_list, 1):
            key = item["content"][:200]  # dùng 200 chars đầu làm key
            rrf_scores[key] = rrf_scores.get(key, 0.0) + 1.0 / (k + rank)
            if key not in content_map:
                content_map[key] = item.copy()

    sorted_items = sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)

    results = []
    for content_key, score in sorted_items[:top_k]:
        item = content_map[content_key].copy()
        item["score"] = round(score, 6)
        item["rerank_method"] = "rrf"
        results.append(item)

    return results


# =============================================================================
# MMR — Maximal Marginal Relevance
# =============================================================================

def _cosine_sim(a: list[float], b: list[float]) -> float:
    a, b = np.array(a), np.array(b)
    denom = np.linalg.norm(a) * np.linalg.norm(b)
    return float(np.dot(a, b) / denom) if denom > 0 else 0.0


def rerank_mmr(
    query_embedding: list[float],
    candidates: list[dict],
    top_k: int = 5,
    lambda_param: float = 0.7,
) -> list[dict]:
    """
    Maximal Marginal Relevance — vừa relevant vừa diverse.

    Công thức: MMR = λ * sim(q,d) - (1-λ) * max(sim(d, S))
    - λ=0.7: nghiêng về relevance, giảm trùng lặp
    - Mỗi vòng chọn doc có MMR score cao nhất, đưa vào Selected set S

    Args:
        query_embedding: Vector của query (đã normalize)
        candidates: List of {'content', 'score', 'embedding'?, 'metadata'}
        top_k: Số kết quả
        lambda_param: 1.0=pure relevance, 0.0=pure diversity

    Returns:
        top_k candidates selected by MMR.
    """
    if not candidates:
        return []

    # Nếu candidates không có embedding, dùng score hiện tại làm relevance proxy
    has_embedding = "embedding" in candidates[0]

    selected_indices: list[int] = []
    remaining = list(range(len(candidates)))

    for _ in range(min(top_k, len(candidates))):
        best_idx, best_score = None, float("-inf")

        for idx in remaining:
            if has_embedding:
                relevance = _cosine_sim(query_embedding, candidates[idx]["embedding"])
            else:
                relevance = candidates[idx].get("score", 0.0)

            max_sim = 0.0
            for sel_idx in selected_indices:
                if has_embedding:
                    sim = _cosine_sim(candidates[idx]["embedding"], candidates[sel_idx]["embedding"])
                else:
                    # Estimate similarity bằng content overlap
                    words_i = set(candidates[idx]["content"].lower().split())
                    words_s = set(candidates[sel_idx]["content"].lower().split())
                    sim = len(words_i & words_s) / max(len(words_i | words_s), 1)
                max_sim = max(max_sim, sim)

            mmr_score = lambda_param * relevance - (1 - lambda_param) * max_sim
            if mmr_score > best_score:
                best_score, best_idx = mmr_score, idx

        if best_idx is None:
            break
        selected_indices.append(best_idx)
        remaining.remove(best_idx)

    results = []
    for rank, idx in enumerate(selected_indices):
        item = candidates[idx].copy()
        item["score"] = round(candidates[idx].get("score", 0.0), 4)
        item["mmr_score"] = round(candidates[idx].get("score", 0.0) * lambda_param, 4)
        item["rerank_method"] = "mmr"
        results.append(item)

    return results


# =============================================================================
# Cross-encoder — Jina Reranker API
# =============================================================================

def rerank_cross_encoder(
    query: str,
    candidates: list[dict],
    top_k: int = 5,
) -> list[dict]:
    """
    Cross-encoder reranking dùng Jina Reranker v2 (multilingual).
    Fallback sang RRF nếu không có API key.

    Jina Reranker so sánh từng cặp (query, document) qua cross-attention,
    cho score chính xác hơn bi-encoder nhưng chậm hơn O(n).
    """
    if not JINA_API_KEY:
        print("  ⚠ JINA_API_KEY không có. Fallback sang RRF.")
        return rerank_rrf([candidates], top_k=top_k)

    try:
        response = requests.post(
            "https://api.jina.ai/v1/rerank",
            headers={
                "Authorization": f"Bearer {JINA_API_KEY}",
                "Content-Type": "application/json",
            },
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

        results = []
        for r in reranked:
            item = candidates[r["index"]].copy()
            item["score"] = round(r["relevance_score"], 4)
            item["rerank_method"] = "cross_encoder_jina"
            results.append(item)
        return results

    except Exception as e:
        print(f"  ⚠ Jina API lỗi: {e}. Fallback sang RRF.")
        return rerank_rrf([candidates], top_k=top_k)


# =============================================================================
# Unified interface
# =============================================================================

def rerank(
    query: str,
    candidates: list[dict],
    top_k: int = 5,
    method: str = "rrf",
) -> list[dict]:
    """
    Unified reranking interface.

    Args:
        query:      Câu truy vấn
        candidates: List of retrieval results (từ semantic + lexical search)
        top_k:      Số kết quả cuối
        method:     "rrf" | "mmr" | "cross_encoder"
    """
    if not candidates:
        return []

    if method == "rrf":
        return rerank_rrf([candidates], top_k=top_k)
    elif method == "mmr":
        return rerank_mmr([], candidates, top_k=top_k, lambda_param=0.7)
    elif method == "cross_encoder":
        return rerank_cross_encoder(query, candidates, top_k=top_k)
    else:
        raise ValueError(f"Unknown method: {method}. Use 'rrf'|'mmr'|'cross_encoder'")


if __name__ == "__main__":
    dummy = [
        {"content": "Điều 248 BLHS: Tội tàng trữ trái phép chất ma tuý phạt tù 2-7 năm", "score": 0.8, "metadata": {"type": "legal"}},
        {"content": "Ca sĩ Long Nhật bị bắt vì liên quan ma tuý tại TP.HCM năm 2026", "score": 0.7, "metadata": {"type": "news"}},
        {"content": "Hình phạt bổ sung: phạt tiền từ 5-500 triệu đồng", "score": 0.6, "metadata": {"type": "legal"}},
        {"content": "Ca sĩ Miu Lê bị khởi tố tội tổ chức sử dụng ma tuý", "score": 0.55, "metadata": {"type": "news"}},
        {"content": "Nghị định 105/2021 quy định cai nghiện bắt buộc", "score": 0.5, "metadata": {"type": "legal"}},
    ]
    q = "hình phạt tội tàng trữ ma tuý"

    print("=== RRF ===")
    from src.task6_lexical_search import lexical_search
    for r in rerank_rrf([dummy[:3], dummy[2:]], top_k=3):
        print(f"  [{r['score']:.6f}] {r['content'][:70]}")

    print("\n=== MMR (lambda=0.7) ===")
    for r in rerank_mmr([], dummy, top_k=3):
        print(f"  [{r['score']:.4f}] {r['content'][:70]}")

    print("\n=== Cross-encoder (Jina, fallback RRF) ===")
    for r in rerank_cross_encoder(q, dummy, top_k=3):
        print(f"  [{r['score']:.4f}] [{r.get('rerank_method')}] {r['content'][:70]}")
