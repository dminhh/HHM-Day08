"""
Task 5 — Semantic Search Module.

Dùng BAAI/bge-m3 (cùng model Task 4) để embed query,
sau đó tìm kiếm trên FAISS index bằng cosine similarity (IndexFlatIP + normalized).
"""

import json
import numpy as np
from pathlib import Path

_INDEX_DIR = Path(__file__).parent.parent / "data" / "faiss_index"
_FAISS_FILE = _INDEX_DIR / "vectors.index"
_CHUNKS_FILE = _INDEX_DIR / "chunks.json"
_EMBEDDING_MODEL = "BAAI/bge-m3"

# Cache để tránh load lại mỗi lần gọi
_model = None
_index = None
_chunks = None


def _get_model():
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer
        _model = SentenceTransformer(_EMBEDDING_MODEL)
    return _model


def _get_index():
    global _index, _chunks
    if _index is None:
        import faiss
        _index = faiss.deserialize_index(np.frombuffer(_FAISS_FILE.read_bytes(), dtype="uint8"))
        _chunks = json.loads(_CHUNKS_FILE.read_text(encoding="utf-8"))
    return _index, _chunks


def semantic_search(query: str, top_k: int = 10) -> list[dict]:
    """
    Tìm kiếm ngữ nghĩa sử dụng vector cosine similarity.

    Args:
        query: Câu truy vấn
        top_k: Số lượng kết quả tối đa

    Returns:
        List of {
            'content': str,
            'score': float,      # cosine similarity [0, 1]
            'metadata': dict     # source, type, chunk_index
        }
        Sorted by score descending.
    """

    model = _get_model()
    index, chunks = _get_index()

    query_vec = model.encode(query, normalize_embeddings=True).astype("float32")
    query_vec = query_vec.reshape(1, -1)

    scores, indices = index.search(query_vec, top_k)

    results = []
    for score, idx in zip(scores[0], indices[0]):
        if idx == -1:
            continue
        chunk = chunks[idx]
        results.append({
            "content": chunk["content"],
            "score": round(float(score), 4),
            "metadata": chunk["metadata"],
        })

    # Đã sorted descending (FAISS IndexFlatIP trả về theo inner product cao nhất)
    return results


if __name__ == "__main__":
    import sys, io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

    queries = [
        "hình phạt cho tội tàng trữ ma tuý",
        "nghệ sĩ bị bắt vì sử dụng ma túy",
        "cai nghiện bắt buộc",
    ]
    for q in queries:
        print(f"\nQuery: {q}")
        results = semantic_search(q, top_k=3)
        for r in results:
            print(f"  [{r['score']:.3f}] ({r['metadata']['type']}/{r['metadata']['source']}) {r['content'][:100]}...")
