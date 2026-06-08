"""
Task 8 — PageIndex Vectorless RAG.

PageIndex tìm kiếm dựa trên cấu trúc tài liệu thay vì vector embedding —
không cần build index hay embedding model.

Đăng ký: https://pageindex.ai/
SDK: https://github.com/VectifyAI/PageIndex

Cài đặt:
    pip install pageindex

Nếu chưa có API key → fallback về BM25 (task6) để pipeline không bị gián đoạn.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

PAGEINDEX_API_KEY = os.getenv("PAGEINDEX_API_KEY", "")
STANDARDIZED_DIR = Path(__file__).parent.parent / "data" / "standardized"


def upload_documents():
    """Upload toàn bộ markdown documents lên PageIndex."""
    if not PAGEINDEX_API_KEY:
        print("PAGEINDEX_API_KEY chưa set — skip upload")
        return

    from pageindex import PageIndex
    pi = PageIndex(api_key=PAGEINDEX_API_KEY)

    for md_file in sorted(STANDARDIZED_DIR.rglob("*.md")):
        content = md_file.read_text(encoding="utf-8")
        doc_type = "legal" if "legal" in md_file.parts else "news"
        pi.upload(
            content=content,
            metadata={"filename": md_file.name, "type": doc_type},
        )
        print(f"  Uploaded: {md_file.name}")


def pageindex_search(query: str, top_k: int = 5) -> list[dict]:
    """
    Vectorless retrieval sử dụng PageIndex.
    Dùng làm fallback khi hybrid search score < threshold.

    Returns:
        List of {'content', 'score', 'metadata', 'retrieval_source': 'pageindex'}
    """
    if not PAGEINDEX_API_KEY:
        # Fallback về BM25 nếu chưa có API key
        try:
            import sys
            sys.path.insert(0, str(Path(__file__).parent))
            from task6_lexical_search import lexical_search
            results = lexical_search(query, top_k=top_k)
            for r in results:
                r["source"] = "bm25_fallback"
                r["retrieval_source"] = "bm25_fallback"
            return results
        except Exception:
            return []

    from pageindex import PageIndex
    pi = PageIndex(api_key=PAGEINDEX_API_KEY)
    raw = pi.query(query=query, top_k=top_k)

    return [
        {
            "content": r.text if hasattr(r, "text") else str(r),
            "score": float(r.score) if hasattr(r, "score") else 0.0,
            "metadata": r.metadata if hasattr(r, "metadata") else {},
            "source": "pageindex",
            "retrieval_source": "pageindex",
        }
        for r in raw
    ]


if __name__ == "__main__":
    import sys, io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

    if not PAGEINDEX_API_KEY:
        print("PAGEINDEX_API_KEY chưa set trong .env")
        print("Chạy fallback BM25:")

    results = pageindex_search("hình phạt sử dụng ma tuý", top_k=3)
    for r in results:
        print(f"[{r['score']:.3f}] [{r['retrieval_source']}] {r['content'][:100]}...")
