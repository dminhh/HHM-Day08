"""
Task 8 — PageIndex Vectorless RAG.

PageIndex (https://pageindex.ai/) cho phép RAG không cần vector store —
dùng structural/semantic understanding của document thay vì embedding.

Nếu không có API key → fallback sang keyword-based search từ local files.

Đăng ký: https://pageindex.ai/
SDK: https://github.com/VectifyAI/PageIndex

Chạy: python -m src.task8_pageindex_vectorless
"""
from __future__ import annotations

import os
import re
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

PAGEINDEX_API_KEY = os.getenv("PAGEINDEX_API_KEY", "")
STANDARDIZED_DIR = Path(__file__).parent.parent / "data" / "standardized"

_uploaded_doc_ids: list[str] = []


def upload_documents() -> list[str]:
    """
    Upload toàn bộ markdown documents lên PageIndex.
    Returns danh sách document IDs.
    """
    global _uploaded_doc_ids

    if not PAGEINDEX_API_KEY:
        raise RuntimeError("PAGEINDEX_API_KEY chưa được set trong .env")

    from pageindex import PageIndex  # type: ignore

    pi = PageIndex(api_key=PAGEINDEX_API_KEY)
    doc_ids = []

    for md_file in sorted(STANDARDIZED_DIR.rglob("*.md")):
        content = md_file.read_text(encoding="utf-8")
        doc_type = "legal" if "legal" in str(md_file) else "news"
        try:
            doc_id = pi.upload(
                content=content,
                metadata={"filename": md_file.name, "type": doc_type},
            )
            doc_ids.append(doc_id)
            print(f"  ✓ Uploaded: {md_file.name} (id={doc_id})")
        except Exception as e:
            print(f"  ✗ Lỗi upload {md_file.name}: {e}")

    _uploaded_doc_ids = doc_ids
    return doc_ids


def _keyword_fallback(query: str, top_k: int = 5) -> list[dict]:
    """
    Fallback khi không có PageIndex API key.
    Tìm kiếm keyword đơn giản trên local markdown files.
    """
    query_terms = [t.lower() for t in re.split(r"\s+", query.strip()) if len(t) > 1]

    results = []
    for md_file in sorted(STANDARDIZED_DIR.rglob("*.md")):
        content = md_file.read_text(encoding="utf-8")
        content_lower = content.lower()

        score = sum(content_lower.count(term) for term in query_terms)
        if score == 0:
            continue

        # Tìm đoạn văn có nhiều từ khóa nhất
        paragraphs = [p.strip() for p in content.split("\n\n") if len(p.strip()) > 50]
        best_para, best_para_score = "", 0
        for para in paragraphs:
            para_lower = para.lower()
            para_score = sum(para_lower.count(t) for t in query_terms)
            if para_score > best_para_score:
                best_para_score, best_para = para_score, para

        if best_para:
            doc_type = "legal" if "legal" in str(md_file) else "news"
            results.append({
                "content": best_para[:800],
                "score": round(min(score / (len(query_terms) * 5 + 1), 1.0), 4),
                "metadata": {"source": md_file.name, "type": doc_type},
                "source": "pageindex",
            })

    results.sort(key=lambda x: x["score"], reverse=True)
    return results[:top_k]


def pageindex_search(query: str, top_k: int = 5) -> list[dict]:
    """
    Vectorless retrieval dùng PageIndex SDK.
    Fallback sang keyword search nếu không có API key.

    Args:
        query:  Câu truy vấn
        top_k:  Số kết quả tối đa

    Returns:
        List of {
            'content': str,
            'score': float,
            'metadata': dict,
            'source': 'pageindex' | 'pageindex_fallback'
        }
    """
    if not PAGEINDEX_API_KEY:
        print("  ℹ PAGEINDEX_API_KEY chưa set → dùng keyword fallback")
        return _keyword_fallback(query, top_k)

    try:
        from pageindex import PageIndex  # type: ignore

        pi = PageIndex(api_key=PAGEINDEX_API_KEY)

        # Upload nếu chưa có
        if not _uploaded_doc_ids:
            upload_documents()

        results = pi.query(query=query, top_k=top_k)

        return [
            {
                "content": r.text if hasattr(r, "text") else str(r),
                "score": float(r.score) if hasattr(r, "score") else 0.5,
                "metadata": r.metadata if hasattr(r, "metadata") else {},
                "source": "pageindex",
            }
            for r in results
        ]

    except ImportError:
        print("  ⚠ pageindex package chưa install. pip install pageindex")
        return _keyword_fallback(query, top_k)
    except Exception as e:
        print(f"  ⚠ PageIndex lỗi: {e}. Fallback sang keyword search.")
        return _keyword_fallback(query, top_k)


if __name__ == "__main__":
    if not PAGEINDEX_API_KEY:
        print("⚠ PAGEINDEX_API_KEY chưa set trong .env")
        print("  Đăng ký tại: https://pageindex.ai/")
        print("  → Dùng keyword fallback...\n")

    test_queries = [
        "hình phạt sử dụng ma tuý",
        "nghệ sĩ bị bắt ma tuý",
    ]
    for q in test_queries:
        print(f"Query: {q}")
        results = pageindex_search(q, top_k=3)
        for i, r in enumerate(results, 1):
            print(f"  {i}. [score={r['score']:.4f}] [{r['source']}] {r['content'][:80]}...")
        print()
