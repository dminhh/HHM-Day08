"""
Task 5 — Semantic Search Module (Dense Retrieval).

Query ChromaDB bằng cosine similarity với embedding model đã chọn ở Task 4.

Chạy: python -m src.task5_semantic_search
"""
from __future__ import annotations

from .task4_chunking_indexing import get_chroma_collection, get_embedding_model


def semantic_search(query: str, top_k: int = 10) -> list[dict]:
    """
    Tìm kiếm ngữ nghĩa dùng dense vector retrieval.

    Args:
        query:  Câu truy vấn (tiếng Việt hoặc tiếng Anh)
        top_k:  Số kết quả trả về tối đa

    Returns:
        List of {
            'content': str,     — nội dung chunk
            'score': float,     — cosine similarity [0, 1], sorted descending
            'metadata': dict    — source, type, chunk_index, ...
        }
    """
    model = get_embedding_model()
    collection = get_chroma_collection()

    if collection.count() == 0:
        raise RuntimeError("ChromaDB collection rỗng. Hãy chạy Task 4 trước.")

    query_embedding = model.encode([query], normalize_embeddings=True).tolist()

    results = collection.query(
        query_embeddings=query_embedding,
        n_results=min(top_k, collection.count()),
        include=["documents", "metadatas", "distances"],
    )

    output = []
    for doc, meta, dist in zip(
        results["documents"][0],
        results["metadatas"][0],
        results["distances"][0],
    ):
        # ChromaDB dùng L2 distance với normalized vectors ≡ cosine distance
        # cosine_similarity = 1 - (L2^2 / 2)  khi vector đã normalize
        score = float(1.0 - dist / 2.0)
        output.append({
            "content": doc,
            "score": round(score, 4),
            "metadata": meta,
        })

    # Đảm bảo sort descending theo score
    output.sort(key=lambda x: x["score"], reverse=True)
    return output


if __name__ == "__main__":
    test_queries = [
        "hình phạt tội tàng trữ trái phép chất ma tuý",
        "nghệ sĩ bị bắt sử dụng ma tuý",
        "cai nghiện bắt buộc theo luật phòng chống ma tuý 2021",
    ]
    for q in test_queries:
        print(f"\nQuery: {q}")
        print("-" * 60)
        results = semantic_search(q, top_k=3)
        for i, r in enumerate(results, 1):
            print(f"  {i}. [score={r['score']:.4f}] [{r['metadata'].get('type')}] "
                  f"{r['content'][:80].strip()}...")
