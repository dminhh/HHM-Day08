"""
Task 6 — Lexical Search Module (BM25).

BM25 (Best Match 25) hoạt động thế nào:
    - TF (Term Frequency): từ xuất hiện nhiều trong doc → điểm cao, nhưng có saturation
    - IDF (Inverse Doc Frequency): từ hiếm xuất hiện → quan trọng hơn từ phổ biến
    - Length normalization: doc dài không bị ưu tiên quá mức (tham số b=0.75)
    - Formula: score(q,d) = Σ IDF(qi) * tf(qi,d)*(k1+1) / (tf(qi,d) + k1*(1-b+b*|d|/avgdl))
    - k1=1.5 (term saturation), b=0.75 (length normalization)

Cài đặt:
    pip install rank-bm25
"""

import json
import numpy as np
from pathlib import Path

_CHUNKS_FILE = Path(__file__).parent.parent / "data" / "faiss_index" / "chunks.json"

# Cache BM25 index trong memory
_bm25 = None
_corpus: list[dict] = []


def _get_bm25():
    global _bm25, _corpus
    if _bm25 is None:
        from rank_bm25 import BM25Okapi
        _corpus = json.loads(_CHUNKS_FILE.read_text(encoding="utf-8"))
        # Tokenize đơn giản bằng split() — đủ tốt cho BM25 với tiếng Việt
        tokenized = [doc["content"].lower().split() for doc in _corpus]
        _bm25 = BM25Okapi(tokenized)
    return _bm25, _corpus


def lexical_search(query: str, top_k: int = 10) -> list[dict]:
    """
    Tìm kiếm từ khóa sử dụng BM25.

    Args:
        query: Câu truy vấn
        top_k: Số lượng kết quả tối đa

    Returns:
        List of {
            'content': str,
            'score': float,      # BM25 score
            'metadata': dict
        }
        Sorted by score descending.
    """
    bm25, corpus = _get_bm25()

    tokenized_query = query.lower().split()
    scores = bm25.get_scores(tokenized_query)

    top_indices = np.argsort(scores)[::-1][:top_k]

    results = []
    for idx in top_indices:
        if scores[idx] > 0:
            results.append({
                "content": corpus[idx]["content"],
                "score": float(scores[idx]),
                "metadata": corpus[idx]["metadata"],
            })
    return results


if __name__ == "__main__":
    import sys, io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

    queries = [
        "Điều 248 tàng trữ trái phép chất ma tuý",
        "Long Nhật Miu Lê bị bắt",
        "cai nghiện bắt buộc tự nguyện",
    ]
    for q in queries:
        print(f"\nQuery: {q}")
        results = lexical_search(q, top_k=3)
        for r in results:
            print(f"  [{r['score']:.3f}] ({r['metadata']['type']}/{r['metadata']['source']}) {r['content'][:100]}...")
