"""
Task 8 — PageIndex Vectorless RAG

Dùng PageIndex SDK để thực hiện vectorless retrieval.
Đây là fallback khi hybrid search (Task 9) không trả về kết quả đủ tốt.

Setup:
    1. Đăng ký tại https://pageindex.ai/
    2. Lấy API key từ dashboard
    3. Thêm vào .env: PAGEINDEX_API_KEY=your_key_here
    4. Upload tài liệu lên PageIndex dashboard
    5. Copy index_id và thêm vào .env: PAGEINDEX_INDEX_ID=your_index_id
"""

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

PAGEINDEX_API_KEY = os.getenv("PAGEINDEX_API_KEY", "")
PAGEINDEX_INDEX_ID = os.getenv("PAGEINDEX_INDEX_ID", "")


def pageindex_search(query: str, top_k: int = 5) -> list[dict]:
    """
    Vectorless retrieval dùng PageIndex.
    Fallback khi hybrid search không trả về kết quả phù hợp.

    Args:
        query: Câu truy vấn
        top_k: Số kết quả trả về

    Returns:
        List of {'content': str, 'score': float, 'metadata': dict, 'source': 'pageindex'}
    """
    if not PAGEINDEX_API_KEY:
        raise ValueError("Thiếu PAGEINDEX_API_KEY trong .env")

    if not PAGEINDEX_INDEX_ID:
        raise ValueError("Thiếu PAGEINDEX_INDEX_ID trong .env")

    from pageindex import PageIndexClient

    client = PageIndexClient(api_key=PAGEINDEX_API_KEY)

    response = client.query(
        index_id=PAGEINDEX_INDEX_ID,
        query=query,
        top_k=top_k,
    )

    results = []
    for item in response:
        results.append({
            "content": item.get("text", item.get("content", "")),
            "score": float(item.get("score", 0.0)),
            "metadata": {
                "source_file": item.get("source", ""),
                "page": item.get("page", None),
            },
            "source": "pageindex",
        })

    return results


if __name__ == "__main__":
    query = "hình phạt tàng trữ ma tuý"
    print(f"Query: {query}\n")
    try:
        results = pageindex_search(query, top_k=3)
        for i, r in enumerate(results, 1):
            print(f"[{i}] score={r['score']} | {r['content'][:100]}...")
    except Exception as e:
        print(f"Lỗi: {e}")
