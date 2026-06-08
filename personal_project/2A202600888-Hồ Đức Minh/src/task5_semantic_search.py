"""
Task 5 — Semantic Search Module

Dùng ChromaDB (đã index ở Task 4) để thực hiện dense retrieval.
Embedding: ChromaDB default (all-MiniLM-L6-v2) hoặc OpenAI nếu có API key.
"""

from pathlib import Path

CHROMA_DIR = Path(__file__).parent.parent / "data" / "chroma_db"


def _get_collection():
    """Kết nối ChromaDB và trả về collection."""
    import chromadb
    from chromadb.utils import embedding_functions

    client = chromadb.PersistentClient(path=str(CHROMA_DIR))

    try:
        from dotenv import load_dotenv
        import os
        load_dotenv()
        api_key = os.getenv("OPENAI_API_KEY")
        if api_key:
            ef = embedding_functions.OpenAIEmbeddingFunction(
                api_key=api_key,
                model_name="text-embedding-3-small",
            )
        else:
            ef = embedding_functions.DefaultEmbeddingFunction()
    except Exception:
        ef = embedding_functions.DefaultEmbeddingFunction()

    return client.get_or_create_collection(
        name="legal_news_docs",
        embedding_function=ef,
    )


def semantic_search(query: str, top_k: int = 10) -> list[dict]:
    """
    Semantic search (dense retrieval) trên vector store.

    Args:
        query: Câu truy vấn
        top_k: Số kết quả trả về

    Returns:
        List of {'content': str, 'score': float, 'metadata': dict}
        Sorted descending theo score.
    """
    collection = _get_collection()

    if collection.count() == 0:
        return []

    results = collection.query(
        query_texts=[query],
        n_results=min(top_k, collection.count()),
    )

    docs = results["documents"][0]
    distances = results["distances"][0]
    metadatas = results["metadatas"][0]

    # ChromaDB trả về L2 distance (nhỏ = tốt hơn)
    # Chuyển sang score (lớn = tốt hơn): score = 1 / (1 + distance)
    output = []
    for doc, dist, meta in zip(docs, distances, metadatas):
        output.append({
            "content": doc,
            "score": round(1 / (1 + dist), 4),
            "metadata": meta,
        })

    # Đảm bảo sorted descending theo score
    output.sort(key=lambda x: x["score"], reverse=True)
    return output


if __name__ == "__main__":
    query = "hình phạt tội phạm ma tuý"
    print(f"Query: {query}\n")
    results = semantic_search(query, top_k=5)
    for i, r in enumerate(results, 1):
        print(f"[{i}] score={r['score']} | {r['metadata'].get('source')} | {r['content'][:100]}...")
