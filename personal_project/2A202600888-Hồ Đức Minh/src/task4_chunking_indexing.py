"""
Task 4 — Chunking & Indexing

Chunking strategy: RecursiveCharacterTextSplitter
- CHUNK_SIZE = 500: đủ nhỏ để retrieval chính xác, đủ lớn để giữ ngữ cảnh
- CHUNK_OVERLAP = 50: 10% overlap để tránh mất thông tin ở ranh giới chunk

Embedding model: openai text-embedding-3-small (qua OPENAI_API_KEY trong .env)
Vector store: ChromaDB — nhẹ, không cần server, hỗ trợ persistent storage
"""

from pathlib import Path

from langchain_text_splitters import RecursiveCharacterTextSplitter

# Chunking config
# CHUNK_SIZE=500: phù hợp văn bản pháp luật tiếng Việt, giữ đủ ngữ cảnh câu
# CHUNK_OVERLAP=50: 10% overlap tránh mất thông tin tại ranh giới chunk
CHUNK_SIZE = 500
CHUNK_OVERLAP = 50

STANDARDIZED_DIR = Path(__file__).parent.parent / "data" / "standardized"
CHROMA_DIR = Path(__file__).parent.parent / "data" / "chroma_db"


def load_documents() -> list[dict]:
    """
    Đọc toàn bộ file .md trong data/standardized/ (legal + news).

    Returns:
        List of {'content': str, 'metadata': dict}
    """
    docs = []
    for md_file in sorted(STANDARDIZED_DIR.rglob("*.md")):
        content = md_file.read_text(encoding="utf-8").strip()
        if not content:
            continue
        docs.append({
            "content": content,
            "metadata": {
                "source": md_file.name,
                "category": md_file.parent.name,  # "legal" hoặc "news"
                "path": str(md_file),
            }
        })
    return docs


def chunk_documents(docs: list[dict]) -> list[dict]:
    """
    Chia documents thành các chunks nhỏ dùng RecursiveCharacterTextSplitter.

    Args:
        docs: List of {'content': str, 'metadata': dict}

    Returns:
        List of {'content': str, 'metadata': dict}
    """
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n", "\n", ".", " ", ""],
    )

    chunks = []
    for doc in docs:
        parts = splitter.split_text(doc["content"])
        for i, part in enumerate(parts):
            chunks.append({
                "content": part,
                "metadata": {
                    **doc["metadata"],
                    "chunk_index": i,
                    "total_chunks": len(parts),
                }
            })
    return chunks


def index_documents(chunks: list[dict]) -> None:
    """
    Index chunks vào ChromaDB với OpenAI embeddings.
    Fallback về default embedding nếu không có OPENAI_API_KEY.
    """
    try:
        import chromadb
        from chromadb.utils import embedding_functions
    except ImportError:
        print("ChromaDB chưa cài. Chạy: pip install chromadb")
        return

    CHROMA_DIR.mkdir(parents=True, exist_ok=True)
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
            print("Dùng OpenAI text-embedding-3-small (1536 dims)")
        else:
            ef = embedding_functions.DefaultEmbeddingFunction()
            print("Dùng ChromaDB default embedding (không có OPENAI_API_KEY)")
    except Exception:
        ef = embedding_functions.DefaultEmbeddingFunction()

    collection = client.get_or_create_collection(
        name="legal_news_docs",
        embedding_function=ef,
    )

    ids = [f"chunk_{i}" for i in range(len(chunks))]
    documents = [c["content"] for c in chunks]
    metadatas = [c["metadata"] for c in chunks]

    collection.upsert(ids=ids, documents=documents, metadatas=metadatas)
    print(f"✓ Indexed {len(chunks)} chunks vào ChromaDB tại {CHROMA_DIR}")


if __name__ == "__main__":
    print("Load documents...")
    docs = load_documents()
    print(f"✓ {len(docs)} documents")

    print("\nChunking...")
    chunks = chunk_documents(docs)
    print(f"✓ {len(chunks)} chunks (size={CHUNK_SIZE}, overlap={CHUNK_OVERLAP})")

    print("\nIndexing...")
    index_documents(chunks)
