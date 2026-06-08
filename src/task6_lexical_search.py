"""
Task 6 — Lexical Search Module (BM25).

Dùng BM25Okapi (rank-bm25) cho sparse retrieval.

Cơ chế BM25:
  score(q,d) = Σ IDF(qᵢ) * (f(qᵢ,d)*(k₁+1)) / (f(qᵢ,d) + k₁*(1-b+b*|d|/avgdl))
  - IDF: từ hiếm có trọng số cao hơn
  - TF saturation: k₁ tránh từ xuất hiện nhiều lần dominate
  - Length norm: b điều chỉnh ảnh hưởng của độ dài document

Khác với TF-IDF thuần, BM25 saturation TF nên phù hợp văn bản pháp luật dài.

Chạy: python -m src.task6_lexical_search
"""
from __future__ import annotations

import re

from rank_bm25 import BM25Okapi

from .task4_chunking_indexing import chunk_documents, load_documents

_bm25_index: BM25Okapi | None = None
_corpus_chunks: list[dict] | None = None


def _tokenize_vi(text: str) -> list[str]:
    """
    Tokenize tiếng Việt đơn giản: lowercase + split theo whitespace và dấu câu.
    Lý do không dùng thư viện nặng (underthesea, pyvi): tránh phụ thuộc,
    BM25 vẫn hoạt động tốt với word-level tokenization cho tiếng Việt.
    """
    text = text.lower()
    tokens = re.split(r'[\s\.,;:!?()\[\]{}\"“”‘’…\-–—/\\]+', text)
    return [t for t in tokens if len(t) > 1]


def build_bm25_index(chunks: list[dict] | None = None) -> tuple[BM25Okapi, list[dict]]:
    """
    Xây dựng BM25 index từ danh sách chunks.
    Nếu chunks=None, tự load từ data/standardized/.
    """
    global _bm25_index, _corpus_chunks

    if chunks is None:
        docs = load_documents()
        chunks = chunk_documents(docs)

    if not chunks:
        raise RuntimeError("Không có chunks để build index. Hãy chạy Task 3+4 trước.")

    tokenized_corpus = [_tokenize_vi(c["content"]) for c in chunks]
    bm25 = BM25Okapi(tokenized_corpus, k1=1.5, b=0.75)

    _bm25_index = bm25
    _corpus_chunks = chunks
    return bm25, chunks


def get_bm25_index() -> tuple[BM25Okapi, list[dict]]:
    """Trả về (bm25, chunks), lazy-load nếu chưa build."""
    global _bm25_index, _corpus_chunks
    if _bm25_index is None:
        build_bm25_index()
    return _bm25_index, _corpus_chunks


def lexical_search(query: str, top_k: int = 10) -> list[dict]:
    """
    Tìm kiếm từ khóa dùng BM25Okapi.

    Args:
        query:  Câu truy vấn
        top_k:  Số kết quả trả về tối đa

    Returns:
        List of {
            'content': str,             — nội dung chunk
            'score': float,             — normalized BM25 score [0,1], sorted descending
            'raw_bm25_score': float,    — raw BM25 score
            'metadata': dict            — source, type, chunk_index, ...
        }
    """
    bm25, chunks = get_bm25_index()

    tokenized_query = _tokenize_vi(query)
    scores = bm25.get_scores(tokenized_query)

    indexed_scores = sorted(enumerate(scores), key=lambda x: x[1], reverse=True)
    top_results = [(idx, sc) for idx, sc in indexed_scores if sc > 0][:top_k]

    max_score = top_results[0][1] if top_results else 1.0
    if max_score == 0:
        max_score = 1.0

    output = []
    for idx, raw_score in top_results:
        output.append({
            "content": chunks[idx]["content"],
            "score": round(float(raw_score) / max_score, 4),
            "raw_bm25_score": round(float(raw_score), 4),
            "metadata": chunks[idx]["metadata"],
        })

    return output


if __name__ == "__main__":
    print("Building BM25 index...")
    build_bm25_index()

    test_queries = [
        "hình phạt tàng trữ ma tuý",
        "ca sĩ bị bắt ma tuý",
        "cai nghiện bắt buộc",
    ]
    for q in test_queries:
        print(f"\nQuery: {q}")
        print("-" * 60)
        results = lexical_search(q, top_k=3)
        for i, r in enumerate(results, 1):
            print(f"  {i}. [bm25={r['raw_bm25_score']:.3f}|norm={r['score']:.4f}] "
                  f"[{r['metadata'].get('type')}] {r['content'][:80].strip()}...")
